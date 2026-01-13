"""Serial packet parsing utilities for esp32-mini-scope.

This module provides helper functions to synchronise with the firmware’s binary
protocol and parse frames.  It abstracts away byte alignment and header
validation.  See docs/protocol.md for the packet format.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import BinaryIO, Generator, Iterable, Tuple

# Packet constants
MAGIC = b"SCOP"
HDR_FMT = "<4sIHH"  # magic, frame_counter, sample_count, flags
HDR_SIZE = struct.calcsize(HDR_FMT)


@dataclass
class FrameHeader:
    """Decoded header fields for a frame."""

    frame_counter: int
    sample_count: int
    flags: int


def _read_exact(stream: BinaryIO, length: int) -> bytes:
    """Read exactly *length* bytes from the stream or raise EOFError."""
    data = bytearray()
    while len(data) < length:
        chunk = stream.read(length - len(data))
        if not chunk:
            raise EOFError("Serial stream ended unexpectedly")
        data.extend(chunk)
    return bytes(data)


def _sync_to_magic(stream: BinaryIO) -> bytes:
    """Read from stream until the MAGIC sequence is found.  Returns the 4 magic bytes
    followed by the remaining header bytes."""
    window = bytearray()
    while True:
        byte = stream.read(1)
        if not byte:
            raise EOFError("Serial stream ended unexpectedly during sync")
        window += byte
        if len(window) > len(MAGIC):
            # Keep a sliding window of the last len(MAGIC) bytes
            del window[0]
        if window == MAGIC:
            # We have aligned to MAGIC; read the rest of the header
            rest = _read_exact(stream, HDR_SIZE - len(MAGIC))
            return MAGIC + rest


def iter_frames(stream: BinaryIO) -> Generator[Tuple[FrameHeader, bytes], None, None]:
    """Continuously read and yield frames from a binary stream.

    Each yielded value is a tuple of (FrameHeader, samples_bytes).  If parsing fails,
    the function resynchronises to the next magic sequence.  The generator runs
    indefinitely until EOFError is raised.
    """
    while True:
        try:
            hdr_bytes = _sync_to_magic(stream)
        except EOFError:
            return
        try:
            magic, frame_counter, sample_count, flags = struct.unpack(HDR_FMT, hdr_bytes)
        except struct.error:
            # Should never happen as header size is fixed
            continue
        if magic != MAGIC:
            # Out of sync; skip and search again
            continue
        # Sanity check on sample_count to avoid allocating huge buffers
        if sample_count <= 0 or sample_count > 4096:
            # Skip this frame; attempt to resync
            continue
        payload_length = sample_count * 2
        try:
            payload = _read_exact(stream, payload_length)
        except EOFError:
            return
        header = FrameHeader(frame_counter=frame_counter, sample_count=sample_count, flags=flags)
        yield (header, payload)


def parse_stream(data: bytes) -> Iterable[Tuple[FrameHeader, bytes]]:
    """Parse one or more concatenated frames from a buffer of bytes.

    This function is useful for unit tests.  It will search for the magic
    sequence within the buffer and yield each complete frame that can be
    extracted.  Incomplete trailing data is ignored.
    """
    frames: list[Tuple[FrameHeader, bytes]] = []
    i = 0
    buf_len = len(data)
    while i + HDR_SIZE <= buf_len:
        # Look for magic
        if data[i : i + 4] != MAGIC:
            i += 1
            continue
        # Potential header
        try:
            magic, frame_counter, sample_count, flags = struct.unpack_from(HDR_FMT, data, i)
        except struct.error:
            break
        total_len = HDR_SIZE + sample_count * 2
        if i + total_len > buf_len:
            # Incomplete frame at end
            break
        payload = data[i + HDR_SIZE : i + total_len]
        header = FrameHeader(frame_counter=frame_counter, sample_count=sample_count, flags=flags)
        frames.append((header, payload))
        i += total_len
    return frames
