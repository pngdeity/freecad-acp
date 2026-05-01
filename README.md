# FreeCAD ACP Client

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FreeCAD](https://img.shields.io/badge/FreeCAD-0.21+-brightgreen.svg)](https://www.freecad.org)

<p align="center">
  <img src="Resources/Icons/ACPClient.svg" width="128" height="128" alt="ACP Client Logo">
</p>

## Overview

The **FreeCAD ACP Client** is a specialized workbench that implements the **Agentic Control Protocol (ACP)**, bringing the power of autonomous AI agents directly into the FreeCAD environment. It allows users to collaborate with AI agents to automate CAD workflows, analyze document structures, and generate complex geometries through natural language.

Unlike simple "chat-to-script" plugins, this client provides a robust, multi-threaded bridge that allows agents to "see" the current document state and "act" on it using a set of verified CAD tools.

## Key Features

- **Integrated Chat Interface**: A modern, Markdown-supported chat view docked within the FreeCAD UI.
- **Asynchronous Execution**: All network I/O and agent processing happen on a background thread, keeping the FreeCAD GUI responsive.
- **Agentic Toolset**: Agents have access to specialized tools including:
  - **Document Inspection**: Reading objects, properties, and tree structures.
  - **Geometry Creation**: Creating primitives (cubes, cylinders, spheres).
  - **Python Automation**: Executing safe, synchronized Python scripts within the FreeCAD context.
  - **Object Manipulation**: Deleting, selecting, and exporting objects.
- **Permission System**: Explicit user confirmation for sensitive actions requested by the agent.

## Installation

### Via Addon Manager (Recommended)
1. Open FreeCAD and go to **Tools -> Addon Manager**.
2. Search for "ACP Client".
3. Click **Install**.
4. Restart FreeCAD.

### Manual Installation
1. Clone this repository into your FreeCAD user directory:
   ```bash
   cd ~/.local/share/FreeCAD/Mod  # Linux
   # OR %APPDATA%\FreeCAD\Mod     # Windows
   git clone https://github.com/pngdeity/freecad-acp.git acp_client
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Restart FreeCAD.

## Getting Started

1. Switch to the **ACP Client** workbench in the FreeCAD workbench selector.
2. Click the **Connect** icon in the toolbar.
3. Enter the endpoint of your ACP-compatible agent.
4. Start interacting! Try prompts like:
   - *"What objects are currently in my document?"*
   - *"Create a 10mm cube at the origin."*
   - *"Write a script to create a pattern of 5 cylinders."*

## Development

### Environment Setup
We recommend using a virtual environment for development:
```bash
python -m venv .venv
source .venv/bin/bin/activate  # Linux
pip install -r requirements.txt -r dev-requirements.txt
```

### Code Quality
We use `ruff` for linting and formatting, and `mypy` for type checking.
```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy freecad/
```

### Running Tests
The project uses `pytest` for unit and integration testing.
```bash
pytest tests/ -v
```

## Architecture

The project follows a decoupled architecture:
- **`core/client.py`**: Manages the `asyncio` loop and ACP SDK connection on a background `QThread`.
- **`core/controller.py`**: Coordinates between the UI and the background thread.
- **`core/tools.py`**: Implements the actual FreeCAD API interactions.
- **`ui/`**: Contains the Qt-based user interface components.

For more details, see [docs/architecture.md](docs/architecture.md).

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/contributing.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Maintained by the ACP Client Contributors.*
