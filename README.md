# NIBP Signal Processing on ESP32

An embedded oscillometric blood-pressure signal-processing prototype implemented on ESP32 using MicroPython, with UART data acquisition, digital filtering, oscillometric pulse analysis, MAP/SBP/DBP estimation, GLCD visualization, and Proteus simulation.

> **Disclaimer:** This project is an engineering and signal-processing prototype. It is **not a medical device**. The reported blood-pressure values are algorithmic outputs from the supplied test dataset and have not been clinically validated or calibrated for medical diagnosis.

---

## 1. Overview

This project implements an end-to-end oscillometric NIBP signal-processing pipeline on an ESP32.

The system receives pressure samples and an oscillometric waveform through UART, processes the signal using embedded DSP algorithms, extracts oscillometric pulses, constructs an oscillometric envelope, estimates mean arterial pressure (MAP), and derives experimental systolic and diastolic pressure estimates.

The final results and filtered waveform are displayed on a 128×64 GLCD.

### Processing pipeline

```text
PC-side NIBP dataset
        │
        │ UART @ 115200 baud
        ▼
ESP32
        │
        ├── Sample reception
        ├── 3rd-order IIR band-pass filtering
        ├── Forward-backward filtering
        ├── Absolute oscillometric peak detection
        ├── Pressure/amplitude validation
        ├── Deflation detection
        ├── Pressure reversal removal
        ├── Amplitude outlier rejection
        ├── Median-3 amplitude smoothing
        ├── Oscillometric envelope construction
        ├── Savitzky-Golay smoothing
        ├── MAP estimation
        └── SBP / DBP estimation
        │
        ├── GLCD waveform
        └── GLCD result
```

---

## 2. Key Features

### Embedded DSP

* ESP32 MicroPython implementation
* 5 Hz pressure-signal processing
* 3rd-order IIR Butterworth band-pass filter
* Fixed filter coefficients for embedded execution
* Forward-backward filtering
* Odd-reflection signal padding
* Absolute oscillometric peak detection
* Peak-distance filtering
* Prominence-based peak validation
* Pressure-range validation
* Deflation detection
* Pressure reversal rejection
* Amplitude outlier rejection
* Median-3 pulse-amplitude smoothing
* Oscillometric envelope construction
* Savitzky-Golay smoothing
* MAP estimation
* SBP/DBP interpolation

### Embedded interface

* ESP32
* MicroPython
* UART
* 128×64 GLCD
* Direct GLCD framebuffer rendering
* Waveform visualization
* Result display

### Development and validation

* PC-side CSV replay
* Golden-dataset regression checks
* Proteus simulation
* Deterministic reference results

---

## 3. Input Data

The current test dataset contains:

```text
Samples:        177
Nominal rate:   5 Hz
Duration:       ~35.4 seconds
```

The PC-side transmitter expects the following CSV columns:

```text
time
pressure
oscillometric_signal
```

The ESP32 currently uses the `pressure` value for the NIBP processing pipeline.

The oscillometric waveform is also transmitted as part of the UART message and is available at the receiver, although the current processing implementation derives the filtered oscillometric signal from the received pressure samples.

---

## 4. UART Communication

The PC transmitter communicates with the ESP32 using:

| Parameter           |     Value |
| ------------------- | --------: |
| Baud rate           |    115200 |
| Data bits           |         8 |
| Parity              |      None |
| Stop bits           |         1 |
| Nominal sample rate |      5 Hz |
| Message format      | ASCII CSV |

Each transmitted sample has the form:

```text
pressure,oscillometric_signal\n
```

Example:

```text
132.500000,0.183421000
```

The ESP32 parses the first field as cuff pressure.

After receiving each valid sample, the ESP32 sends:

```text
OK\n
```

### Current transmitter behavior

The current `test_sender_uart.py` implementation sends samples at the nominal 5 Hz rate but does **not** wait for or process the `OK\n` responses from the ESP32.

Therefore, the current communication architecture should be considered:

**timed one-way sample transmission with receiver-side acknowledgement generation**, rather than a closed-loop ACK-controlled streaming protocol.

A future version could add explicit acknowledgement handling and retransmission/error detection.

---

## 5. Digital Filtering

The firmware uses a 3rd-order IIR Butterworth band-pass filter.

Current nominal passband:

```text
Low cutoff:   0.5 Hz
High cutoff:  2.0 Hz
Sampling:     5 Hz
```

This corresponds approximately to:

```text
30–120 cycles/min
```

The filter coefficients are precomputed and embedded directly in the MicroPython firmware.

