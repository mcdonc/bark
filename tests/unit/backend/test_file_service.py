"""Tests for file_service: list, read, write, delete, rename, path traversal."""

import pytest

from backend import file_service, workspace_manager


@pytest.fixture
async def workspace_dir(workspace, user, temp_data_dir):
    """Create the workspace directory on disk and return (user_id, workspace_id, path)."""
    path = workspace_manager.get_workspace_host_path(user["id"], workspace["id"])
    path.mkdir(parents=True, exist_ok=True)
    return user["id"], workspace["id"], path


class TestResolvePathTraversal:
    async def test_normal_path(self, workspace_dir):
        uid, wid, path = workspace_dir
        resolved = file_service.resolve_path(uid, wid, "file.txt")
        assert str(resolved).startswith(str(path))

    async def test_traversal_rejected(self, workspace_dir):
        uid, wid, _ = workspace_dir
        with pytest.raises(ValueError, match="traversal"):
            file_service.resolve_path(uid, wid, "../../etc/passwd")

    async def test_dot_path(self, workspace_dir):
        uid, wid, path = workspace_dir
        resolved = file_service.resolve_path(uid, wid, ".")
        assert resolved == path


class TestWriteAndRead:
    async def test_write_and_read_file(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "hello.txt", b"hello world")
        content = file_service.read_file(uid, wid, "hello.txt")
        assert content == "hello world"

    async def test_write_nested_path(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "sub/dir/file.txt", b"nested")
        content = file_service.read_file(uid, wid, "sub/dir/file.txt")
        assert content == "nested"

    async def test_read_nonexistent(self, workspace_dir):
        uid, wid, _ = workspace_dir
        assert file_service.read_file(uid, wid, "nope.txt") is None

    async def test_read_large_file_returns_none(self, workspace_dir):
        uid, wid, path = workspace_dir
        big_file = path / "big.bin"
        big_file.write_bytes(b"x" * 1_100_000)
        assert file_service.read_file(uid, wid, "big.bin") is None


class TestListFiles:
    async def test_list_empty_dir(self, workspace_dir):
        uid, wid, _ = workspace_dir
        entries = file_service.list_files(uid, wid, ".")
        assert entries == []

    async def test_list_with_files(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "a.txt", b"aaa")
        file_service.write_file(uid, wid, "b.txt", b"bbb")
        entries = file_service.list_files(uid, wid, ".")
        names = [e["name"] for e in entries]
        assert "a.txt" in names
        assert "b.txt" in names

    async def test_list_shows_dirs(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "subdir/file.txt", b"x")
        entries = file_service.list_files(uid, wid, ".")
        dirs = [e for e in entries if e["is_dir"]]
        assert any(d["name"] == "subdir" for d in dirs)


class TestDelete:
    async def test_delete_file(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "doomed.txt", b"bye")
        result = file_service.delete_path(uid, wid, "doomed.txt")
        assert "doomed.txt" in result
        assert file_service.read_file(uid, wid, "doomed.txt") is None

    async def test_delete_directory(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "dir/a.txt", b"a")
        file_service.write_file(uid, wid, "dir/b.txt", b"b")
        file_service.delete_path(uid, wid, "dir")
        entries = file_service.list_files(uid, wid, ".")
        names = [e["name"] for e in entries]
        assert "dir" not in names

    async def test_delete_nonexistent(self, workspace_dir):
        uid, wid, _ = workspace_dir
        with pytest.raises(FileNotFoundError):
            file_service.delete_path(uid, wid, "ghost.txt")


class TestRename:
    async def test_rename_file(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "old.txt", b"content")
        file_service.rename_path(uid, wid, "old.txt", "new.txt")
        assert file_service.read_file(uid, wid, "old.txt") is None
        assert file_service.read_file(uid, wid, "new.txt") == "content"

    async def test_rename_to_existing_fails(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "a.txt", b"a")
        file_service.write_file(uid, wid, "b.txt", b"b")
        with pytest.raises(FileExistsError):
            file_service.rename_path(uid, wid, "a.txt", "b.txt")

    async def test_rename_nonexistent_fails(self, workspace_dir):
        uid, wid, _ = workspace_dir
        with pytest.raises(FileNotFoundError):
            file_service.rename_path(uid, wid, "nope.txt", "new.txt")

    async def test_rename_into_subdirectory(self, workspace_dir):
        uid, wid, _ = workspace_dir
        file_service.write_file(uid, wid, "file.txt", b"data")
        file_service.rename_path(uid, wid, "file.txt", "sub/file.txt")
        assert file_service.read_file(uid, wid, "sub/file.txt") == "data"
