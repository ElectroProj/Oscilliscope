# Changelog

All notable changes to this project will be documented in this file.  The format is based on [Keep a Changelog](https://keepachangelog.com/) and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] – 2026‑01‑13

### Added

- Initial public release of **esp32‑mini‑scope**.
- Documentation for the analog front end including a bill of materials and ASCII schematic.
- ESP‑IDF firmware that samples ADC1 via I²S DMA and streams binary frames over UART.
- Python host server (`tools/host/server.py`) and WebSocket‑based browser UI (`web/`).
- Detailed protocol specification and localhost UI setup notes in `docs/`.
- Basic GitHub Actions workflow for building the firmware, running Python lint, and executing unit tests.