This avoids requiring a runtime signal-processing library on the ESP32.

### Forward-backward filtering

The implementation applies the IIR filter in both directions:

```text
Input signal
     │
     ▼
Odd reflection padding
     │
     ▼
Forward IIR filter
     │
     ▼
Reverse
     │
     ▼
Forward IIR filter
     │
     ▼
Reverse
     │
     ▼
Remove padding
     │
     ▼
Filtered signal
```

This is a portable implementation of forward-backward filtering intended to reduce phase distortion.

The padding length is:

```text
PADLEN = 40 samples
```

---

## 6. Oscillometric Peak Detection

Peak detection is performed on the **absolute value of the filtered oscillometric waveform**.

This allows both positive and negative oscillometric excursions to contribute to pulse detection.

### Detection stages

#### Stage 1 — Local maxima

Local maxima are identified in:

```text
abs(filtered_signal)
```

#### Stage 2 — Minimum peak distance

Candidate peaks are sorted by amplitude and selected while enforcing:

```text
Minimum peak distance = 3 samples
```

At 5 Hz this corresponds to approximately:

```text
0.60 seconds
```

#### Stage 3 — Prominence

Each selected peak is evaluated using a local prominence calculation.

Current threshold:

```text
PEAK_PROMINENCE = 0.05
```

#### Stage 4 — Chronological ordering

The accepted peaks are returned in time order for subsequent pulse validation.

---

## 7. Pulse Validation

Each detected peak is converted into a pulse candidate containing:

* Sample index
* Time
* Cuff pressure
* Oscillometric amplitude

A pulse is accepted when its pressure and amplitude satisfy:

```text
50 mmHg ≤ pressure ≤ 180 mmHg
```

and:

```text
amplitude ≥ 0.15
```

The pressure and amplitude constraints reduce the influence of invalid or very small detections.

---

## 8. Deflation Detection

The firmware first identifies the maximum cuff pressure.

The current reference dataset contains a maximum pressure of:

```text
132 mmHg
```

The algorithm then searches for the beginning of the deflation phase.

The minimum pressure drop used for detection is:

```text
DEFLECTION_MIN_DROP = 2.0 mmHg
```

The algorithm also checks the pressure trend over subsequent pulses before accepting the deflation transition.

Samples before the detected deflation point are removed from the oscillometric analysis.

---

## 9. Pressure Reversal Removal

The dominant pressure direction is estimated from the median of successive pressure differences.

For the reference dataset, the detected direction is:

```text
decreasing
```

Pressure reversals greater than:

```text
MAX_ALLOWED_REVERSAL = 1.5 mmHg
```

are rejected.

This provides a simple robustness mechanism against pressure fluctuations or inconsistent samples during the deflation phase.

---

## 10. Amplitude Outlier Removal

After pressure reversal filtering, pulse amplitudes are compared against the global median amplitude.

Current limits are:

```text
Lower limit = 0.25 × median amplitude
Upper limit = 2.50 × median amplitude
```

Pulses outside this range are removed.

The remaining pulse amplitudes are then processed using a 3-point median operation.

This provides lightweight robustness against isolated amplitude anomalies while remaining practical for MicroPython execution.

---

## 11. Oscillometric Envelope

The final pulse set is grouped by cuff pressure.

For each pressure value, the median pulse amplitude is used to construct the oscillometric envelope.

Conceptually:

```text
Cuff pressure
      │
      │
      │       ●
      │      ● ●
      │    ●     ●
      │  ●         ●
      │ ●           ●
      └──────────────────
            Amplitude
```

The resulting envelope represents the relationship between cuff pressure and oscillometric pulse amplitude.

For the current reference dataset:

```text
Final pulses:    13
Envelope points: 13
```

---

## 12. Savitzky-Golay Smoothing

The oscillometric envelope is smoothed using a fixed 5-point, 2nd-order Savitzky-Golay filter.

Configuration:

```text
Window length: 5
Polynomial order: 2
```

The filter coefficients are embedded directly in the firmware.

This avoids dependency on external DSP libraries during ESP32 execution.

---

## 13. MAP Estimation

The maximum of the smoothed oscillometric envelope is used to determine the provisional mean arterial pressure.

Conceptually:

```text
MAP = cuff pressure at maximum envelope amplitude
```

For the current reference dataset:

```text
MAP = 101 mmHg
```

The MAP calculation is therefore an algorithmic estimate based on the oscillometric envelope.

---

## 14. SBP / DBP Estimation

The current prototype estimates systolic and diastolic pressure from fractions of the maximum oscillometric envelope amplitude.

