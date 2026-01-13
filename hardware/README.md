# Analog Front‑End

This folder documents the single‑channel analog front end used to safely feed external signals into the ESP32’s ADC.  The goal is to protect the microcontroller, scale typical signals into the ADC range, bias the AC‑coupled waveform around mid‑supply, and buffer the signal to reduce loading.

## Topology

The following stages make up the front end.  See `schematic_ascii.txt` for a visual representation and `BOM.csv` for recommended component values.

1. **Input protection** – A series resistor (`R1`) and transient voltage suppressor diode (`D1`) limit the current and clamp high‑voltage spikes.  Optionally, Schottky diodes to 3.3 V and ground can protect against minor over/under‑voltage.
2. **Selectable attenuation** – A switch (`SW1`) selects between a 1× path (direct) and a 10× path implemented by a resistive divider (`R2`/`R3`).  This allows capturing both small and larger signals while keeping the ADC within its 0–3.3 V range.
3. **AC coupling and biasing** – A coupling capacitor (`C1`) blocks DC from the source.  Two resistors (`R4` and `R5`) form a mid‑bias node at half the supply (≈1.65 V) so the AC waveform is centered in the ADC input range.
4. **Buffer op‑amp** – A rail‑to‑rail op‑amp configured as a unity‑gain voltage follower (e.g. MCP6002, TLV9002, OPA320) provides a low‑impedance drive to the ESP32.  The op‑amp is powered from 3.3 V with proper decoupling (`C2`).
5. **Anti‑alias / noise filter** – A small series resistor (`Rf`) and capacitor (`Cf`) create a first‑order low‑pass filter that attenuates high‑frequency noise before sampling.

The output of the filter connects to an ADC1 channel on the ESP32 (default GPIO34 / ADC1_CH6).  Avoid using ADC2 pins when Wi‑Fi is enabled as they share resources.

## Input range and safety

The selected attenuation and protection components limit the maximum safe input amplitude.  With a 10× divider the ADC sees roughly `1/11` of the input; with 1× the input is passed through.  The ESP32 ADC and op‑amp operate from 0–3.3 V, so signals should not exceed ±15 V on the 10× path or ±3 V on the 1× path.  **Do not connect the scope to mains voltages or any source exceeding these limits.**  Always verify signals with a proper oscilloscope first.

## Calibration and accuracy

The ESP32 ADC is convenient but not precision instrumentation: it has limited resolution, integral and differential non‑linearity, and sample‑to‑sample noise.  To improve accuracy:

- Use the 11 dB attenuation setting in firmware (`ADC_ATTEN_DB_11`) so the ADC covers most of the 0–3.3 V range.
- Average multiple samples in software if you need higher effective resolution (at the cost of bandwidth).
- Adjust the gain and offset constants in firmware or in the host application to match a known reference (e.g. a 1 kHz square wave from a function generator).  See `docs/protocol.md` for details.

## Files

- **`BOM.csv`** – Bill of materials with reference designators, values, and notes.
- **`schematic_ascii.txt`** – An ASCII schematic showing how components are connected.  This can be used alongside your favourite schematic capture program.