from __future__ import annotations

import markdown
from PySide6 import QtCore, QtWidgets


class ACPChatView(QtWidgets.QWidget):
    """The chat interface widget with history and input."""

    send_message: QtCore.SignalInstance = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAccessibleName("ACP Chat View")

        self.layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        self.history: QtWidgets.QTextBrowser = QtWidgets.QTextBrowser()
        self.history.setOpenExternalLinks(True)
        self.history.setReadOnly(True)
        self.history.setAccessibleName("Chat History")
        self.history.setHtml("<i>Welcome to the ACP Client. Connect to an agent to start.</i>")
        self.layout.addWidget(self.history)

        self.input_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        self.input_field: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText("Type your message to the agent...")
        self.input_field.setAccessibleName("Message Input")
        self.input_field.returnPressed.connect(self._on_send)

        self.send_button: QtWidgets.QPushButton = QtWidgets.QPushButton("Send")
        self.send_button.setAccessibleName("Send Message")
        self.send_button.clicked.connect(self._on_send)

        self.input_layout.addWidget(self.input_field)
        self.input_layout.addWidget(self.send_button)
        self.layout.addLayout(self.input_layout)

        self.loading_label: QtWidgets.QLabel = QtWidgets.QLabel("")
        self.loading_label.setStyleSheet("color: #1a73e8; font-style: italic; padding: 2px;")
        self.loading_label.setAccessibleName("Agent Status")
        self.layout.addWidget(self.loading_label)

    def _on_send(self) -> None:
        """Emit the current input text as a message and clear the input field."""
        text: str = self.input_field.text().strip()
        if text:
            self.append_message("User", text)
            self.input_field.clear()
            self.send_message.emit(text)

    @QtCore.Slot()
    @QtCore.Slot(str, str)
    def append_message(self, sender: str, text: str = "") -> None:
        """Append a message to the chat history.

        Args:
            sender: The display name of the message sender.
            text: The message content (Markdown supported).
        """
        if not text:
            return
        html: str = self._format_message(sender, text)
        self.history.append(html)

    def _format_message(self, sender: str, text: str) -> str:
        """Convert raw text/markdown to HTML for display in QTextBrowser."""
        color: str = "#2a7ae2" if sender == "User" else "#555555"
        md_html: str = markdown.markdown(text, extensions=["fenced_code", "tables"])
        return f'<div><b style="color: {color};">{sender}:</b> {md_html}</div><br>'

    @QtCore.Slot()
    def set_processing(self) -> None:
        """Disable input controls while the agent is processing."""
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.loading_label.setText("Agent is thinking...")

    @QtCore.Slot()
    def set_ready(self) -> None:
        """Re-enable input controls once processing finishes."""
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
        self.loading_label.setText("")

    @QtCore.Slot()
    def clear_history(self) -> None:
        """Clear the chat history display."""
        self.history.clear()
        self.history.setHtml("<i>Chat history cleared. Connect to an agent to start.</i>")

    @QtCore.Slot()
    def export_history(self) -> None:
        """Export chat history to a file (Markdown, HTML, or plain text)."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Chat History",
            "",
            "Markdown (*.md);;HTML (*.html);;Text (*.txt)",
        )
        if not path:
            return
        content: str = self.history.toPlainText() if path.endswith(".txt") else self.history.toHtml()
        with open(path, "w") as f:
            f.write(content)
