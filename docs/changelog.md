# Changelog

## [1.0.0] — 2025-01-XX

Initial release of the FreeCAD ACP Client Workbench.

### Features

- **Native Chat Sidebar**: A dockable `QDockWidget` with Markdown-rendered message history, text input, and send button.
- **ACP Agent Support**: Connect to ACP-compatible agents via `stdio` subprocess (e.g., Gemini CLI).
- **FreeCAD Tool Dispatch**:
  - `read_document_state` — Query active document object tree, placements, visibility, and selection.
  - `execute_python_script` — Execute arbitrary Python scripts in FreeCAD context with permission confirmation.
  - `create_primitive` — Create Box, Cylinder, Sphere, Cone, Torus shapes programmatically.
  - `delete_object` — Remove objects from the active document.
  - `get_selection` — Retrieve currently selected objects.
  - `export_file` — Export document to STL or STEP format.
- **Permission System**: Agent tool calls requiring user confirmation prompt a `QMessageBox`.
- **Threading**: Background `QThread` with asyncio event loop keeps the FreeCAD GUI responsive during agent communication.
- **Workbench Integration**: Register as a FreeCAD workbench with toolbar and menu commands (Connect, Disconnect, Toggle UI).
