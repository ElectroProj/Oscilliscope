# esp32-mini-scope

A small open‑source single‑channel oscilloscope built around an ESP32.  The project combines a robust analog front end for safe signal acquisition, firmware that samples the ESP32’s ADC via the I²S peripheral, and a host application that serves a web‑based user interface over localhost.  Everything is meant to look and behave like a real hardware+firmware+software project.

## Overview

This repository contains three main components:

- **Hardware design** – An analog front end that protects the ESP32’s ADC and scales input signals.  It provides over‑voltage protection, selectable 1×/10× attenuation, AC coupling with a mid‑bias node, a rail‑to‑rail buffer op‑amp, and a simple RC anti‑alias filter.  The design is described in `hardware/README.md` and includes a bill of materials and schematic.
- **Firmware** – An ESP‑IDF application that continuously samples an ADC1 channel using the I²S driver in DMA mode.  Samples are packed into frames and streamed over the UART as a binary protocol.  The sample rate, frame size, and calibration factors can be configured in menuconfig or compile‑time defines.  See `firmware/main/app_main.c` for details.
- **Localhost UI** – A Python host application that reads frames from the serial port, serves static files, and streams data to a browser via WebSocket.  The browser UI renders waveforms on an HTML `<canvas>` at 20–60 FPS and provides controls for run/stop, trigger mode and level, volts/div, and time/div.  Instructions for running the host and UI are in `docs/localhost-ui.md`.

## Circuit

![Analog front-end schematic](screenshots/circuit-front-end.png)

## Quick start

### 1. Build the analog front end

Follow the guide in `hardware/README.md` to assemble the input protection and scaling network.  By default the firmware is configured to sample from GPIO34 (ADC1_CH6), but any ADC1 channel can be used if you update the `ADC1_CHANNEL_USED` define in the firmware.

**Safety:** Never connect the circuit to mains voltages or sources above the recommended limits — this project is for low‑voltage educational experiments only.

### 2. Set up the ESP‑IDF toolchain

Ensure you have ESP‑IDF v5 (or newer) installed.  Clone this repository and build the firmware:

```sh
cd firmware
idf.py set-target esp32
idf.py menuconfig      # optional: adjust SAMPLE_RATE_HZ and FRAME_SAMPLES
idf.py build
idf.py flash
idf.py monitor         # to view debug output and binary packets
```

The firmware outputs binary frames to stdout. When using the host server, stop the monitor to free the serial port.

### 3. Run the localhost UI

The host application requires Python 3.8 or newer. It reads the binary stream from the ESP32, parses frames using the documented protocol, and provides a WebSocket feed to the browser.

```sh
cd tools/host
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Adjust --port and --baud for your platform: /dev/ttyUSB0 on Linux, COM3 on Windows
python server.py --port /dev/ttyUSB0 --baud 115200
```

Open your browser to `http://127.0.0.1:8000`. The page will automatically connect via WebSocket and start displaying the waveform. Use the UI controls to adjust volts/div, time/div, trigger mode (auto/normal/single), and trigger level. Status indicators show the sample rate, frame size, frames per second (FPS), dropped frame count, and serial connection status.

### 4. Calibration

The ESP32 ADC is not perfectly linear or accurate. You can compensate by adjusting the gain and offset in the firmware or in the host.

- **Firmware:** modify `ADC_GAIN` and `ADC_OFFSET_COUNTS` in `firmware/main/app_main.c`.
- **Host:** use the volts/div control to match a known reference voltage.

Additional calibration tips are provided in `docs/protocol.md`.

## Repository contents

```
esp32-mini-scope/
├── README.md          – This file
├── LICENSE            – Project license (MIT)
├── CHANGELOG.md       – Summary of notable changes
├── .gitignore         – Git exclusions for ESP‑IDF, Python, and Node
├── hardware/
│   ├── README.md      – Analog front end design documentation
│   ├── BOM.csv        – Bill of materials
│   └── schematic_ascii.txt – ASCII schematic diagram
├── firmware/
│   ├── CMakeLists.txt        – Top‑level CMake for ESP‑IDF
│   ├── sdkconfig.defaults    – Default configuration (sample rate etc.)
│   └── main/
│       ├── app_main.c        – Firmware entry point
│       ├── Kconfig           – Menuconfig options
│       └── CMakeLists.txt    – Component CMake
├── tools/
│   └── host/
│       ├── server.py         – Serial to WebSocket bridge
│       ├── protocol.py       – Packet parser and utilities
│       ├── requirements.txt  – Python dependencies
│       └── test_protocol.py  – Simple unit test for protocol parsing
├── web/
│   ├── index.html      – Web UI
│   ├── app.js          – Canvas rendering and control logic
│   └── style.css       – UI styles
├── docs/
│   ├── protocol.md    – Detailed explanation of the serial protocol
│   └── localhost-ui.md – Setup, usage, and troubleshooting for the host UI
├── .github/
│   └── workflows/
│       └── build.yml   – GitHub Actions workflow (linting & CI)
└── screenshots/
    ├── circuit-front-end.png – Circuit schematic used in this README
    └── ui-placeholder.png    – Placeholder image for the Web UI
```

## Contributing

Contributions to improve the hardware design, firmware, or host UI are welcome. Please open issues or pull requests on GitHub. When adding new features, update the documentation and add relevant tests. See the CI workflow in `.github/workflows/build.yml` for guidelines on code formatting and static analysis.

## License

This project is released under the MIT License. See `LICENSE` for the full license text.
