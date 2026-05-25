"""Bark CLI — typer app."""

from __future__ import annotations


import asyncio
import logging

import typer

from .auth import login, logout as do_logout
from .client import BarkClient, WorkspaceNotFoundError, _ws_shell
from .config import CLIConfig

app = typer.Typer(
    name="bark",
    help="Bark — containerized development shell.",
    rich_markup_mode="rich",
)

_cfg_cache: CLIConfig | None = None


def _cfg() -> CLIConfig:
    global _cfg_cache  # pragma: no cover
    if _cfg_cache is None:  # pragma: no cover
        _cfg_cache = CLIConfig.load()  # pragma: no cover
    return _cfg_cache


def _client() -> BarkClient:  # pragma: no cover
    return BarkClient(_cfg())


def _require_auth() -> None:
    cfg = _cfg()
    if not cfg.auth.token:
        logging.error("Not logged in — run bark login first.")
        raise typer.Exit(code=1)


@app.command()
def login_cmd(
    server: str | None = typer.Option(
        None,
        "--server",
        help="Bark server URL (e.g. http://localhost:8997)",
    ),
) -> None:
    """Authenticate with the Bark server."""
    if server is None:  # pragma: no cover
        server = _cfg().server.url
    login(server)


@app.command()
def logout() -> None:
    """Clear stored credentials."""
    do_logout()


@app.command()
def status() -> None:
    """Show connection info (server, user)."""
    cfg = _cfg()
    if cfg.auth.token:
        typer.echo(f"Server:   {cfg.server.url}")
        typer.echo(f"Logged in as: {cfg.auth.email or 'unknown'}")
    else:
        typer.echo(f"Server:   {cfg.server.url}")
        typer.echo("Not logged in — run bark login to authenticate.")


@app.command("workspaces")
def list_workspaces() -> None:
    """List all workspaces."""
    _require_auth()
    client = _client()
    workspaces = client.list_workspaces()
    if not workspaces:
        typer.echo("No workspaces found.")
        return
    for ws in workspaces:
        typer.echo(f"  {ws.name}  ({ws.id[:12]})  {ws.created_at[:10]}")


@app.command()
def create(
    name: str = typer.Argument(..., help="Workspace name"),
) -> None:
    """Create a new workspace."""
    _require_auth()
    ws = _client().create_workspace(name)
    typer.echo(f"Created workspace {name} ({ws.id[:12]})")


@app.command()
def delete(
    name: str = typer.Argument(..., help="Workspace name"),
) -> None:
    """Delete a workspace."""
    _require_auth()
    _client().delete_workspace(name)
    typer.echo(f"Deleted workspace {name}")


@app.command()
def shell(
    workspace: str | None = typer.Argument(
        None, help="Workspace name (or select interactively)"
    ),
) -> None:
    """Connect to a workspace and drop into a bash shell."""
    cfg = _cfg()
    if not cfg.auth.token:  # pragma: no cover
        logging.error(
            "Not logged in — run bark login first."
        )  # pragma: no cover
        raise typer.Exit(code=1)  # pragma: no cover

    client = _client()

    # Resolve workspace
    if workspace:
        try:
            ws = client.resolve_workspace(workspace)
        except WorkspaceNotFoundError:  # pragma: no cover
            logging.error("No workspace named '%s'", workspace)
            raise typer.Exit(code=1) from None
    else:
        workspaces = client.list_workspaces()
        if not workspaces:
            typer.echo("No workspaces found — create one with bark create.")
            raise typer.Exit(code=1)
        if len(workspaces) == 1:
            ws = workspaces[0]
        else:
            typer.echo("Select a workspace:")
            for i, w in enumerate(workspaces, 1):
                typer.echo(f"  {i}. {w.name}")
            choice = input("> ").strip()
            if not choice:  # pragma: no cover
                raise typer.Exit()
            try:
                idx = int(choice) - 1
            except ValueError:  # pragma: no cover
                raise typer.Exit(code=1)  # pragma: no cover
            ws = workspaces[idx]

    # Build WebSocket URL
    server_url = cfg.server.url.rstrip("/")
    if server_url.startswith("http://"):
        ws_url = server_url.replace("http://", "ws://") + "/ws"
    elif server_url.startswith("https://"):  # pragma: no cover
        ws_url = server_url.replace("https://", "wss://") + "/ws"
    else:  # pragma: no cover
        ws_url = f"ws://{server_url}/ws"

    token = cfg.auth.token
    logging.info("Connecting to %s...", ws.name)
    asyncio.run(_ws_shell(ws_url, token, ws.id))


if __name__ == "__main__":  # pragma: no cover
    app()