Current configuration:

```text
SBP target = 0.50 × Amax
DBP target = 0.70 × Amax
```

where:

```text
Amax = maximum smoothed envelope amplitude
```

The firmware searches:

* the **higher-pressure side of MAP** for SBP
* the **lower-pressure side of MAP** for DBP

When the target amplitude is crossed between two envelope points, pressure is estimated using linear interpolation.

If the crossing cannot be found, a nearest-point fallback is used.

The final values are rounded to the nearest integer mmHg.

A final pressure-order sanity check requires:

```text
SBP > MAP > DBP
```

for the result to be considered pressure-order valid.

---

## 15. Reference Validation

The firmware contains a deterministic golden-reference validation stage.

The reference dataset expects:

| Validation item              |   Expected |
| ---------------------------- | ---------: |
| Detected peaks               |         33 |
| Valid pulses                 |         24 |
| Maximum pressure             |   132 mmHg |
| Maximum pressure sample      |        102 |
| Pre-deflation pulses removed |          9 |
| Pressure direction           | decreasing |
| Pressure reversals removed   |          2 |
| Amplitude outliers removed   |          0 |
| Final pulses                 |         13 |
| Envelope points              |         13 |
| Provisional MAP              |   101 mmHg |

The firmware compares the actual processing results against these expected values.

If all checks pass:

```text
FINAL VALIDATION: PASS
```

This is **golden-dataset regression validation**. It demonstrates reproducibility of the current implementation against the supplied reference dataset.

It does **not** establish clinical accuracy.

---

## 16. Current Reference Result

For the supplied reference dataset, the validated processing result is:

```text
MAP = 101 mmHg
SBP = 122 mmHg
DBP = 86 mmHg
```

These values are algorithmic outputs from the reference dataset.

They should not be interpreted as measurements demonstrating clinical blood-pressure accuracy.

---

## 17. GLCD Interface

The firmware drives a 128×64 graphical LCD directly from the ESP32.

### Receive page

During UART acquisition, the display shows:

```text
NIBP SYSTEM
RECEIVING DATA
COUNT xxx
PLEASE WAIT
```

The receive counter is updated periodically during data acquisition.

### Waveform page

After processing, the filtered NIBP waveform is rendered across the display.

### Result page

The final display shows:

```text
NIBP RESULT

SYS xxx
DIA xxx
MAP xxx
```

The result page remains active after processing.

---

## 18. Proteus Simulation

The repository includes a Proteus project:

```text
Real NIBP Signal Processing on ESP32.pdsprj
```

The simulation provides an additional hardware-level representation of the ESP32-based NIBP processing system.

Included visual documentation:

```text
proteus-simulation.png
glcd-result.png
```

The repository also includes an annotated demonstration video:

```text
NIBP-ESP32-Proteus-Demo_Annotated.mp4
```

These artifacts document the embedded processing flow and display behavior.

---

## 19. Project Files

```text
NIBP-Signal-Processing-ESP32/
│
├── .gitignore
├── README.md
│
├── main.py
│
├── test_sender_uart.py
│
├── Real NIBP Signal Processing on ESP32.pdsprj
│
├── proteus-simulation.png
├── glcd-result.png
│
└── NIBP-ESP32-Proteus-Demo_Annotated.mp4
```

### `main.py`

ESP32 MicroPython firmware containing:

* UART acquisition
* Digital filtering
* Peak detection
* Pulse validation
* Deflation analysis
* Envelope construction
* MAP estimation
* SBP/DBP estimation
* GLCD rendering
* Golden-dataset validation

### `test_sender_uart.py`

PC-side Python transmitter that:

* Loads the reference CSV
* Validates required columns
* Sends pressure and oscillometric samples through UART
* Maintains a nominal 5 Hz transmission rate
* Reports transmission statistics

---

## 20. Running the Project

### Requirements

* ESP32
* MicroPython
* 128×64 GLCD
* USB/UART connection
* Python 3
* `pyserial`
* Optional: Proteus

Install the Python serial dependency:

```powershell
py -m pip install pyserial
```

### Step 1 — Prepare the CSV

The transmitter expects:

```text
time,pressure,oscillometric_signal
```

### Step 2 — Configure the serial port

Edit the local configuration in:

```text
test_sender_uart.py
```

and set:

```python
COM_PORT = "COM11"
```

Use the serial port assigned to your ESP32.

### Step 3 — Configure the CSV path

Set:

```python
CSV_FILE = r"path\to\record_212_processed_master.csv"
```

