# FreeCAD ACP Client Workbench

This workbench enables FreeCAD to act as an **Agentic Control Protocol (ACP)** Client. 
It allows FreeCAD users to interact with AI-powered agents (like Gemini CLI, Claude, or custom local agents) to assist with CAD design, document analysis, and automation.

## Features
- **Native Chat Sidebar:** Interact with agents directly within FreeCAD.
- **Local Agent Support:** Connect to agents running as local subprocesses via `stdio`.
- **FreeCAD Capabilities:** Agents can query the document state and execute Python scripts to modify the design.

## Installation
1. Copy the `src/freecad/acpclient` directory (or the whole `FreeCAD_ACP` folder) to your FreeCAD `Mod` directory.
   - Linux: `~/.local/share/FreeCAD/Mod/`
   - Windows: `%APPDATA%\FreeCAD\Mod\`
   - macOS: `~/Library/Application Support/FreeCAD/Mod/`
2. Install dependencies:
   ```bash
   pip install acp-sdk PySide6
   ```

## Usage
1. Open FreeCAD and switch to the **ACP Client** workbench.
2. Click the **Connect to Agent** button.
3. (Optional) Provide the command to spawn your local agent (e.g., `gemini --experimental-acp`).
4. Start chatting! Try asking the agent to "Create a 100mm cube" or "List all objects in the document".

## Architecture
- **UI:** Built with PySide6 using a `QDockWidget` and `QTextBrowser`.
- **Protocol:** Uses the official [Agent Client Protocol Python SDK](https://github.com/agentclientprotocol/python-sdk).
- **Threading:** Runs the `asyncio` protocol loop in a background `QThread` to ensure the FreeCAD GUI remains responsive.
