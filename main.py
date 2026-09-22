from machine import Pin, UART
import time

UART_ID = 0
UART_BAUD = 115200
EXPECTED_SAMPLES = 177
FS = 5.0
LOWCUT = 0.5
HIGHCUT = 2.0
FILTER_ORDER = 3
MIN_PEAK_DISTANCE_SEC = 0.60
MIN_PEAK_DISTANCE_SAMPLES = 3
PEAK_PROMINENCE = 0.05
PRESSURE_MIN = 50.0
PRESSURE_MAX = 180.0
DEFLECTION_MIN_DROP = 2.0
MAX_ALLOWED_REVERSAL = 1.5
MIN_AMPLITUDE = 0.15
MIN_PULSES_FOR_ENVELOPE = 6
AMPLITUDE_RATIO_MIN = 0.25
AMPLITUDE_RATIO_MAX = 2.50
SAVGOL_WINDOW = 5
SAVGOL_POLYORDER = 2
PADLEN = 40
WAVEFORM_DISPLAY_TIME_MS = 5000
SBP_RATIO = 0.50
DBP_RATIO = 0.70

uart = UART(UART_ID, baudrate=UART_BAUD, bits=8, parity=None, stop=1, timeout=100)

DATA_PINS = [Pin(4, Pin.OUT), Pin(5, Pin.OUT), Pin(6, Pin.OUT), Pin(7, Pin.OUT), Pin(8, Pin.OUT), Pin(9, Pin.OUT), Pin(10, Pin.OUT), Pin(11, Pin.OUT)]
DI = Pin(12, Pin.OUT)
RW = Pin(13, Pin.OUT)
E = Pin(14, Pin.OUT)
CS1 = Pin(15, Pin.OUT)
CS2 = Pin(16, Pin.OUT)
RST = Pin(17, Pin.OUT)


def glcd_write_byte(value):
    for i in range(8):
        DATA_PINS[i].value((value >> i) & 1)
    E.value(1)
    time.sleep_us(1)
    E.value(0)
    time.sleep_us(1)


def glcd_command(cmd):
    DI.value(0)
    RW.value(0)
    glcd_write_byte(cmd)


def glcd_data(data):
    DI.value(1)
    RW.value(0)
    glcd_write_byte(data)


def glcd_select_left():
    CS1.value(1)
    CS2.value(0)


def glcd_select_right():
    CS1.value(0)
    CS2.value(1)


def glcd_select_both():
    CS1.value(1)
    CS2.value(1)


def glcd_set_page(page):
    glcd_command(0xB8 | (page & 0x07))


def glcd_set_column(column):
    glcd_command(0x40 | (column & 0x3F))


def glcd_init():
    RST.value(0)
    time.sleep_ms(10)
    RST.value(1)
    time.sleep_ms(10)
    glcd_select_both()
    glcd_command(0x3F)
    glcd_command(0xC0)
    glcd_clear()


def glcd_clear():
    for page in range(8):
        glcd_select_left()
        glcd_set_page(page)
        glcd_set_column(0)
        for _ in range(64):
            glcd_data(0x00)
        glcd_select_right()
        glcd_set_page(page)
        glcd_set_column(0)
        for _ in range(64):
            glcd_data(0x00)


FONT = {
    " ": [0x00, 0x00, 0x00, 0x00, 0x00],
    "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
    "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
    "2": [0x42, 0x61, 0x51, 0x49, 0x46],
    "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
    "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
    "5": [0x27, 0x45, 0x45, 0x45, 0x39],
    "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
    "7": [0x01, 0x71, 0x09, 0x05, 0x03],
    "8": [0x36, 0x49, 0x49, 0x49, 0x36],
    "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
    "A": [0x7E, 0x11, 0x11, 0x11, 0x7E],
    "B": [0x7F, 0x49, 0x49, 0x49, 0x36],
    "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C],
    "E": [0x7F, 0x49, 0x49, 0x49, 0x41],
    "F": [0x7F, 0x09, 0x09, 0x09, 0x01],
    "G": [0x3E, 0x41, 0x49, 0x49, 0x7A],
    "H": [0x7F, 0x08, 0x08, 0x08, 0x7F],
    "I": [0x00, 0x41, 0x7F, 0x41, 0x00],
    "J": [0x20, 0x40, 0x41, 0x3F, 0x01],
    "K": [0x7F, 0x08, 0x14, 0x22, 0x41],
    "L": [0x7F, 0x40, 0x40, 0x40, 0x40],
    "M": [0x7F, 0x02, 0x0C, 0x02, 0x7F],
    "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],
    "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],
    "P": [0x7F, 0x09, 0x09, 0x09, 0x06],
    "Q": [0x3E, 0x41, 0x51, 0x21, 0x5E],
    "R": [0x7F, 0x09, 0x19, 0x29, 0x46],
    "S": [0x46, 0x49, 0x49, 0x49, 0x31],
    "T": [0x01, 0x01, 0x7F, 0x01, 0x01],
    "U": [0x3F, 0x40, 0x40, 0x40, 0x3F],
    "V": [0x1F, 0x20, 0x40, 0x20, 0x1F],
    "W": [0x7F, 0x20, 0x18, 0x20, 0x7F],
    "X": [0x63, 0x14, 0x08, 0x14, 0x63],
    "Y": [0x07, 0x08, 0x70, 0x08, 0x07],
    "Z": [0x61, 0x51, 0x49, 0x45, 0x43]
}


