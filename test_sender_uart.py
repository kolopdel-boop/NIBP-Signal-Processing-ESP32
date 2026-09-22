import csv
import time
import serial


# ============================================================
# CONFIG
# ============================================================

CSV_FILE = r"C:\nibp_signal_processing\record_212_processed_master.csv"

COM_PORT = "COM11"
BAUDRATE = 115200

SAMPLE_RATE = 5.0
SAMPLE_INTERVAL = 1.0 / SAMPLE_RATE


# ============================================================
# OPEN SERIAL
# ============================================================

ser = serial.Serial(
    COM_PORT,
    BAUDRATE,
    timeout=1
)


print("======================================")
print("       NIBP RAW DATA TRANSMITTER")
print("======================================")
print("CSV:", CSV_FILE)
print("PORT:", COM_PORT)
print("BAUD:", BAUDRATE)
print("RATE:", SAMPLE_RATE, "Hz")
print("======================================")
print()


# ============================================================
# READ CSV
# ============================================================

samples = []

with open(CSV_FILE, "r", newline="") as f:

    reader = csv.DictReader(f)

    print("CSV columns:")
    print(reader.fieldnames)
    print()

    required = [
        "time",
        "pressure",
        "oscillometric_signal"
    ]

    for column in required:

        if column not in reader.fieldnames:

            ser.close()

            raise ValueError(
                "Missing CSV column: {}".format(column)
            )

    for row in reader:

        pressure = float(
            row["pressure"]
        )

        signal = float(
            row["oscillometric_signal"]
        )

        samples.append(
            (
                pressure,
                signal
            )
        )


# ============================================================
# CHECK
# ============================================================

print("Total samples:", len(samples))

if len(samples) == 0:

    ser.close()

    raise ValueError(
        "No samples found."
    )


print()
print("First samples:")
print("--------------------------------------")

for i in range(min(5, len(samples))):

    pressure, signal = samples[i]

    print(
        "{:03d}  P={:8.3f}  S={:12.6f}".format(
            i + 1,
            pressure,
            signal
        )
    )

print("--------------------------------------")
print()


# ============================================================
# TRANSMISSION
# ============================================================

print("Starting transmission...")
print()

start_time = time.perf_counter()


for index, sample in enumerate(samples):

    pressure = sample[0]
    signal = sample[1]

    target_time = (
        start_time
        + index * SAMPLE_INTERVAL
    )

    while True:

        now = time.perf_counter()

        remaining = target_time - now

        if remaining <= 0:
            break

        time.sleep(
            min(remaining, 0.005)
        )

    # --------------------------------------------------------
    # EXACT FORMAT
    # --------------------------------------------------------

    message = "{:.6f},{:.9f}\n".format(
        pressure,
        signal
    )

    ser.write(
        message.encode("ascii")
    )

    print(
        "{:03d}  P={:8.3f}  S={:12.6f}".format(
            index + 1,
            pressure,
            signal
        )
    )


# ============================================================
# FINISH
# ============================================================

elapsed = (
    time.perf_counter()
    - start_time
)

ser.close()

print()
print("======================================")
print("       TRANSMISSION COMPLETE")
print("======================================")

print("Samples:", len(samples))
print("Elapsed:", round(elapsed, 3), "s")

print(
    "Expected:",
    round(
        (len(samples) - 1)
        * SAMPLE_INTERVAL,
        3
    ),
    "s"
)

print("======================================")