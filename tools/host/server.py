"""Serial‑to‑WebSocket bridge for esp32-mini-scope.

This script reads binary frames from an ESP32 over a serial port and exposes
them to a browser via a FastAPI WebSocket endpoint.  It also serves the static
frontend located in the repository’s `web` directory.  See docs/localhost-ui.md
for usage instructions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import struct
import threading
from pathlib import Path
from queue import Queue
from typing import Set

import serial
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from . import protocol

app = FastAPI()

# Queued frames from the serial reader
frame_queue: Queue[tuple[protocol.FrameHeader, bytes]] = Queue()

# Set of connected WebSocket clients
clients: Set[WebSocket] = set()

# Serial configuration – these are set at runtime via CLI args
SERIAL_PORT: str | None = None
SERIAL_BAUD: int = 115200


def serial_reader(port: str, baud: int) -> None:
    """Background thread that reads frames from the serial port and puts them on the queue."""
    try:
        ser = serial.Serial(port, baud, timeout=1)
    except serial.SerialException as exc:
        print(f"Failed to open serial port {port}: {exc}")
        return
    for header, payload in protocol.iter_frames(ser):
        frame_queue.put((header, payload))


async def frame_dispatcher() -> None:
    """Async task that dispatches frames from the queue to all connected WebSocket clients."""
    loop = asyncio.get_running_loop()
    while True:
        # Blocking get in thread pool to avoid blocking event loop
        header, payload = await loop.run_in_executor(None, frame_queue.get)
        # Unpack payload into a list of ints
        try:
            samples = list(struct.unpack(f"<{header.sample_count}H", payload))
        except struct.error:
            # Skip malformed payloads
            continue
        message = {
            "frame": header.frame_counter,
            "sample_count": header.sample_count,
            "flags": header.flags,
            "samples": samples,
        }
        # Broadcast to all clients
        disconnected: set[WebSocket] = set()
        for ws in clients:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                disconnected.add(ws)
        # Remove disconnected clients
        for ws in disconnected:
            clients.discard(ws)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections from the browser."""
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            # Keep the connection alive by awaiting messages; we don’t currently process client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)


def mount_static(app: FastAPI) -> None:
    """Mount the web directory as static files at the root path."""
    # Compute the path to the 'web' folder relative to this file.  tools/host/server.py
    # -> repo_root = ../../
    current = Path(__file__).resolve()
    repo_root = current.parent.parent.parent
    web_dir = repo_root / "web"
    if not web_dir.is_dir():
        raise RuntimeError(f"Cannot locate web directory at {web_dir}")
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")


@app.on_event("startup")
async def startup_event() -> None:
    """Start the serial reader thread and frame dispatcher when the app launches."""
    # Start serial reader thread
    if SERIAL_PORT is None:
        print("No serial port specified; server will run without serial input")
    else:
        t = threading.Thread(target=serial_reader, args=(SERIAL_PORT, SERIAL_BAUD), daemon=True)
        t.start()
    # Start frame dispatcher task
    asyncio.create_task(frame_dispatcher())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="esp32-mini-scope host server")
    parser.add_argument("--port", required=True, help="Serial port (e.g. /dev/ttyUSB0 or COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address for HTTP/WebSocket server")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP port for web UI (default: 8000)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global SERIAL_PORT, SERIAL_BAUD
    SERIAL_PORT = args.port
    SERIAL_BAUD = args.baud
    # Mount static files before starting server
    mount_static(app)
    # Enable CORS for localhost convenience
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    # Run Uvicorn
    uvicorn.run(app, host=args.host, port=args.http_port, log_level="info")


if __name__ == "__main__":
    main()