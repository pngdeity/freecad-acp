# TODO

## Upstream Investigation

### ACP Python SDK: Race Conditions During Agent Teardown
- **File:** `freecad/acpclient/core/client.py`
- **Methods:** `_async_disconnect` (`client.py:257-277`), `_async_connect` (`client.py:228-250`)
- **Issue:** The `spawn_agent_process` context manager in the ACP Python SDK (`acp-sdk`) may exhibit race conditions when `close_session()` and `__aexit__()` are called while the agent is still processing a prompt. Specifically:
  1. `close_session()` sends a JSON-RPC message to the agent process over stdio. If the agent process is in the middle of streaming a response, the underlying stdio pipe may be in an inconsistent state.
  2. `__aexit__()` terminates the agent process. If stdout/stderr buffers still contain unread data, `proc.terminate()` may not cleanly drain the pipe, potentially causing the asyncio event loop to see a `ConnectionResetError` that is only partly handled.
- **Impact:** On disconnect while the agent is mid-response, the user may see a brief error message before the `disconnected` signal fires at `client.py:277`. In some cases, the asyncio event loop may log an unhandled exception from the stdio transport.
- **Action:** File an issue on the ACP Python SDK repository at https://github.com/agentclientprotocol/python-sdk requesting that `spawn_agent_process.__aexit__` include a drain-and-cancel step before terminating the subprocess, and that `close_session` accept a timeout parameter.
- **Workaround:** `client.py:259-272` — `_async_disconnect` wraps both `close_session()` and `__aexit__()` in broad `try/except` blocks and emits `disconnected` unconditionally afterward. This prevents the error from reaching the user but may mask underlying transport errors that could be useful for debugging.
- **Status: PENDING UPSTREAM** — Issue needs to be filed at the SDK repo. Workaround confirmed in place at `client.py:259-272`.

### Thread Safety of Cross-Thread Signal Emission
- **File:** `freecad/acpclient/core/client.py:ACPClientThread` (`client.py:120-281`)
- **Note:** Qt signals emitted from a non-main thread are automatically queued if the receiver lives on the main thread. This is correct behavior per Qt documentation.
- **Verified:** All `ACPClientThread` signals (`message_received`, `error_occurred`, `connected`, `disconnected`, `processing_started`, `processing_finished`, `request_execute_script`, `request_read_document`, `request_permission_signal`, `request_run_tool`) declared at `client.py:127-137`. All emit from the background asyncio loop (`client.py:36,219,250,277`). All receivers in `ACPController` at `controller.py:26-35` live on the main thread.
- **Status: VERIFIED CORRECT** — No action required.

---

## Planned Features for v1.1

All items below are unimplemented as of 2026-04-30. Each includes the current state of the codebase.

### 1. qasync migration
- **Goal:** Replace manual `QThread` with `qasync.QEventLoop` for simpler async/Qt integration.
- **Current state:** `qasync>=0.27` is declared in `requirements.txt:3` and mocked in `tests/conftest.py:116`, but is **never imported or used** in production code. `ACPClientThread` at `client.py:120` remains a raw `QThread` subclass manually spinning an `asyncio.new_event_loop()` at `client.py:184`.
- **Scope:** Replace `ACPClientThread` with a `QEventLoop` + coroutine approach. Remove manual event loop management. Update `controller.py:25-52` to manage the new lifecycle.
- **Dependencies:** `qasync` is already in `requirements.txt`.

### 2. i18n support
- **Goal:** Wrap all user-facing strings with `QT_TRANSLATE_NOOP`.
- **Current state:** Zero i18n patterns anywhere. All user-facing strings are plain English literals. Key locations:
  - `controller.py:68` — system instruction string
  - `controller.py:79,85,91,96` — status messages ("Connected to Agent.", etc.)
  - `chat_view.py:24` — welcome message
  - `chat_view.py:79` — "Agent is thinking..."
  - `dock_widget.py:18` — "ACP Agent Chat"
  - `dock_widget.py:26` — "Disconnected"
  - `commands.py:14,34,48,68` — menu/toolbar labels and dialog text
- **Scope:** Audit and wrap all user-visible strings (estimated 30-40 strings). Create a translation template. No runtime translation loading until translators contribute.

### 3. Session persistence
- **Goal:** Remember last agent command and connection history in FreeCAD params.
- **Current state:** Zero calls to `FreeCAD.ParamGet`, `App.ParamGet`, or any parameter API anywhere in the codebase. The connect dialog at `commands.py:29` uses a hardcoded default `"gemini --experimental-acp"` with no recall.
- **Scope:** Integrate with `FreeCAD.ParamGet("User parameter:BaseApp/ACP")`. Store last-used command path and a list of recent connections. Load on startup.