def create_framebuffer():
    return [[0 for _ in range(128)] for _ in range(64)]


def draw_char(framebuffer, x, y, ch):
    if ch not in FONT:
        ch = " "
    bitmap = FONT[ch]
    for col in range(5):
        byte = bitmap[col]
        for row in range(7):
            if byte & (1 << row):
                px = x + col
                py = y + row
                if 0 <= px < 128 and 0 <= py < 64:
                    framebuffer[py][px] = 1


def draw_text(framebuffer, x, y, text):
    cursor = x
    for ch in text:
        draw_char(framebuffer, cursor, y, ch)
        cursor += 6


def framebuffer_to_glcd(framebuffer):
    for page in range(8):
        glcd_select_left()
        glcd_set_page(page)
        glcd_set_column(0)
        for x in range(64):
            value = 0
            for bit in range(8):
                y = page * 8 + bit
                if framebuffer[y][x]:
                    value |= 1 << bit
            glcd_data(value)
        glcd_select_right()
        glcd_set_page(page)
        glcd_set_column(0)
        for x in range(64, 128):
            value = 0
            for bit in range(8):
                y = page * 8 + bit
                if framebuffer[y][x]:
                    value |= 1 << bit
            glcd_data(value)


def draw_receive_page(count):
    framebuffer = create_framebuffer()

    draw_text(framebuffer, 22, 3, "NIBP SYSTEM")
    draw_text(framebuffer, 16, 17, "RECEIVING DATA")
    draw_text(framebuffer, 34, 31, "COUNT " + str(count))
    draw_text(framebuffer, 22, 45, "PLEASE WAIT")

    framebuffer_to_glcd(framebuffer)


def receive_samples():
    samples = []
    print("")
    print("========================================")
    print("NIBP FINAL MAIN")
    print("RECEIVING DATA")
    print("========================================")

    # Show an explicit status page while waiting for UART samples.
    draw_receive_page(0)

    start = time.ticks_ms()
    last_display_count = -10

    while len(samples) < EXPECTED_SAMPLES:
        if uart.any():
            line = uart.readline()
            if line is None:
                continue
            try:
                text = line.decode().strip()
                if text == "":
                    continue

                # Sender transmits: pressure,oscillometric_signal
                # Stage 10 uses only the first value: cuff pressure.
                if "," in text:
                    parts = text.split(",")
                    pressure_value = float(parts[0])
                else:
                    pressure_value = float(text)

                samples.append(pressure_value)
                uart.write(b"OK\n")

                current_count = len(samples)

                # Update the GLCD every 10 samples and at the final sample.
                # This keeps the UART reception path fast enough while the
                # display visibly proves that the system is working.
                if (
                    current_count - last_display_count >= 10
                    or current_count == EXPECTED_SAMPLES
                ):
                    draw_receive_page(current_count)
                    last_display_count = current_count

            except Exception:
                pass

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("Received =", len(samples))
    print("Expected =", EXPECTED_SAMPLES)
    print("RX TIME =", elapsed, "ms")
    return samples


B = [0.256915601248463, 0.0, -0.770746803745390, 0.0, 0.770746803745390, 0.0, -0.256915601248463]
A = [1.0, 0.0, -0.577240524806303, 0.0, 0.421787048689562, 0.0, -0.056297236491843]


