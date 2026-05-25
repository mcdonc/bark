"""HTTP + WebSocket client for the Bark backend."""

from __future__ import annotations


import asyncio
import json
import logging
import os
import sys
import termios
import tty
from dataclasses import dataclass

import httpx
import websockets

from .config import CLIConfig


@dataclass
class Workspace:
    id: str
    name: str
    created_at: str


def _get_terminal_size() -> tuple[int, int]:
    """Return (columns, rows) of the local terminal, or a sensible default."""
    if sys.stdin.isatty():
        size = os.get_terminal_size()
        return size.columns, size.lines
    return 80, 24


class BarkClient:
    def __init__(self, cfg: CLIConfig):
        self.cfg = cfg

    # --- HTTP helpers ---

    def _headers(self) -> dict[str, str]:
        token = self.cfg.auth.token or ""
        return {"Authorization": f"Bearer {token}"}

    def get(self, path: str, **kwargs) -> httpx.Response:  # pragma: no cover
        return httpx.get(
            f"{self.cfg.server.url}{path}",
            headers=self._headers(),
            timeout=15.0,
            **kwargs,
        )

    def post(self, path: str, **kwargs) -> httpx.Response:  # pragma: no cover
        return httpx.post(
            f"{self.cfg.server.url}{path}",
            headers=self._headers(),
            timeout=15.0,
            **kwargs,
        )

    def delete(
        self, path: str, **kwargs
    ) -> httpx.Response:  # pragma: no cover
        return httpx.delete(
            f"{self.cfg.server.url}{path}",
            headers=self._headers(),
            timeout=15.0,
            **kwargs,
        )

    # --- REST API ---

    def list_workspaces(self) -> list[Workspace]:
        resp = self.get("/workspaces")
        if resp.status_code == 401:
            raise AuthError("Not logged in — run `bark login`")
        resp.raise_for_status()
        raw = resp.json()
        # (workspace listing is tested via test_list_workspaces_empty, test_resolve_workspace_by_name, etc.)
        return [
            Workspace(id=w["id"], name=w["name"], created_at=w["created_at"])
            for w in raw
        ]

    def create_workspace(self, name: str) -> Workspace:  # pragma: no cover
        resp = self.post("/workspaces", params={"name": name})
        if resp.status_code == 401:
            raise AuthError("Not logged in — run `bark login`")
        resp.raise_for_status()
        w = resp.json()
        return Workspace(
            id=w["id"], name=w["name"], created_at=w["created_at"]
        )

    def resolve_workspace(self, name: str) -> Workspace:
        """Find a workspace by name. Raises WorkspaceNotFoundError if not found."""
        ws = self.list_workspaces()
        match = next((w for w in ws if w.name == name), None)
        if match is None:
            raise WorkspaceNotFoundError(name)
        return match

    def delete_workspace(self, name: str) -> None:
        ws = self.resolve_workspace(name)
        resp = self.delete(f"/workspaces/{ws.id}")
        if resp.status_code == 401:
            raise AuthError("Not logged in — run `bark login`")
        if not resp.is_success:
            logging.error("Failed to delete workspace: %s", resp.text)
            sys.exit(1)


class WorkspaceNotFoundError(Exception):
    pass


class AuthError(Exception):
    pass


# --- Shell session ---


def _raw_mode_enter() -> object:
    """Enter raw mode on stdin.  Returns opaque old-settings object."""
    return termios.tcgetattr(sys.stdin)


def _raw_mode_exit(old_settings: object) -> None:
    """Restore terminal from a previous _raw_mode_enter call."""
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


async def _ws_shell(
    ws_url: str,
    token: str,
    workspace_id: str,
    raw_mode: bool = True,
) -> None:
    """Run the interactive PTY shell over WebSocket.

    raw_mode controls whether stdin is placed in raw (cbreak) mode.
    Pass False in tests or when stdin is not a real terminal.
    """
    async with websockets.connect(
        f"{ws_url}?token={token}", max_size=2**20
    ) as ws:
        # 1. Connect to workspace
        await ws.send(
            json.dumps(
                {"cmd": "workspace_connect", "workspaceId": workspace_id}
            )
        )
        resp = json.loads(await ws.recv())
        if resp.get("type") != "workspace_ready":
            raise ConnectionError(f"Connection failed: {resp}")

        # 1b. Signal UI is ready so the backend can deliver pending status.
        await ws.send(json.dumps({"cmd": "ui_ready"}))

        # 2. Start terminal
        cols, rows = _get_terminal_size()
        await ws.send(
            json.dumps({"cmd": "terminal_start", "cols": cols, "rows": rows})
        )

        # 3. Drain the initial clear sequence
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("type") == "terminal_output":
                break
            msg_type = msg.get("type") or msg.get(
                "cmd", "unknown"
            )  # pragma: no cover
            logging.debug(
                "[discarded startup message: %s]", msg_type
            )  # pragma: no cover

        # 4. Put terminal in raw mode, run shell, restore
        # raw_mode path: tcgetattr + tty.setraw + _raw_mode_exit + terminal_stop  # pragma: no cover
        if raw_mode:
            old_settings = _raw_mode_enter()
            tty.setraw(sys.stdin)
        try:
            await _run_shell(ws, cols, rows)
        finally:
            if raw_mode:
                _raw_mode_exit(old_settings)
        await ws.send(json.dumps({"cmd": "terminal_stop"}))  # pragma: no cover


async def _run_shell(ws, cols: int, rows: int) -> None:
    """Run stdin/stdout forwarding loop with SIGWINCH support."""
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    _current_cols = [cols]
    _current_rows = [rows]

    async def _send_resize() -> None:
        await ws.send(
            json.dumps(
                {
                    "cmd": "terminal_resize",
                    "cols": _current_cols[0],
                    "rows": _current_rows[0],
                }
            )
        )

    async def stdin_loop() -> None:
        try:
            while not stop_event.is_set():
                data = await loop.run_in_executor(
                    None, sys.stdin.buffer.read, 1
                )
                if not data:
                    break
                await ws.send(
                    json.dumps(
                        {
                            "cmd": "terminal_input",
                            "data": data.decode("utf-8", errors="replace"),
                        }
                    )
                )
        except (BrokenPipeError, OSError):  # stdin closed mid-stream
            pass

    async def stdout_loop() -> None:
        while not stop_event.is_set():
            msg = await ws.recv()
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8", errors="replace")
            data = json.loads(msg)
            if data.get("type") == "terminal_output":
                sys.stdout.write(data["data"])
                sys.stdout.flush()
            elif data.get("type") == "event":
                event = data.get("event", {})
                if (
                    event.get("type") == "CUSTOM"
                    and event.get("name") == "container_stopped"
                ):
                    logging.info("[container stopped]")
                    stop_event.set()
                    break
        stop_event.set()

    async def resize_loop() -> None:
        while not stop_event.is_set():
            await asyncio.sleep(1)
            new_cols, new_rows = _get_terminal_size()
            if new_cols != _current_cols[0] or new_rows != _current_rows[0]:
                _current_cols[0] = new_cols
                _current_rows[0] = new_rows
                await _send_resize()

    await asyncio.gather(stdin_loop(), stdout_loop(), resize_loop())
