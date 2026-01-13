"""Unit tests for the protocol parser.

Run with pytest or python -m unittest to ensure that the parser correctly extracts frames
from concatenated byte streams.  This minimal test helps catch regressions in
packet handling logic.
"""

import struct

from . import protocol


def test_parse_single_frame() -> None:
    # Create a single frame with 3 samples: 100, 200, 300
    samples = [100, 200, 300]
    sample_bytes = struct.pack("<3H", *samples)
    header = struct.pack(
        protocol.HDR_FMT,
        protocol.MAGIC,
        1,  # frame_counter
        len(samples),
        0,  # flags
    )
    data = header + sample_bytes
    frames = list(protocol.parse_stream(data))
    assert len(frames) == 1
    hdr, payload = frames[0]
    assert hdr.frame_counter == 1
    assert hdr.sample_count == 3
    assert list(struct.unpack("<3H", payload)) == samples


def test_parse_concatenated_frames() -> None:
    # Create two back‑to‑back frames
    frames_bytes = bytearray()
    for idx, samples in enumerate([[1, 2], [10, 20, 30, 40]]):
        payload = struct.pack(f"<{len(samples)}H", *samples)
        header = struct.pack(
            protocol.HDR_FMT,
            protocol.MAGIC,
            idx,
            len(samples),
            0,
        )
        frames_bytes += header + payload
    parsed = list(protocol.parse_stream(bytes(frames_bytes)))
    assert len(parsed) == 2
    # Check first frame
    hdr0, pay0 = parsed[0]
    assert hdr0.frame_counter == 0
    assert hdr0.sample_count == 2
    assert list(struct.unpack("<2H", pay0)) == [1, 2]
    # Check second frame
    hdr1, pay1 = parsed[1]
    assert hdr1.frame_counter == 1
    assert hdr1.sample_count == 4
    assert list(struct.unpack("<4H", pay1)) == [10, 20, 30, 40]