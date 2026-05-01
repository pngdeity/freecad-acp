import markdown
from PySide6 import QtCore, QtWidgets


class ACPChatView(QtWidgets.QWidget):
    """The chat interface widget with history and input."""

    send_message = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        # Chat History
        self.history = QtWidgets.QTextBrowser()
        self.history.setOpenExternalLinks(True)
        self.history.setReadOnly(True)
        # Basic styling for the chat
        self.history.setHtml("<i>Welcome to the ACP Client. Connect to an agent to start.</i>")
        self.layout.addWidget(self.history)

        # Input Area
        self.input_layout = QtWidgets.QHBoxLayout()
        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText("Type your message to the agent...")
        self.input_field.returnPressed.connect(self._on_send)

        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self._on_send)

        self.input_layout.addWidget(self.input_field)
        self.input_layout.addWidget(self.send_button)
        self.layout.addLayout(self.input_layout)

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self.append_message("User", text)
            self.input_field.clear()
            self.send_message.emit(text)

    def append_message(self, sender, text):
        """Appends a message to the chat history."""
        html = self._format_message(sender, text)
        self.history.append(html)

    def _format_message(self, sender, text):
        """Converts raw text/markdown to simple HTML for QTextBrowser."""
        color = "#2a7ae2" if sender == "User" else "#555555"

        # Robust Markdown-to-HTML parsing
        md_html = markdown.markdown(text, extensions=['fenced_code', 'tables'])

        return f'<div><b style="color: {color};">{sender}:</b> {md_html}</div><br>'
