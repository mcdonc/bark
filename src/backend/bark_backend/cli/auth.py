"""Login / logout — authenticate and store JWT."""

from __future__ import annotations


import httpx
from rich.console import Console
from rich.prompt import Prompt

from .config import CLIConfig

_err = Console(stderr=True)
_out = Console()


def login(
    server_url: str,
    email: str | None = None,
    password: str | None = None,
) -> None:
    """Prompt for credentials, store JWT in config."""
    cfg = CLIConfig.load()

    # If we already have a token for this server, verify it first.
    if cfg.auth.token and cfg.server.url == server_url:
        try:
            resp = httpx.get(
                f"{server_url}/workspaces",
                headers={"Authorization": f"Bearer {cfg.auth.token}"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                _out.print(
                    f"Already logged in as"
                    f" [bold]{cfg.auth.email or 'unknown'}[/bold]"
                )
                return
        except httpx.HTTPError:
            pass  # Token invalid or server unreachable — fall through to prompt

    email = email or Prompt.ask("[bold]Email[/bold]")
    password = password or Prompt.ask("[bold]Password[/bold]", password=True)

    resp = httpx.post(
        f"{server_url}/auth/login",
        json={"email": email, "password": password},
        timeout=15.0,
    )
    if resp.status_code != 200:
        detail = resp.json().get("detail", resp.text)
        _err.print(f"[red]Login failed:[/red] {detail}")
        raise SystemExit(1)

    token = resp.json()["access_token"]

    cfg.server.url = server_url
    cfg.auth.token = token
    cfg.auth.email = email
    cfg.save()
    _out.print(f"Logged in as [bold]{email}[/bold]")


def logout() -> None:
    """Clear stored token."""
    cfg = CLIConfig.load()
    if cfg.auth.token:
        token = cfg.auth.token
        # Clear local state first, then notify server.
        cfg.auth.token = None
        cfg.auth.email = None
        cfg.save()
        try:
            httpx.post(
                f"{cfg.server.url}/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
        except httpx.HTTPError:
            _err.print(
                "[yellow]Logged out locally[/yellow]"
                " — server logout failed (network error)"
            )
            return
    else:
        cfg.save()
    _out.print("Logged out")
