"""``EventStreamServer``: stream every event as a JSON line to local clients (D8).

A future Mac app connects here. It is just another subscriber: the server's
``handle`` is subscribed to the bus like the sinks are. A client that cannot
keep up is dropped rather than allowed to hold events back.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import stat
from pathlib import Path

from hark.events import Event

logger = logging.getLogger(__name__)

DEFAULT_EVENT_SOCKET = Path.home() / "Library" / "Application Support" / "hark" / "events.sock"


class EventStreamServer:
    def __init__(self, socket_path: Path | str = DEFAULT_EVENT_SOCKET, client_timeout: float = 2.0) -> None:
        self.path = Path(socket_path)
        self._timeout = client_timeout
        self._clients: set[asyncio.StreamWriter] = set()
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        if len(os.fsencode(self.path)) >= 104:  # macOS sun_path limit
            raise ValueError(f"socket path is too long for a Unix socket: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._clear_stale_socket()
        os.chmod(self.path.parent, 0o700)
        self._server = await asyncio.start_unix_server(self._connected, path=str(self.path))
        os.chmod(self.path, 0o600)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for writer in list(self._clients):
            writer.close()
        self._clients.clear()
        self.path.unlink(missing_ok=True)

    async def handle(self, event: Event) -> None:
        """Bus handler: write the event to every connected client."""
        line = json.dumps(event.to_dict()).encode() + b"\n"
        for writer in list(self._clients):
            try:
                writer.write(line)
                await asyncio.wait_for(writer.drain(), self._timeout)
            except (OSError, TimeoutError):
                self._clients.discard(writer)
                writer.close()

    async def _connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._clients.add(writer)
        try:
            await reader.read()  # returns at EOF: the client left
        finally:
            self._clients.discard(writer)
            writer.close()

    def _clear_stale_socket(self) -> None:
        if not self.path.exists():
            return
        if not stat.S_ISSOCK(self.path.stat().st_mode):
            raise RuntimeError(f"{self.path} exists and is not a socket")
        probe = socket.socket(socket.AF_UNIX)
        try:
            probe.settimeout(1.0)
            probe.connect(str(self.path))
        except OSError:
            self.path.unlink()  # nobody is listening: left over from a crash
        else:
            raise RuntimeError(f"another Hark is already streaming on {self.path}")
        finally:
            probe.close()