The path should point to the local reference dataset.

### Step 4 — Run the transmitter

```powershell
py test_sender_uart.py
```

The ESP32 waits for 177 samples.

After receiving the complete dataset, the firmware automatically performs the processing pipeline and displays the waveform and result.

---

## 21. Validation Status

| Test area                            | Status            |
| ------------------------------------ | ----------------- |
| UART sample reception                | Implemented       |
| CSV input validation                 | Implemented       |
| 5 Hz sample transmission             | Implemented       |
| IIR filtering                        | Implemented       |
| Forward-backward filtering           | Implemented       |
| Oscillometric peak detection         | Implemented       |
| Pulse validation                     | Implemented       |
| Deflation detection                  | Implemented       |
| Pressure reversal removal            | Implemented       |
| Amplitude outlier removal            | Implemented       |
| Oscillometric envelope               | Implemented       |
| Savitzky-Golay smoothing             | Implemented       |
| MAP estimation                       | Implemented       |
| SBP/DBP estimation                   | Implemented       |
| Pressure-order validation            | Implemented       |
| Golden-dataset regression validation | PASS              |
| Proteus simulation                   | Included          |
| GLCD visualization                   | Implemented       |
| Clinical validation                  | Not performed     |
| Quantitative accuracy study          | Not yet completed |

---

## 22. Limitations

This project is intentionally an engineering prototype.

Important limitations include:

* The current validation uses a single reference dataset.
* Golden-dataset validation demonstrates reproducibility, not clinical accuracy.
* The SBP/DBP ratios are fixed empirical parameters.
* No patient-to-patient validation has been performed.
* No comparison against a calibrated clinical NIBP monitor has been performed.
* No formal error metrics such as MAE, RMSE, or Bland-Altman analysis have been completed.
* Motion-artifact robustness has not been systematically evaluated.
* Sensor/pressure transducer characteristics are not part of the current validation.
* The PC transmitter does not currently process the `OK\n` acknowledgements returned by the ESP32.
* The current input path is a replay/test-data architecture rather than direct acquisition from a clinical pressure sensor.
* The algorithm should not be used for medical diagnosis or treatment decisions.

---

## 23. Future Work

### Signal processing

* Adaptive oscillometric pulse detection
* Improved deflation-phase detection
* Robust baseline handling
* Improved artifact rejection
* Adaptive amplitude outlier detection
* Improved envelope interpolation
* Alternative envelope models

### Blood-pressure estimation

* Dataset-based parameter optimization
* Multi-dataset validation
* Quantitative error analysis
* Reference-device comparison
* Bland-Altman analysis
* Subject-to-subject validation
* Improved SBP/DBP estimation models

### Embedded implementation

* Direct pressure-sensor acquisition
* ADC integration
* Hardware timer-based sampling
* DMA-based acquisition
* More deterministic UART handling
* Reduced memory footprint
* DSP performance optimization

### Communication

* Receiver ACK handling in the PC transmitter
* Retransmission support
* Packet framing
* Sequence numbers
* Checksum/CRC
* Communication error reporting

### Testing

* Automated regression tests
* Multiple NIBP datasets
* Noise injection
* Motion-artifact simulation
* Parameter sensitivity testing
* Continuous integration for algorithm regression

---

## 24. Engineering Focus

This project demonstrates an embedded biomedical signal-processing workflow:

```text
Physiological / simulated pressure data
                │
                ▼
          UART acquisition
                │
                ▼
        Embedded DSP filtering
                │
                ▼
      Oscillometric pulse analysis
                │
                ▼
        Envelope extraction
                │
                ▼
       Physiological estimation
                │
                ▼
       Embedded visualization
```

The project combines:

* Biomedical signal processing
* Digital filtering
* Embedded DSP
* MicroPython
* UART communication
* Oscillometric analysis
* Physiological parameter estimation
* GLCD interfacing
* Proteus simulation
* Deterministic regression validation

---

## 25. Project Status

**Current status: Functional embedded NIBP signal-processing prototype**

The current implementation successfully demonstrates:

* End-to-end NIBP signal processing on ESP32
* Embedded IIR filtering
* Oscillometric pulse extraction
* Envelope construction
* MAP estimation
* Experimental SBP/DBP estimation
* GLCD visualization
* Proteus-based system demonstration
* Golden-dataset regression validation

Future development is focused on:

* Broader dataset validation
* Quantitative accuracy analysis
* Improved robustness
* Direct sensor acquisition
* Communication reliability
* More clinically representative validation

---

## 26. License

See [`LICENSE`](LICENSE).
