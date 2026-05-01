# Copyright (C) 2026 FreeCAD ACP Client Contributors
# SPDX-License-Identifier: LGPL-3.0-or-later

from __future__ import annotations

import json
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from freecad.acpclient.core import tools
from freecad.acpclient.core.client import ACPClientThread
from freecad.acpclient.ui.chat_view import ACPChatView


class ACPController(QtCore.QObject):
    """Main controller managing the UI and the background thread.

    Resides on the main thread.
    """

    status_changed: QtCore.SignalInstance = QtCore.Signal(str, str)

    # Semantic status colors that remain legible in both light and dark themes.
    _COLOR_PROCESSING: str = "#1a73e8"
    _COLOR_CONNECTED: str = "#34a853"
    _COLOR_ERROR: str = "#ea4335"

    @staticmethod
    def _dim_color() -> str:
        """Return a theme-adaptive dim/gray color for the disconnected state."""
        palette = QtWidgets.QApplication.instance().palette()
        dim = palette.color(QtGui.QPalette.PlaceholderText)
        return dim.name() if dim.isValid() and dim.name() else "#999"

    def __init__(self, chat_view: ACPChatView, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.chat_view: ACPChatView = chat_view

        self.client_thread: ACPClientThread = ACPClientThread()
        self.client_thread.message_received.connect(self.chat_view.append_message)
        self.client_thread.error_occurred.connect(self._on_error_occurred)
        self.client_thread.connected.connect(self._on_connected)
        self.client_thread.disconnected.connect(self._on_disconnected)
        self.client_thread.processing_finished.connect(self._on_processing_finished)

        self.client_thread.request_execute_script.connect(self.handle_execute_script)
        self.client_thread.request_read_document.connect(self.handle_read_document)
        self.client_thread.request_permission_signal.connect(self.handle_permission)
        self.client_thread.request_run_tool.connect(self.handle_run_tool)

        self.chat_view.send_message.connect(self.handle_send_message)
        self.chat_view.cancel_requested.connect(self.handle_cancel)
        self._is_first_prompt: bool = True

    def start(self) -> None:
        """Start the background client thread."""
        self.client_thread.start()

    def stop(self) -> None:
        """Disconnect from the agent and stop the background thread."""
        self.client_thread.disconnect_from_agent()
        self.client_thread.stop()

    def connect_to_agent(self, command_path: str) -> None:
        """Connect to an ACP agent using the given command path."""
        self._is_first_prompt = True
        self.client_thread.connect_to_agent(command_path)

    def disconnect_from_agent(self) -> None:
        """Disconnect from the currently connected ACP agent."""
        self.client_thread.disconnect_from_agent()

    @QtCore.Slot(str)
    def handle_send_message(self, text: str) -> None:
        """Handle a message sent from the chat view and forward it to the agent."""
        self.chat_view.set_processing()
        self.status_changed.emit("Agent is processing...", self._COLOR_PROCESSING)

        if self._is_first_prompt:
            system_instruction = (
                "You are an ACP agent connected to FreeCAD. You can modify the CAD environment using ext_methods.\n"
            )
            system_instruction += tools.get_tools_schema_markdown()
            formatted_text = system_instruction + "\n\nUser Request: " + text
            self._is_first_prompt = False
        else:
            formatted_text = text

        self.client_thread.send_prompt(formatted_text)

    @QtCore.Slot()
    def handle_cancel(self) -> None:
        """Cancel the currently processing agent prompt."""
        self.client_thread.cancel_prompt()
        self.chat_view.set_ready()
        self.status_changed.emit("Connected", self._COLOR_CONNECTED)

    def _on_connected(self) -> None:
        """Handle agent connection established."""
        self.chat_view.append_message("System", "Connected to Agent.")
        self.chat_view.set_ready()
        self.status_changed.emit("Connected", self._COLOR_CONNECTED)

    def _on_disconnected(self) -> None:
        """Handle agent disconnection."""
        self.chat_view.append_message("System", "Disconnected from Agent.")
        self.status_changed.emit("Disconnected", self._dim_color())

    def _on_error_occurred(self, msg: str) -> None:
        """Handle an error from the agent or background thread."""
        self.chat_view.append_message("System", f"Error: {msg}")
        self.chat_view.set_ready()
        self.status_changed.emit("Error", self._COLOR_ERROR)

    def _on_processing_finished(self) -> None:
        """Handle completion of agent processing."""
        self.chat_view.set_ready()
        self.status_changed.emit("Connected", self._COLOR_CONNECTED)

    @QtCore.Slot(str, str)
    def handle_execute_script(self, req_id: str, script: str) -> None:
        """Execute a Python script in the FreeCAD context and resolve the request."""
        result: str = tools.execute_python_script_sync(script)
        self.client_thread.resolve_execute_script(req_id, result)

    @QtCore.Slot(str)
    def handle_read_document(self, req_id: str) -> None:
        """Read the current document state and resolve the request."""
        result: dict[str, Any] = tools.read_document_state()
        self.client_thread.resolve_read_document(req_id, json.dumps(result))

    @QtCore.Slot(str, str, str)
    def handle_run_tool(self, req_id: str, method: str, params_json: str) -> None:
        """Run a named tool with the given JSON-encoded parameters."""
        params: dict[str, Any] = json.loads(params_json)
        result: dict[str, Any] = tools.run_tool(method, params)
        self.client_thread.resolve_run_tool(req_id, json.dumps(result))

    @QtCore.Slot(str, str, str)
    def handle_permission(self, req_id: str, title: str, description: str) -> None:
        """Show a permission dialog and resolve the request with the user's choice."""
        msg: QtWidgets.QMessageBox = QtWidgets.QMessageBox(self.chat_view)
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle(title)
        msg.setText("The agent is requesting permission to execute an action:")
        msg.setDetailedText(description)
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.No)
        res: int = msg.exec()
        allowed: bool = res == QtWidgets.QMessageBox.Yes
        self.client_thread.resolve_permission(req_id, allowed)
