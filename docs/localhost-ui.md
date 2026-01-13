# Localhost UI

This document describes how to run the Python host server, access the Web UI, and troubleshoot common issues.  The localhost UI provides a real‑time display of waveforms captured by the ESP32 firmware.

## Running the host server

The host application is located in `tools/host/` and requires Python 3.8+ with a few dependencies.  It serves two functions:

1. **Serial reader** – Connects to the ESP32 via the specified serial port and baud rate, reads the binary protocol, and parses frames.
2. **Web server** – Serves the static assets from the `web/` folder (HTML, CSS, JavaScript) at `http://127.0.0.1:8000` and provides a WebSocket endpoint (`/ws`) that pushes parsed frames to connected browsers.

To start the host:

```sh
cd tools/host
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# On Linux/macOS specify the serial device (e.g. /dev/ttyUSB0 or /dev/cuUSB0)
python server.py --port /dev/ttyUSB0 --baud 115200

# On Windows specify the COM port name without quotes
python server.py --port COM3 --baud 115200
```

The default baud rate in the firmware is 115200 bit/s, but you can increase it to 921600 bit/s for higher throughput by changing `CONFIG_MONITOR_BAUD` in `firmware/sdkconfig.defaults` and passing the matching `--baud` argument to the server.

### Notes for Windows

On Windows, Python’s serial library uses names like `COM1`, `COM3`, etc.  Open Device Manager to find the COM port associated with your ESP32.  If you encounter permissions errors, make sure no other program (like the ESP‑IDF `idf.py monitor`) is holding the port open.

### Notes for Linux/macOS

On Linux your ESP32 will appear as `/dev/ttyUSB0` or `/dev/ttyACM0` depending on the USB‑to‑UART chip.  On macOS it may appear as `/dev/cu.SLAB_USBtoUART` or similar.  You might need to add your user to the `dialout` group on Linux or install drivers on macOS.  Run `ls -l /dev/ttyUSB*` to list available devices.

## Opening the UI

Once the server is running you can open a browser and navigate to [`http://127.0.0.1:8000`](http://127.0.0.1:8000).  The UI will attempt to open a WebSocket to `/ws`.  When frames are received, a waveform appears on the canvas and updates at the configured refresh rate.

### Controls

- **Run/Stop** – Pause and resume streaming.  When stopped, the last received frame is frozen.
- **Trigger mode** – Auto, normal, or single.  Auto continuously updates; normal waits for the trigger level crossing; single stops after one triggered frame.
- **Trigger level** – Set the voltage level (relative to mid‑scale) that triggers a new frame.  In auto mode this control is disabled.
- **Volts/Div** – Adjust the vertical scale; multiplies the raw ADC counts to approximate volts.
- **Time/Div** – Adjust the horizontal scale; determines how many samples are displayed per division on the canvas.  Changing this does not alter the sampling rate but rescales the plotted data.
- **Stats** – Displays the current sample rate (from firmware), frame size, frames per second (FPS), number of dropped frames, and whether the serial and WebSocket connections are open.

### Expected latency

The overall latency from signal to display depends on several factors:

- **Sampling and frame accumulation** – With a default frame size of 1024 samples at 200 kS/s, each frame represents 5.12 ms of data.  Increasing the frame size increases both time resolution and latency.
- **UART throughput** – At 115200 bit/s the theoretical maximum is ~11 kB/s.  A 1024‑sample frame is ~2 kB including header, so roughly 5 fps is possible.  Using 921600 bit/s allows ~40 fps.
- **Host processing** – The Python server parses frames and immediately pushes them via WebSocket.  CPU usage is low on modern machines.
- **Browser rendering** – The UI uses requestAnimationFrame to render at up to 60 fps.  If frames arrive slower than the screen refresh rate, the FPS will match the incoming frame rate.

Overall you can expect a latency on the order of tens of milliseconds at 200 kS/s and high baud rates.  Lower sample rates or larger frame sizes will increase latency proportionally.

## Troubleshooting

| Problem                                 | Possible cause / solution                                                   |
|---------------------------------------- |---------------------------------------------------------------------------- |
| **No data in UI, status shows “closed”** | Check that the server is running and the serial port is correct.  Ensure no other program (like `idf.py monitor`) is using the port. |
| **Frequent dropped frames**             | Increase the UART baud rate or decrease the sample rate/frame size in firmware.  Ensure your USB interface and OS can handle the throughput. |
| **Trigger never fires**                 | Adjust the trigger level and set the trigger mode to “Normal” or “Single”.  For signals centered at mid‑scale the trigger level should be set above or below zero appropriately. |
| **UI becomes unresponsive**             | Use a modern browser.  Reload the page after stopping the server.  Check the browser console for errors. |
| **Permission denied on /dev/ttyUSB0**   | On Linux, add your user to the `dialout` group (`sudo usermod -aG dialout $USER`) and reconnect, or run the server with sudo. |
| **Windows antivirus blocks server**     | Some antivirus software may block Python from listening on localhost.  Add an exception or temporarily disable the antivirus. |

For additional questions, see the project README or open an issue.