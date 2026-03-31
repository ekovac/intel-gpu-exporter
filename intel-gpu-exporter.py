from prometheus_client import start_http_server, Gauge
import os
import sys
import subprocess
import csv
import logging

ENGINE_CSV_MAPPING = {
        'RCS': 'Render/3D',
        'BCS': 'Blitter',
        'VCS': 'Video',
        'VECS': 'VideoEnhance',
        'CCS': 'Compute',
}

MODE_CSV_MAPPING = {
        '%': 'busy',
        'se': 'sema',
        'wa': 'wait',
}

igpu_engines_ratio = Gauge(
    "igpu_engines_ratio", "utilization", ['engine', 'mode']
)

for engine in ENGINE_CSV_MAPPING.values():
    for mode in MODE_CSV_MAPPING.values():
        igpu_engines_ratio.labels(engine, mode)

igpu_frequency_actual = Gauge("igpu_frequency_actual", "Frequency actual MHz")
igpu_frequency_requested = Gauge("igpu_frequency_requested", "Frequency requested MHz")

igpu_interrupts = Gauge("igpu_interrupt_rate", "Interrupts/s")

igpu_rc6 = Gauge("igpu_rc6_ratio", "RC6 %")



def update(data):
    for engine_key, engine_name in ENGINE_CSV_MAPPING.items():
        for mode_key, mode_name in MODE_CSV_MAPPING.items():
            datum = data.get("{} {}".format(engine_key, mode_key))
            igpu_engines_ratio.labels(engine=engine_name, mode=mode_name).set(datum)

    igpu_frequency_actual.set(data.get("Freq MHz act"))
    igpu_frequency_requested.set(data.get("Freq MHz req"))
    igpu_interrupts.set(data.get("IRQ /s"))

    igpu_rc6.set(data.get("RC6 %"))


if __name__ == "__main__":
    if os.getenv("DEBUG", False):
        debug = logging.DEBUG
    else:
        debug = logging.INFO
    logging.basicConfig(format="%(asctime)s - %(message)s", level=debug)

    start_http_server(8080)

    period = os.getenv("REFRESH_PERIOD_MS", 5000)
    device = os.getenv("DEVICE")

    if device is not None:
        cmd = "intel_gpu_top -c -s {} -d {}".format(int(period), device)
    else:
        cmd = "intel_gpu_top -c -s {}".format(int(period))

    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8"
    )

    reader = csv.DictReader(process.stdout)
    for row in reader:
        update(row)

    process.kill()

    if process.returncode != 0:
        logging.error("Error: " + process.stderr.read().decode("utf-8"))

    logging.info("Finished")