### 4. Architectural refactor (per `docs/refactor.md`)
- **Goal:** Four-phase remediation of Separation of Concerns, security, and stability issues.
- **Phase 1 — Unified Tool Registry:** Replace `TOOL_DISPATCH` (`tools.py:283-289`) and `TOOLS_REGISTRY` (`tools.py:318-388`) with a single `ToolDefinition` dataclass. No `@dataclass` usage exists in the codebase today. Migrate `ext_method` (`client.py:90-121`) from if/elif chains to generic dispatch driven by `requires_permission`. ~70 lines of nested dict must be converted.
- **Phase 2 — Agent Session Manager:** Extract prompt formatting and `_is_first_prompt` (`controller.py:38,64-70`) into `core/session.py`. `core/session.py` does not exist yet. Define a `SessionManager` class API and wire it into `ACPController`.
- **Phase 3 — Hardened Thread Bridge:** Add `asyncio.wait_for` timeout to `run_on_main_thread` (`client.py:150-157`). Currently a bare `await fut` at `client.py:153` with no timeout. Must define timeout behavior (cancel future? return error? clean up `pending_requests`?).
- [x] **Phase 4 — Hardened Python Sandbox:** Restrict `__builtins__` in the `exec()` call at `tools.py:98`. `SAFE_BUILTINS` dict added at `tools.py:79` with ~57 safe builtins (types, math, exceptions) in place of full builtins. `__import__`, `open`, `eval`, `exec`, `compile`, `input`, `breakpoint` are blocked. Note residual risk: already-imported modules in scope (`FreeCAD`, `Part`, `Mesh`) remain accessible.
- **Review gaps identified in `docs/refactor.md:86-98`:** (1) post-refactor `ext_method` sketch needed, (2) timeout error path undefined, (3) `read_document_state` bypass treatment ambiguous, (4) sandbox residual risk acknowledged, (5) testing/migration plan missing, (6) `core/session.py` API undefined, (7) registry migration burden acknowledged.
- **Scope of each phase:**
  - Phase 1: ~150 LOC new (`ToolDefinition` + migration), ~50 LOC changed (`ext_method` + `tools.py` callers)
  - Phase 2: ~80 LOC new (`core/session.py`), ~30 LOC changed (`controller.py`)
  - Phase 3: ~20 LOC changed (`client.py:150-157`)
  - Phase 4: ~15 LOC changed (`tools.py:96-98`)

### 5. Agent mode/model switching
- **Goal:** Expose `set_session_mode` / `set_session_model` in UI.
- **Current state:** Zero references to `set_session_mode`, `set_session_model`, or any `model`/`mode` API in the codebase. No such methods exist on `FreeCADACPClient` or in the ACP SDK session interface.
- **Scope:** Requires upstream ACP SDK support. If available, add a dropdown or settings dialog in the UI to select mode/model before/during sessions.

### 6. Cancel button
- [x] **Goal:** Wire stop button to `conn.cancel(session_id)`.
- **Status:** Implemented 2026-04-30. `ACPChatView` at `chat_view.py:38` has a Stop button visible during processing. Wired through `handle_cancel` in `controller.py:79` to `cancel_prompt` in `client.py:204`, which calls `conn.cancel(session_id)`.

### 7. Streaming token display
- **Goal:** Render `session_update` text chunks incrementally (in-place mutation of last message).
- **Current state:** `client.py:35-36` emits the full `.text` of each `AgentMessageChunk` as a discrete signal. `chat_view.py:56-66` appends each chunk as a separate HTML block to `QTextBrowser`. Tokens arrive as distinct appended `<div>` elements, not as in-place edits of a single streaming message.
- **Scope:** Change `chat_view.py` to maintain a "streaming" message block. On first chunk, create a placeholder. On subsequent chunks, mutate the last block's content in-place. On `processing_finished`, finalize the block.

### 8. Dark/light theme adaptation
- **Goal:** Adapt chat bubble colors to FreeCAD stylesheet.
- **Current state:** All colors are hardcoded hex values that will not adapt to dark mode:
  - `dock_widget.py:27` — `"color: #999; ..."` (disconnected label)
  - `controller.py:62,80,85,91,96` — status colors (`"#1a73e8"`, `"#34a853"`, `"#ea4335"`, `"#999"`)
  - `chat_view.py:42` — italic emphasis color `"#1a73e8"`
  - `chat_view.py:70` — user bubble `"#2a7ae2"`, agent bubble `"#555555"`
  - `chat_view.py:24` — hardcoded welcome HTML
- **Scope:** Query `QApplication.style()` / `QApplication.palette()` at widget construction. Derive bubble colors from palette roles (`Window`, `WindowText`, `Highlight`). Reapply on `QEvent.PaletteChange`.

---

## Known Limitations

- **No pytest-qt integration** — `tests/conftest.py:10-80` uses hand-rolled mock Qt classes (`_MockQObject`, `_MockQThread`, `_MockSignal`). No real `QApplication` is created in any test. `ACPController` (the main-thread coordinator) has zero test coverage. Controller tests require a running `QApplication`, which is only available inside FreeCAD. Integrating `pytest-qt` with FreeCAD's headless mode is deferred.
- **`_is_first_prompt` flag** — `controller.py:38,64-70` — System instructions are injected by prepending to the first user message inside `handle_send_message`. Moving this to a dedicated session setup step (Phase 2 of the architectural refactor) is deferred to v1.1.
- **Single agent connection** — `controller.py:25` creates a single `ACPClientThread` instance; `ACPController` has a 1:1 relationship with the dock widget at `dock_widget.py:34`. Multiple concurrent agents would require instantiating multiple `ACPClientThread` instances with independent session management.

---

## Completed (since initial release)

- [x] **CI Pipeline** — `Makefile` (18 lines, provider-agnostic targets), `docs/ci.md` (70 lines, design doc), `.github/workflows/ci.yml` (37 lines, GitHub Actions with Python 3.10/3.11 matrix).
- [x] **LICENSE** — MIT license file created, referenced from `package.xml:12` and `README.md:104`.
- [x] **`docs/refactor.md`** — Architectural review with 4-phase remediation strategy and §5 code review notes (`docs/refactor.md:70-103`).
- [x] **Documentation accuracy** — Fixed Python version badge (3.8+ → 3.10+), venv path typo (`bin/bin` → `bin`), `CONTRIBUTING.md` link, false CI claim, placeholder changelog date, missing `py.typed` in architecture.md tree, toolchain docs in `AGENTS.md`.
- [x] **Mypy stub issue** — `types-Markdown` installed in venv; `markdown` added to `pyproject.toml:47` mypy overrides.
- [x] **Source formatting** — All Python files formatted via `ruff format`.
