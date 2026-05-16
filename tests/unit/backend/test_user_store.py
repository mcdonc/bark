"""Tests for user_store: users, workspaces, messages, port allocations."""

import pytest

from backend import user_store


class TestUsers:
    async def test_create_user(self, db):
        user = await user_store.create_user("alice", "hash123")
        assert user["username"] == "alice"
        assert "id" in user

    async def test_get_user_by_username(self, user):
        found = await user_store.get_user_by_username("testuser")
        assert found is not None
        assert found["id"] == user["id"]

    async def test_get_user_by_username_not_found(self, db):
        found = await user_store.get_user_by_username("nonexistent")
        assert found is None

    async def test_get_user_by_id(self, user):
        found = await user_store.get_user_by_id(user["id"])
        assert found is not None
        assert found["username"] == "testuser"

    async def test_get_user_by_id_not_found(self, db):
        found = await user_store.get_user_by_id("fake-id")
        assert found is None


class TestWorkspaces:
    async def test_create_workspace(self, user):
        ws = await user_store.create_workspace(user["id"], "my-workspace")
        assert ws["name"] == "my-workspace"
        assert ws["user_id"] == user["id"]
        assert "id" in ws

    async def test_list_workspaces(self, user):
        await user_store.create_workspace(user["id"], "ws1")
        await user_store.create_workspace(user["id"], "ws2")
        workspaces = await user_store.list_workspaces(user["id"])
        names = [ws["name"] for ws in workspaces]
        assert "ws1" in names
        assert "ws2" in names

    async def test_get_workspace(self, workspace, user):
        found = await user_store.get_workspace(workspace["id"], user["id"])
        assert found is not None
        assert found["name"] == "test-workspace"

    async def test_get_workspace_wrong_user(self, workspace):
        found = await user_store.get_workspace(workspace["id"], "wrong-user-id")
        assert found is None

    async def test_delete_workspace(self, workspace, user):
        deleted = await user_store.delete_workspace(workspace["id"], user["id"])
        assert deleted is True
        found = await user_store.get_workspace(workspace["id"], user["id"])
        assert found is None

    async def test_delete_workspace_not_found(self, user):
        deleted = await user_store.delete_workspace("fake-id", user["id"])
        assert deleted is False

    async def test_duplicate_workspace_name(self, user):
        await user_store.create_workspace(user["id"], "unique-name")
        with pytest.raises(Exception):
            await user_store.create_workspace(user["id"], "unique-name")


class TestMessages:
    async def test_save_and_get_messages(self, workspace):
        await user_store.save_message(workspace["id"], "user", "hello")
        await user_store.save_message(workspace["id"], "assistant", "hi there")
        messages = await user_store.get_messages(workspace["id"])
        assert len(messages) == 2
        assert messages[0]["entry_type"] == "user"
        assert messages[0]["content"] == "hello"
        assert messages[1]["entry_type"] == "assistant"

    async def test_messages_cascade_on_workspace_delete(self, workspace, user):
        await user_store.save_message(workspace["id"], "user", "test")
        await user_store.delete_workspace(workspace["id"], user["id"])
        messages = await user_store.get_messages(workspace["id"])
        assert len(messages) == 0


class TestPortAllocations:
    async def test_add_and_get_ports(self, workspace):
        await user_store.add_port_allocations(workspace["id"], [9000, 9001, 9002])
        ports = await user_store.get_workspace_ports(workspace["id"])
        assert ports == [9000, 9001, 9002]

    async def test_get_all_allocated_ports(self, workspace):
        await user_store.add_port_allocations(workspace["id"], [9000, 9001])
        all_ports = await user_store.get_all_allocated_ports()
        assert 9000 in all_ports
        assert 9001 in all_ports

    async def test_remove_ports(self, workspace):
        await user_store.add_port_allocations(workspace["id"], [9000, 9001, 9002])
        await user_store.remove_port_allocations(workspace["id"], [9001])
        ports = await user_store.get_workspace_ports(workspace["id"])
        assert ports == [9000, 9002]

    async def test_ports_cascade_on_workspace_delete(self, workspace, user):
        await user_store.add_port_allocations(workspace["id"], [9000, 9001])
        await user_store.delete_workspace(workspace["id"], user["id"])
        ports = await user_store.get_workspace_ports(workspace["id"])
        assert ports == []

    async def test_duplicate_port_rejected(self, workspace, user):
        await user_store.add_port_allocations(workspace["id"], [9000])
        # Create second workspace
        ws2 = await user_store.create_workspace(user["id"], "ws2")
        with pytest.raises(Exception):
            await user_store.add_port_allocations(ws2["id"], [9000])
