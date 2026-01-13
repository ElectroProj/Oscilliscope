# Serial protocol

The ESP32 firmware streams sampled data over UART using a simple, self‑describing binary packet format.  Each packet contains a fixed 4‑byte magic header, a frame counter, a sample count, flags/reserved field, and a payload of 16‑bit samples.  The host application reads bytes from the serial port, synchronises to the magic header, and then parses frames accordingly.

## Packet layout

| Field          | Type    | Size (bytes) | Description                                    |
|--------------- |---------|--------------|------------------------------------------------ |
| `magic`        | char[4] | 4            | ASCII literal **"SCOP"** to mark frame start    |
| `frame_count`  | `uint32`| 4            | Monotonic counter incremented every frame       |
| `sample_count` | `uint16`| 2            | Number of valid samples in the payload          |
| `flags`        | `uint16`| 2            | Reserved for future use (currently zero)        |
| `samples`      | `uint16[n]`| 2 × *n*  | Raw ADC counts, length given by `sample_count`  |

All multi‑byte fields are little‑endian.  In code, the header can be represented with a packed C structure or `struct` in Python:

```c
typedef struct __attribute__((packed)) {
    char magic[4];       // "SCOP"
    uint32_t frame_counter;
    uint16_t sample_count;
    uint16_t flags;
} scope_pkt_hdr_t;
```

The maximum `sample_count` is constrained by the DMA buffer length configured in the firmware (`FRAME_SAMPLES`).  If fewer words are returned by `i2s_read`, the `sample_count` field reflects the actual number of samples sent.

## Synchronisation

The host must search for the four‑byte `magic` sequence to align with frame boundaries.  If `magic` appears in the data stream but the next header fields are invalid (e.g. implausible `sample_count`), the host discards bytes until a valid header is found.  This resynchronisation logic is implemented in `tools/host/protocol.py`.

## Calibration

ESP32 ADC readings are 12‑bit values packed into 16‑bit words.  The raw counts range from 0 (approx. 0 V) to 4095 (approx. 3.3 V) when using the 11 dB attenuation setting.  You can convert a raw sample `s` to voltage using:

```python
voltage = (s / 4095.0) * VREF * GAIN + OFFSET
```

Where:

- `VREF` – The reference voltage of the ADC (~3.3 V).  In ESP‑IDF this may vary and can be calibrated using `esp_adc_cal_characteristics_t` but here we assume 3.3 V.
- `GAIN` – Multiplier to account for the front‑end attenuation (1× or 1/11 of the 10× path) and any op‑amp gain.  Select this in the UI via the volts/div control.
- `OFFSET` – Correction factor for DC offset (ideally zero when the bias network is exactly mid‑scale).  In practice the op‑amp and ADC may have small offsets.

You can choose to apply calibration either in firmware (by scaling counts before transmission) or in the host (by multiplying the sample values).  In firmware the constants `ADC_GAIN` and `ADC_OFFSET` can be adjusted, and the host UI exposes controls for volts/div and time/div to scale the rendering.

## Example packet

Below is an example of a 4‑sample packet in little‑endian hexadecimal.  The frame counter is 42, the sample count is 4, and flags are zero.  The ADC counts are 1000, 1500, 2000, 2500.

```
53 43 4f 50   // magic "SCOP"
2a 00 00 00   // frame_counter = 42
04 00         // sample_count = 4
00 00         // flags = 0
e8 03         // sample[0] = 1000
dc 05         // sample[1] = 1500
d0 07         // sample[2] = 2000
c4 09         // sample[3] = 2500
```

## Error handling

If the host detects a malformed packet (e.g. unexpected `magic`, mismatched payload length, or unreasonable `sample_count`), it should discard bytes until the next valid header is found.  The host code maintains a counter of dropped or bad frames and exposes this in the UI so users can monitor signal integrity.