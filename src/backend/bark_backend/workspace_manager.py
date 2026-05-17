import os
import shutil
from pathlib import Path

from . import container_manager, user_store

_data_dir = Path(os.environ.get("BARK_DATA_DIR", str(Path.home() / ".bark" / "data")))
WORKSPACES_ROOT = _data_dir / "workspaces"


def _workspace_path(user_id: str, workspace_id: str) -> Path:
    return WORKSPACES_ROOT / user_id / "data" / workspace_id


def _sessions_path(user_id: str, workspace_id: str) -> Path:
    return WORKSPACES_ROOT / user_id / "sessions" / workspace_id


async def create_workspace(user_id: str, name: str) -> dict:
    workspace = await user_store.create_workspace(user_id, name)
    path = _workspace_path(user_id, workspace["id"])
    path.mkdir(parents=True, exist_ok=True)
    sessions = _sessions_path(user_id, workspace["id"])
    sessions.mkdir(parents=True, exist_ok=True)
    # Allocate ports at creation time so ranges are sequential
    await container_manager.allocate_ports(workspace["id"], workspace["num_ports"])
    return workspace


async def list_workspaces(user_id: str) -> list[dict]:
    return await user_store.list_workspaces(user_id)


async def get_workspace(workspace_id: str, user_id: str) -> dict | None:
    return await user_store.get_workspace(workspace_id, user_id)


async def delete_workspace(workspace_id: str, user_id: str) -> bool:
    workspace = await user_store.get_workspace(workspace_id, user_id)
    if workspace is None:
        return False

    deleted = await user_store.delete_workspace(workspace_id, user_id)
    if deleted:
        path = _workspace_path(user_id, workspace_id)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        sessions = _sessions_path(user_id, workspace_id)
        if sessions.exists():
            shutil.rmtree(sessions, ignore_errors=True)
    return deleted


def get_workspace_host_path(user_id: str, workspace_id: str) -> Path:
    path = _workspace_path(user_id, workspace_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sessions_host_path(user_id: str, workspace_id: str) -> Path:
    path = _sessions_path(user_id, workspace_id)
    path.mkdir(parents=True, exist_ok=True)
    return path