def reflect_pad_odd(x, padlen):
    n = len(x)
    padded = []
    for i in range(padlen, 0, -1):
        padded.append(2.0 * x[0] - x[i])
    for value in x:
        padded.append(value)
    for i in range(n - 2, n - padlen - 2, -1):
        padded.append(2.0 * x[-1] - x[i])
    return padded


def filter_forward(x):
    y = [0.0] * len(x)
    for n in range(len(x)):
        acc = 0.0
        for k in range(len(B)):
            if n - k >= 0:
                acc += B[k] * x[n - k]
        for k in range(1, len(A)):
            if n - k >= 0:
                acc -= A[k] * y[n - k]
        y[n] = acc / A[0]
    return y


def filtfilt_portable(x):
    padded = reflect_pad_odd(x, PADLEN)
    y = filter_forward(padded)
    y.reverse()
    y = filter_forward(y)
    y.reverse()
    return y[PADLEN:PADLEN + len(x)]


def median(values):
    if len(values) == 0:
        return 0.0
    data = values[:]
    data.sort()
    n = len(data)
    if n % 2 == 1:
        return data[n // 2]
    return (data[n // 2 - 1] + data[n // 2]) / 2.0


def calculate_prominence(signal, index):
    peak = signal[index]
    left_min = peak
    right_min = peak
    i = index - 1
    while i >= 0:
        if signal[i] > peak:
            break
        if signal[i] < left_min:
            left_min = signal[i]
        i -= 1
    i = index + 1
    while i < len(signal):
        if signal[i] > peak:
            break
        if signal[i] < right_min:
            right_min = signal[i]
        i += 1
    return peak - max(left_min, right_min)


def detect_peaks(signal):
    # Golden detector works on the absolute oscillometric waveform.
    # This captures both positive maxima and negative troughs.
    abs_signal = []
    for value in signal:
        abs_signal.append(abs(value))

    # STEP 1: local maxima on absolute signal
    candidates = []
    n = len(abs_signal)
    for i in range(1, n - 1):
        if (
            abs_signal[i] > abs_signal[i - 1]
            and
            abs_signal[i] >= abs_signal[i + 1]
        ):
            candidates.append(i)

    # STEP 2: distance first, strongest first
    candidates.sort(
        key=lambda idx: abs_signal[idx],
        reverse=True
    )

    selected = []
    for idx in candidates:
        too_close = False
        for existing in selected:
            if abs(idx - existing) < MIN_PEAK_DISTANCE_SAMPLES:
                too_close = True
                break
        if not too_close:
            selected.append(idx)

    # STEP 3: prominence on absolute signal
    prominent = []
    for idx in selected:
        prominence = calculate_prominence(abs_signal, idx)
        if prominence >= PEAK_PROMINENCE:
            prominent.append(
                (idx, abs_signal[idx], prominence)
            )

    # STEP 4: chronological order
    prominent.sort(key=lambda x: x[0])
    return [item[0] for item in prominent]


def build_valid_pulses(samples, filtered, peak_indices):
    pulses = []
    for idx in peak_indices:
        pressure = samples[idx]
        amplitude = abs(filtered[idx])
        if PRESSURE_MIN <= pressure <= PRESSURE_MAX and amplitude >= MIN_AMPLITUDE:
            pulses.append({"sample_index": idx, "time": idx / FS, "cuff_pressure": pressure, "amplitude": amplitude})
    return pulses


def find_max_pressure(pulses):
    max_index = 0
    max_pressure = pulses[0]["cuff_pressure"]
    for i in range(1, len(pulses)):
        if pulses[i]["cuff_pressure"] > max_pressure:
            max_pressure = pulses[i]["cuff_pressure"]
            max_index = i
    return max_index, max_pressure


def find_deflation_start(pulses, max_pressure_idx):
    for i in range(max_pressure_idx, len(pulses) - 1):
        current_p = pulses[i]["cuff_pressure"]
        future_p = pulses[i + 1]["cuff_pressure"]
        drop = current_p - future_p
        if drop >= DEFLECTION_MIN_DROP:
            end_check = min(i + 4, len(pulses) - 1)
            future_segment = []
            for j in range(i, end_check + 1):
                future_segment.append(pulses[j]["cuff_pressure"])
            if len(future_segment) >= 2:
                overall_drop = future_segment[0] - future_segment[-1]
                if overall_drop >= 0:
                    return i
    return max_pressure_idx


def pressure_direction(pulses):
    diffs = []
    for i in range(1, len(pulses)):
        diffs.append(pulses[i]["cuff_pressure"] - pulses[i - 1]["cuff_pressure"])
    med = median(diffs)
    if med < 0:
        return "decreasing"
    if med > 0:
        return "increasing"
    return "unknown"


def remove_pressure_reversals(pulses, direction):
    if len(pulses) == 0:
        return pulses, 0
    result = [pulses[0]]
    removed = 0
    for i in range(1, len(pulses)):
        delta = pulses[i]["cuff_pressure"] - pulses[i - 1]["cuff_pressure"]
        reversal = False
        if direction == "decreasing" and delta > MAX_ALLOWED_REVERSAL:
            reversal = True
        elif direction == "increasing" and delta < -MAX_ALLOWED_REVERSAL:
            reversal = True
        if reversal:
            removed += 1
        else:
            result.append(pulses[i])
    return result, removed


def remove_amplitude_outliers(pulses):
    if len(pulses) == 0:
        return pulses, 0, 0.0, 0.0, 0.0
    amplitudes = [pulse["amplitude"] for pulse in pulses]
    global_median = median(amplitudes)
    lower = global_median * AMPLITUDE_RATIO_MIN
    upper = global_median * AMPLITUDE_RATIO_MAX
    result = []
    removed = 0
    for pulse in pulses:
        amp = pulse["amplitude"]
        if lower <= amp <= upper:
            result.append(pulse)
        else:
            removed += 1
    return result, removed, global_median, lower, upper


def apply_median3(pulses):
    n = len(pulses)
    output = []
    for i in range(n):
        values = []
        start = max(0, i - 1)
        end = min(n - 1, i + 1)
        for j in range(start, end + 1):
            values.append(pulses[j]["amplitude"])
        p = pulses[i].copy()
        p["amplitude_median3"] = median(values)
        output.append(p)
    return output


def sort_final_pulses(pulses, direction):
    if direction == "decreasing":
        pulses.sort(key=lambda p: p["cuff_pressure"], reverse=True)
    else:
        pulses.sort(key=lambda p: p["cuff_pressure"])
    return pulses


def build_envelope(pulses):
    groups = {}
    for pulse in pulses:
        pressure = pulse["cuff_pressure"]
        if pressure not in groups:
            groups[pressure] = []
        groups[pressure].append(pulse["amplitude_median3"])
    envelope = []
    keys = list(groups.keys())
    keys.sort()
    for pressure in keys:
        values = groups[pressure]
        envelope.append({"pressure": pressure, "amplitude": median(values), "count": len(values)})
    return envelope


SG = [
    [0.885714285714286, 0.257142857142857, -0.085714285714286, -0.142857142857143, 0.085714285714286],
    [0.257142857142857, 0.371428571428571, 0.342857142857143, 0.171428571428571, -0.142857142857143],
    [-0.085714285714286, 0.342857142857143, 0.485714285714286, 0.342857142857143, -0.085714285714286],
    [-0.142857142857143, 0.171428571428571, 0.342857142857143, 0.371428571428571, 0.257142857142857],
    [0.085714285714286, -0.142857142857143, -0.085714285714286, 0.257142857142857, 0.885714285714286]
]


def savgol_smooth(values):
    n = len(values)
    if n < 5:
        return values[:]
    output = [0.0] * n
    for i in range(5):
        acc = 0.0
        coeffs = SG[i]
        for j in range(5):
            acc += coeffs[j] * values[j]
        output[i] = acc
    for i in range(5, n - 2):
        acc = 0.0
        for j in range(5):
            acc += SG[2][j] * values[i - 2 + j]
        output[i] = acc
    acc = 0.0
    for j in range(5):
        acc += SG[3][j] * values[n - 5 + j]
    output[n - 2] = acc
    acc = 0.0
    for j in range(5):
        acc += SG[4][j] * values[n - 5 + j]
    output[n - 1] = acc
    return output


def calculate_map(envelope):
    pressures = []
    amplitudes = []
    for point in envelope:
        pressures.append(point["pressure"])
        amplitudes.append(point["amplitude"])
    smoothed = savgol_smooth(amplitudes)
    max_index = 0
    for i in range(1, len(smoothed)):
        if smoothed[i] > smoothed[max_index]:
            max_index = i
    provisional_map = int(pressures[max_index])
    return provisional_map, max_index, smoothed


def interpolate_pressure(p1, a1, p2, a2, target):
    if a2 == a1:
        return p1
    return p1 + (target - a1) * (p2 - p1) / (a2 - a1)


def calculate_sbp_dbp(envelope, smoothed, map_index):

    n = len(envelope)

    if n < 3 or map_index < 0 or map_index >= len(smoothed):
        return 0, 0, 0.0, 0.0, 0.0

    amax = smoothed[map_index]

    if amax <= 0:
        return 0, 0, amax, 0.0, 0.0

    sbp_target = SBP_RATIO * amax
    dbp_target = DBP_RATIO * amax

    # =========================================================
    # SBP
    # Higher-pressure side of MAP.
    # The envelope is sorted in ascending pressure, so move
    # forward from MAP toward higher pressures.
    # =========================================================

    sbp = 0.0

    for i in range(map_index, n - 1):

        a1 = smoothed[i]
        a2 = smoothed[i + 1]

        if a1 >= sbp_target and a2 < sbp_target:

            p1 = envelope[i]["pressure"]
            p2 = envelope[i + 1]["pressure"]

            sbp = interpolate_pressure(
                p1,
                a1,
                p2,
                a2,
                sbp_target
            )

            break

    # SBP fallback: nearest point on the higher-pressure side.
    if sbp <= 0.0 and map_index < n - 1:

        best_i = map_index + 1
        best_error = abs(
            smoothed[best_i] - sbp_target
        )

        for i in range(map_index + 1, n):

            error = abs(
                smoothed[i] - sbp_target
            )

            if error < best_error:
                best_error = error
                best_i = i

        sbp = envelope[best_i]["pressure"]

    # =========================================================
    # DBP
    # Lower-pressure side of MAP.
    # Move backward from MAP toward lower pressures.
    # =========================================================

    dbp = 0.0

    for i in range(map_index, 0, -1):

        a_low = smoothed[i - 1]
        a_high = smoothed[i]

        if a_low < dbp_target and a_high >= dbp_target:

            p_low = envelope[i - 1]["pressure"]
            p_high = envelope[i]["pressure"]

            dbp = interpolate_pressure(
                p_low,
                a_low,
                p_high,
                a_high,
                dbp_target
            )

            break

    # DBP fallback: nearest point on the lower-pressure side.
    if dbp <= 0.0 and map_index > 0:

        best_i = map_index - 1
        best_error = abs(
            smoothed[best_i] - dbp_target
        )

        for i in range(map_index - 1, -1, -1):

            error = abs(
                smoothed[i] - dbp_target
            )

            if error < best_error:
                best_error = error
                best_i = i

        dbp = envelope[best_i]["pressure"]

    # Round to nearest integer mmHg.
    if sbp > 0:
        sbp = int(sbp + 0.5)

    if dbp > 0:
        dbp = int(dbp + 0.5)

    # Final pressure-order sanity check.
    map_pressure = envelope[map_index]["pressure"]

    if sbp <= map_pressure:
        sbp = 0

    if dbp >= map_pressure:
        dbp = 0

    return (
        sbp,
        dbp,
        amax,
        sbp_target,
        dbp_target
    )


def draw_waveform(filtered):
    framebuffer = create_framebuffer()
    draw_text(framebuffer, 2, 1, "NIBP WAVE")
    y_top = 14
    y_bottom = 62
    height = y_bottom - y_top
    fmin = min(filtered)
    fmax = max(filtered)
    if fmax == fmin:
        fmax = fmin + 1.0
    n = len(filtered)
    previous_x = None
    previous_y = None
    for i in range(n):
        if n <= 1:
            x = 0
        else:
            x = int(i * 127 / (n - 1))
        normalized = (filtered[i] - fmin) / (fmax - fmin)
        y = int(y_bottom - normalized * height)
        if y < y_top:
            y = y_top
        if y > y_bottom:
            y = y_bottom
        framebuffer[y][x] = 1
        if previous_x is not None:
            dx = x - previous_x
            dy = y - previous_y
            steps = max(abs(dx), abs(dy))
            if steps > 0:
                for s in range(steps + 1):
                    px = previous_x + int(dx * s / steps)
                    py = previous_y + int(dy * s / steps)
                    if 0 <= px < 128 and y_top <= py <= y_bottom:
                        framebuffer[py][px] = 1
        previous_x = x
        previous_y = y
    framebuffer_to_glcd(framebuffer)


def draw_result_page(systolic, diastolic, provisional_map):
    framebuffer = create_framebuffer()
    draw_text(framebuffer, 28, 2, "NIBP RESULT")
    draw_text(framebuffer, 34, 17, "SYS " + str(systolic))
    draw_text(framebuffer, 34, 30, "DIA " + str(diastolic))
    draw_text(framebuffer, 34, 43, "MAP " + str(provisional_map))
    framebuffer_to_glcd(framebuffer)


def golden_validation(peak_indices, valid_count, max_pressure, max_sample_index, pre_deflation_removed, direction, reversal_removed, amplitude_outliers, final_count, envelope_count, provisional_map):
    golden_peaks = [2, 6, 12, 18, 24, 32, 35, 44, 48, 56, 61, 67, 73, 80, 84, 89, 94, 98, 102, 106, 110, 114, 117, 125, 129, 136, 141, 146, 152, 157, 161, 166, 172]
    print("")
    print("========================================")
    print("GOLDEN VALIDATION")
    print("========================================")
    checks = []
    checks.append((peak_indices == golden_peaks, "Peak indices"))
    checks.append((valid_count == 24, "Valid pulses"))
    checks.append((int(max_pressure) == 132, "Maximum pressure"))
    checks.append((max_sample_index == 102, "Maximum pressure index"))
    checks.append((pre_deflation_removed == 9, "Pre-deflation removed"))
    checks.append((direction == "decreasing", "Direction"))
    checks.append((reversal_removed == 2, "Pressure reversals"))
    checks.append((amplitude_outliers == 0, "Amplitude outliers"))
    checks.append((final_count == 13, "Final pulses"))
    checks.append((envelope_count == 13, "Envelope points"))
    checks.append((provisional_map == 101, "Provisional MAP"))
    all_pass = True
    for passed, name in checks:
        if passed:
            print(name, ": PASS")
        else:
            print(name, ": FAIL")
            all_pass = False
    print("")
    if all_pass:
        print("FINAL VALIDATION: PASS")
    else:
        print("FINAL VALIDATION: FAIL")
    return all_pass


def main():
    glcd_init()
    samples = receive_samples()
    if len(samples) != EXPECTED_SAMPLES:
        print("ERROR: SAMPLE COUNT")
        while True:
            time.sleep_ms(1000)
    print("")
    print("SAMPLE COUNT: PASS")

    print("")
    print("FILTERING...")
    start = time.ticks_ms()
    filtered = filtfilt_portable(samples)
    filter_time = time.ticks_diff(time.ticks_ms(), start)
    print("FILTER TIME =", filter_time, "ms")

    print("")
    print("PEAK DETECTION...")
    start = time.ticks_ms()
    peak_indices = detect_peaks(filtered)
    peak_time = time.ticks_diff(time.ticks_ms(), start)
    print("PEAK DETECTION TIME =", peak_time, "ms")
    print("CANDIDATE PEAKS =", len(peak_indices))
    print("PEAK INDICES =", peak_indices)

    pulses = build_valid_pulses(samples, filtered, peak_indices)
    print("VALID PULSES =", len(pulses))
    if len(pulses) == 0:
        print("ERROR: NO VALID PULSES")
        while True:
            time.sleep_ms(1000)

    max_pressure_pulse_idx, max_pressure = find_max_pressure(pulses)
    max_sample_index = pulses[max_pressure_pulse_idx]["sample_index"]
    max_time = max_sample_index / FS
    print("MAX PRESSURE =", int(max_pressure))
    print("MAX PRESSURE SAMPLE =", max_sample_index)
    print("MAX PRESSURE TIME =", max_time)
    print("MAX PRESSURE PULSE INDEX =", max_pressure_pulse_idx)

    deflation_idx = find_deflation_start(pulses, max_pressure_pulse_idx)
    deflation_sample = pulses[deflation_idx]["sample_index"]
    deflation_pressure = pulses[deflation_idx]["cuff_pressure"]
    print("DEFLATION PULSE INDEX =", deflation_idx)
    print("DEFLATION SAMPLE =", deflation_sample)
    print("DEFLATION PRESSURE =", int(deflation_pressure))

    before = len(pulses)
    pulses = pulses[deflation_idx:]
    pulses = pulses[:]
    pre_deflation_removed = before - len(pulses)
    print("PRE-DEFLATION REMOVED =", pre_deflation_removed)

    direction = pressure_direction(pulses)
    print("DIRECTION =", direction)

    pulses, reversal_removed = remove_pressure_reversals(pulses, direction)
    print("PRESSURE REVERSALS REMOVED =", reversal_removed)

    pulses, amplitude_outliers, global_median, lower, upper = remove_amplitude_outliers(pulses)
    print("GLOBAL MEDIAN AMPLITUDE =", "{:.6f}".format(global_median))
    print("AMPLITUDE LOWER =", "{:.6f}".format(lower))
    print("AMPLITUDE UPPER =", "{:.6f}".format(upper))
    print("AMPLITUDE OUTLIERS REMOVED =", amplitude_outliers)

    pulses = apply_median3(pulses)
    pulses = sort_final_pulses(pulses, direction)
    print("FINAL PULSES =", len(pulses))

    print("")
    print("FINAL PULSE TABLE")
    print("INDEX  PRESSURE  AMPLITUDE  MEDIAN3")
    for pulse in pulses:
        print(pulse["sample_index"], "{:.3f}".format(pulse["cuff_pressure"]), "{:.6f}".format(pulse["amplitude"]), "{:.6f}".format(pulse["amplitude_median3"]))

    envelope = build_envelope(pulses)
    print("")
    print("ENVELOPE POINTS =", len(envelope))

    if len(envelope) >= MIN_PULSES_FOR_ENVELOPE:
        provisional_map, map_index, smoothed = calculate_map(envelope)
    else:
        provisional_map = 0
        map_index = 0
        smoothed = []

    print("PROVISIONAL MAP =", provisional_map)
    print("MAP ENVELOPE INDEX =", map_index)

    if len(envelope) >= MIN_PULSES_FOR_ENVELOPE and len(smoothed) == len(envelope):
        systolic, diastolic, amax, sbp_target, dbp_target = calculate_sbp_dbp(envelope, smoothed, map_index)
    else:
        systolic = 0
        diastolic = 0
        amax = 0.0
        sbp_target = 0.0
        dbp_target = 0.0

    print("")
    print("========================================")
    print("STAGE 9 - SBP / DBP")
    print("========================================")
    print("Amax =", "{:.6f}".format(amax))
    print("SBP TARGET =", "{:.6f}".format(sbp_target))
    print("DBP TARGET =", "{:.6f}".format(dbp_target))
    print("SBP =", systolic)
    print("DBP =", diastolic)

    if systolic > 0 and diastolic > 0 and systolic > provisional_map and provisional_map > diastolic:
        pressure_order_valid = True
    else:
        pressure_order_valid = False
    print("PRESSURE ORDER =", pressure_order_valid)

    print("")
    print("SMOOTHED ENVELOPE")
    for i in range(len(envelope)):
        print(int(envelope[i]["pressure"]), "{:.6f}".format(envelope[i]["amplitude"]), "->", "{:.6f}".format(smoothed[i]))

    validation = golden_validation(
        peak_indices,
        len(build_valid_pulses(samples, filtered, peak_indices)),
        max_pressure,
        max_sample_index,
        pre_deflation_removed,
        direction,
        reversal_removed,
        amplitude_outliers,
        len(pulses),
        len(envelope),
        provisional_map
    )

    print("")
    print("========================================")
    print("DISPLAY PAGE 1")
    print("WAVEFORM")
    print("========================================")
    draw_waveform(filtered)
    print("WAVEFORM DISPLAYED")
    time.sleep_ms(WAVEFORM_DISPLAY_TIME_MS)

    print("")
    print("========================================")
    print("DISPLAY PAGE 2")
    print("RESULT")
    print("========================================")
    draw_result_page(systolic, diastolic, provisional_map)
    print("RESULT DISPLAYED")
    print("")
    print("========================================")
    if validation:
        print("FINAL SYSTEM VALIDATION: PASS")
    else:
        print("FINAL SYSTEM VALIDATION: FAIL")
    print("PRESSURE ORDER VALIDATION =", pressure_order_valid)
    print("SYSTEM WILL REMAIN ON RESULT PAGE")
    print("========================================")
    while True:
        time.sleep_ms(1000)


main()
