# Architecture

## Component Structure

```
freecad/acpclient/
├── __init__.py
├── py.typed
├── init_gui.py          # Workbench registration (FreeCADGui.addWorkbench)
├── commands.py          # Menu/toolbar command classes (Connect, Disconnect, ToggleUI)
├── core/
│   ├── __init__.py
│   ├── tools.py         # FreeCAD tool functions + dispatch map
│   ├── client.py        # ACPClientThread (QThread + asyncio) + FreeCADACPClient (ACP Client impl)
│   └── controller.py    # ACPController: main-thread coordinator between UI and background thread
└── ui/
    ├── __init__.py
    ├── chat_view.py     # ACPChatView widget (text browser + input + send)
    └── dock_widget.py   # ACPDockWidget (QDockWidget singleton)
```

- **init_gui.py** — Registers `ACPClientWorkbench` via `FreeCADGui.addWorkbench()`. Sets up the toolbar and menu items referencing `ACP_Connect`, `ACP_Disconnect`, `ACP_ToggleUI` commands.
- **commands.py** — Defines `ConnectCommand`, `DisconnectCommand`, `ToggleUICommand` (FreeCAD command pattern). Registers them with `FreeCADGui.addCommand()`. These orchestrate showing the dock and invoking controller methods.
- **ui/chat_view.py** — `ACPChatView(QWidget)` renders the message history in a `QTextBrowser` with Markdown, provides a `QLineEdit` input, and a Send button. Emits `send_message(text)`.
- **ui/dock_widget.py** — `ACPDockWidget(QDockWidget)` singleton that hosts the chat view and a status label. Creates the `ACPController` and connects its `status_changed` signal to update the label.
- **core/controller.py** — `ACPController(QObject)` lives on the main thread. Connects `ACPChatView.send_message` → `handle_send_message()`, and `ACPClientThread` signals (from background thread) → `handle_execute_script`, `handle_read_document`, etc. Injects system prompt + tool schema on first prompt.
- **core/client.py** — `ACPClientThread(QThread)` runs an asyncio event loop on a background thread. `FreeCADACPClient` implements the ACP `Client` interface: handles `session_update` (agent responses), `ext_method` (tool dispatch), and `request_permission` (user confirmation dialogs via signals dispatched to main thread).
- **core/tools.py** — Stateless functions that call FreeCAD API: `read_document_state`, `execute_python_script_sync`, `create_primitive`, `delete_object`, `get_selection`, `export_file`. Contains `TOOL_DISPATCH` mapping and `TOOLS_REGISTRY` for schema injection.

## Data Flow

```
User (FreeCAD GUI)
  │
  ├── types message in ACPChatView input
  │   └── chat_view.send_message signal → ACPController.handle_send_message(text)
  │
  ├── ACPController formats prompt (system instruction + tool schema on first message)
  │   └── calls client_thread.send_prompt(formatted_text)
  │
  ├── ACPClientThread (background QThread)
  │   └── asyncio loop: conn.prompt(session_id, [text_block(text)])
  │       │
  │       ├── Agent responds with text chunks
  │       │   └── FreeCADACPClient.session_update()
  │       │       └── thread_bridge.message_received.emit("Agent", text)
  │       │           └── chat_view.append_message("Agent", text)
  │       │
  │       ├── Agent calls ext_method (e.g. "create_primitive")
  │       │   └── FreeCADACPClient.ext_method()
  │       │       └── thread_bridge.request_run_tool.emit(req_id, method, params_json)
  │       │           └── ACPController.handle_run_tool() → tools.run_tool()
  │       │           └── client_thread.resolve_run_tool(req_id, result_json)
  │       │
  │       └── Agent requests permission
  │           └── FreeCADACPClient.request_permission()
  │               └── thread_bridge.request_permission_signal.emit()
  │                   └── ACPController.handle_permission() → QMessageBox
  │                   └── client_thread.resolve_permission(req_id, allowed)
  │
  └── Processing finished
      └── ACPClientThread.processing_finished.emit()
          └── chat_view.set_ready()
```

## Threading Model

- **Main thread**: Qt GUI, ACPController, ACPChatView, ACPDockWidget. All FreeCAD API calls (`tools.py` functions) must run here.
- **Background thread**: ACPClientThread runs an `asyncio.new_event_loop()` via `QThread.run()`. The asyncio event loop handles all ACP SDK I/O (connect, prompt, session updates).
- **Main ↔ Background bridge**: Uses UUID-keyed `asyncio.Future` objects and Qt signals:
  1. Background thread creates a `Future` and emits a Qt signal with a `req_id`.
  2. Main thread slot receives the signal, executes the work (FreeCAD API call), and calls a `resolve_*` slot on the client thread.
  3. `resolve_*` uses `loop.call_soon_threadsafe(fut.set_result, result)` to resolve the Future on the background loop.

## Tool Dispatch Mechanism

`core/tools.py` provides two layers:

1. **`TOOL_DISPATCH`**: A `dict[str, Callable]` mapping method names (e.g. `"create_primitive"`) to handler functions. `run_tool(method, params)` looks up the handler and calls `func(**params)`.

2. **`TOOLS_REGISTRY`**: A `dict[str, dict]` with descriptions and parameter schemas for each tool (plus `execute_python_script` which is handled via `ext_method` rather than `TOOL_DISPATCH`). `get_tools_schema_markdown()` serializes this into a Markdown string that is injected into the system instruction on first prompt.

The agent sees these tools via the system instruction and calls them through ACP extension methods (`ext_method`). `FreeCADACPClient.ext_method()` routes `read_document_state` and `execute_python_script` as special cases (for permission checks), and delegates all other tools to `request_run_tool` → `ACPController.handle_run_tool()` → `tools.run_tool()`.
