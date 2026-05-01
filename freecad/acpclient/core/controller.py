import json

from PySide6 import QtCore, QtWidgets

from freecad.acpclient.core import tools
from freecad.acpclient.core.client import ACPClientThread


class ACPController(QtCore.QObject):
    """Main controller managing the UI and the background thread.

    Resides on the main thread.
    """

    def __init__(self, chat_view, parent=None):
        super().__init__(parent)
        self.chat_view = chat_view

        self.client_thread = ACPClientThread()
        self.client_thread.message_received.connect(self.chat_view.append_message)
        self.client_thread.error_occurred.connect(
            lambda msg: self.chat_view.append_message("System", f"Error: {msg}")
        )
        self.client_thread.connected.connect(
            lambda: self.chat_view.append_message("System", "Connected to Agent.")
        )
        self.client_thread.disconnected.connect(
            lambda: self.chat_view.append_message("System", "Disconnected from Agent.")
        )

        self.client_thread.request_execute_script.connect(self.handle_execute_script)
        self.client_thread.request_read_document.connect(self.handle_read_document)
        self.client_thread.request_permission_signal.connect(self.handle_permission)
        self.client_thread.request_run_tool.connect(self.handle_run_tool)

        self.chat_view.send_message.connect(self.handle_send_message)
        self._is_first_prompt = True

    def start(self):
        self.client_thread.start()

    def stop(self):
        self.client_thread.disconnect_from_agent()
        self.client_thread.stop()

    def connect_to_agent(self, command_path):
        self._is_first_prompt = True
        self.client_thread.connect_to_agent(command_path)

    def disconnect_from_agent(self):
        self.client_thread.disconnect_from_agent()

    @QtCore.Slot(str)
    def handle_send_message(self, text):
        if self._is_first_prompt:
            system_instruction = (
                "You are an ACP agent connected to FreeCAD. "
                "You can modify the CAD environment using ext_methods.\n"
            )
            system_instruction += tools.get_tools_schema_markdown()
            formatted_text = system_instruction + "\n\nUser Request: " + text
            self._is_first_prompt = False
        else:
            formatted_text = text

        self.client_thread.send_prompt(formatted_text)

    @QtCore.Slot(str, str)
    def handle_execute_script(self, req_id, script):
        result = tools.execute_python_script_sync(script)
        self.client_thread.resolve_execute_script(req_id, result)

    @QtCore.Slot(str)
    def handle_read_document(self, req_id):
        result = tools.read_document_state()
        self.client_thread.resolve_read_document(req_id, result)

    @QtCore.Slot(str, str, str)
    def handle_run_tool(self, req_id, method, params_json):
        params = json.loads(params_json)
        result = tools.run_tool(method, params)
        self.client_thread.resolve_run_tool(req_id, json.dumps(result))

    @QtCore.Slot(str, str, str)
    def handle_permission(self, req_id, title, description):
        msg = QtWidgets.QMessageBox(self.chat_view)
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle(title)
        msg.setText("The agent is requesting permission to execute an action:")
        msg.setDetailedText(description)
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.No)
        res = msg.exec()
        allowed = res == QtWidgets.QMessageBox.Yes
        self.client_thread.resolve_permission(req_id, allowed)
