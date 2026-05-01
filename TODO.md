# TODO

## Upstream Investigation

### ACP Python SDK: Race Conditions During Agent Teardown
- **File:** `freecad/acpclient/core/client.py`
- **Methods:** `_async_disconnect`, `_async_connect`
- **Issue:** The `spawn_agent_process` context manager in the ACP Python SDK (`acp-sdk`) may exhibit race conditions when `close_session()` and `__aexit__()` are called while the agent is still processing a prompt. Specifically:
  1. `close_session()` sends a JSON-RPC message to the agent process over stdio. If the agent process is in the middle of streaming a response, the underlying stdio pipe may be in an inconsistent state.
  2. `__aexit__()` terminates the agent process. If stdout/stderr buffers still contain unread data, `proc.terminate()` may not cleanly drain the pipe, potentially causing the asyncio event loop to see a `ConnectionResetError` that is only partly handled.
- **Impact:** On disconnect while the agent is mid-response, the user may see a brief error message before the `disconnected` signal fires. In some cases, the asyncio event loop may log an unhandled exception from the stdio transport.
- **Action:** File an issue on the ACP Python SDK repository at https://github.com/agentclientprotocol/python-sdk requesting that `spawn_agent_process.__aexit__` include a drain-and-cancel step before terminating the subprocess, and that `close_session` accept a timeout parameter.
- **Workaround:** Our `_async_disconnect` wraps both calls in broad `try/except` blocks and emits `disconnected` unconditionally afterward. This prevents the error from reaching the user but may mask underlying transport errors that could be useful for debugging.

### Thread Safety of cross-thread signal emission
- **File:** `freecad/acpclient/core/client.py:ACPClientThread`
- **Note:** Qt signals emitted from a non-main thread are automatically queued if the receiver lives on the main thread. This is correct behavior per Qt documentation. Our `message_received`, `error_occurred`, `connected`, `disconnected`, `processing_started`, and `processing_finished` signals all follow this pattern.

## Planned Features for v1.1

- [ ] **qasync migration** — Replace manual QThread with qasync.QEventLoop for simpler async/Qt integration
- [ ] **i18n support** — Wrap all user-facing strings with QT_TRANSLATE_NOOP
- [ ] **Remote agent support** — HTTP/WebSocket transport in addition to stdio
- [ ] **Session persistence** — Remember last agent command and connection history in FreeCAD params
- [ ] **Agent mode/model switching** — Expose set_session_mode / set_session_model in UI
- [ ] **Cancel button** — Wire stop button to conn.cancel(session_id)
- [ ] **Streaming token display** — Render session_update text chunks incrementally
- [ ] **Dark/light theme adaptation** — Adapt chat bubble colors to FreeCAD stylesheet

## Known Limitations

- **No pytest-qt integration** — Controller tests require a running QApplication, which is only available inside FreeCAD. Unit testing the full ACPController is deferred until pytest-qt can be integrated with FreeCAD's headless mode.
- **`_is_first_prompt` flag** — System instructions are injected by prepending to the first user message. Moving this to a dedicated session setup step has been deferred to v1.1.
- **Single agent connection** — The architecture supports only one agent at a time. Multiple concurrent agents would require instantiating multiple ACPClientThread instances.
