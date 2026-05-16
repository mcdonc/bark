"""Tests for agui_translator: Pi RPC event to AG-UI event mapping."""

from backend.agui_translator import (
    translate_event,
    _bash_likely_creates_files,
    _extract_content_text,
)


class TestTranslateEvent:
    def test_agent_start(self):
        events = translate_event({"type": "agent_start"}, "ws-1")
        assert len(events) == 1
        assert events[0]["type"] == "RUN_STARTED"
        assert events[0]["threadId"] == "ws-1"
        assert "runId" in events[0]

    def test_agent_end(self):
        events = translate_event({"type": "agent_end"}, "ws-1")
        assert len(events) == 1
        assert events[0]["type"] == "RUN_FINISHED"

    def test_turn_start(self):
        events = translate_event({"type": "turn_start"}, "ws-1")
        assert events[0]["type"] == "STEP_STARTED"
        assert events[0]["stepName"] == "turn"

    def test_message_start(self):
        events = translate_event({
            "type": "message_start",
            "message": {"id": "msg-1"},
        }, "ws-1")
        assert events[0]["type"] == "TEXT_MESSAGE_START"
        assert events[0]["messageId"] == "msg-1"
        assert events[0]["role"] == "assistant"

    def test_message_update_text_delta(self):
        events = translate_event({
            "type": "message_update",
            "message": {"id": "msg-1"},
            "assistantMessageEvent": {"type": "text_delta", "delta": "hello"},
        }, "ws-1")
        assert events[0]["type"] == "TEXT_MESSAGE_CONTENT"
        assert events[0]["delta"] == "hello"

    def test_message_update_thinking_delta(self):
        events = translate_event({
            "type": "message_update",
            "message": {"id": "msg-1"},
            "assistantMessageEvent": {"type": "thinking_delta", "delta": "hmm"},
        }, "ws-1")
        assert events[0]["type"] == "REASONING_MESSAGE_CONTENT"
        assert events[0]["delta"] == "hmm"

    def test_message_end(self):
        events = translate_event({
            "type": "message_end",
            "message": {"id": "msg-1"},
        }, "ws-1")
        assert events[0]["type"] == "TEXT_MESSAGE_END"

    def test_tool_execution_start(self):
        events = translate_event({
            "type": "tool_execution_start",
            "toolCallId": "tc-1",
            "toolName": "bash",
            "args": {"command": "ls -la"},
        }, "ws-1")
        assert events[0]["type"] == "TOOL_CALL_START"
        assert events[0]["toolCallName"] == "bash"
        assert "command=ls -la" in events[0]["toolCallArgs"]

    def test_tool_execution_end(self):
        events = translate_event({
            "type": "tool_execution_end",
            "toolCallId": "tc-1",
            "toolName": "bash",
            "result": {"content": [{"type": "text", "text": "output"}]},
        }, "ws-1")
        assert len(events) == 2
        assert events[0]["type"] == "TOOL_CALL_END"
        assert events[1]["type"] == "TOOL_CALL_RESULT"
        assert events[1]["content"] == "output"

    def test_tool_write_emits_file_changed(self):
        events = translate_event({
            "type": "tool_execution_end",
            "toolCallId": "tc-1",
            "toolName": "write",
            "result": {"content": [{"type": "text", "text": "ok"}]},
        }, "ws-1")
        custom = [e for e in events if e["type"] == "CUSTOM"]
        assert any(e["name"] == "file_changed" for e in custom)

    def test_tool_edit_emits_file_changed(self):
        events = translate_event({
            "type": "tool_execution_end",
            "toolCallId": "tc-1",
            "toolName": "edit",
            "result": {"content": [{"type": "text", "text": "ok"}]},
        }, "ws-1")
        custom = [e for e in events if e["type"] == "CUSTOM"]
        assert any(e["name"] == "file_changed" for e in custom)

    def test_error_event(self):
        events = translate_event({
            "type": "error",
            "message": "something broke",
            "code": 500,
        }, "ws-1")
        assert events[0]["type"] == "RUN_ERROR"
        assert events[0]["message"] == "something broke"

    def test_session_event_skipped(self):
        events = translate_event({"type": "session"}, "ws-1")
        assert events == []

    def test_unknown_event_forwarded_as_custom(self):
        events = translate_event({"type": "mystery_event", "data": 42}, "ws-1")
        assert events[0]["type"] == "CUSTOM"
        assert events[0]["name"] == "pi_mystery_event"

    def test_extension_ui_request(self):
        pi_event = {
            "type": "extension_ui_request",
            "id": "ext-1",
            "method": "input",
            "title": "HOST_TOOL_REQUEST",
        }
        events = translate_event(pi_event, "ws-1")
        assert events[0]["type"] == "CUSTOM"
        assert events[0]["name"] == "extension_ui_request"
        assert events[0]["value"] == pi_event


class TestBashLikelyCreatesFiles:
    def test_mkdir(self):
        assert _bash_likely_creates_files({"args": {"command": "mkdir -p /tmp/foo"}})

    def test_touch(self):
        assert _bash_likely_creates_files({"args": {"command": "touch file.txt"}})

    def test_git_clone(self):
        assert _bash_likely_creates_files({"args": {"command": "git clone https://github.com/foo/bar"}})

    def test_echo_redirect(self):
        assert _bash_likely_creates_files({"args": {"command": 'echo "hi" > output.txt'}})

    def test_ls_does_not(self):
        assert not _bash_likely_creates_files({"args": {"command": "ls -la"}})

    def test_cat_does_not(self):
        assert not _bash_likely_creates_files({"args": {"command": "cat file.txt"}})

    def test_string_args(self):
        assert _bash_likely_creates_files({"args": "mkdir foo"})

    def test_empty_args(self):
        assert not _bash_likely_creates_files({"args": {}})


class TestExtractContentText:
    def test_dict_with_content_list(self):
        assert _extract_content_text({
            "content": [{"type": "text", "text": "hello"}, {"type": "text", "text": " world"}]
        }) == "hello world"

    def test_string_content(self):
        assert _extract_content_text({"content": "plain string"}) == "plain string"

    def test_raw_string(self):
        assert _extract_content_text("just a string") == "just a string"

    def test_none(self):
        assert _extract_content_text(None) == ""

    def test_empty_dict(self):
        assert _extract_content_text({}) == ""

    def test_mixed_content_list(self):
        assert _extract_content_text({
            "content": [{"type": "text", "text": "a"}, "b"]
        }) == "ab"
