from __future__ import annotations

import markdown
from PySide6 import QtCore, QtGui, QtWidgets


def _palette_colors():
    """Derive a consistent palette of semantic colors from the active style.

    Returns:
        Dict with keys: accent, user_bubble, agent_bubble, dim_text.
    """
    palette = QtWidgets.QApplication.instance().palette()
    accent = palette.color(QtGui.QPalette.Highlight)
    text = palette.color(QtGui.QPalette.WindowText)
    dim = palette.color(QtGui.QPalette.PlaceholderText)
    bg = palette.color(QtGui.QPalette.Window)

    # Choose contrast colors: accent for user, subdued for agent
    user_color = accent.name() if accent.isValid() else "#2a7ae2"

    # Agent bubble — use text color but dimmed
    agent_color = _lerp_hex(text.name(), bg.name(), 0.6) if text.isValid() else "#555555"

    # Dim text for status labels
    dim_color = dim.name() if dim.isValid() and dim.name() != bg.name() else _lerp_hex(text.name(), bg.name(), 0.5)

    return {
        "accent": user_color,
        "user_bubble": user_color,
        "agent_bubble": agent_color,
        "dim_text": dim_color,
    }


def _lerp_hex(hex_a: str, hex_b: str, t: float) -> str:
    """Linearly interpolate between two hex RGB colors."""
    try:
        a = int(hex_a.lstrip("#"), 16)
        b = int(hex_b.lstrip("#"), 16)
        r_a, g_a, b_a = (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF
        r_b, g_b, b_b = (b >> 16) & 0xFF, (b >> 8) & 0xFF, b & 0xFF
        r = int(r_a + (r_b - r_a) * t)
        g = int(g_a + (g_b - g_a) * t)
        _b = int(b_a + (b_b - b_a) * t)
        return f"#{r:02x}{g:02x}{_b:02x}"
    except (ValueError, IndexError):
        return hex_a


class ACPChatView(QtWidgets.QWidget):
    """The chat interface widget with history and input."""

    send_message: QtCore.SignalInstance = QtCore.Signal(str)
    cancel_requested: QtCore.SignalInstance = QtCore.Signal()

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

        self.stop_button: QtWidgets.QPushButton = QtWidgets.QPushButton("Stop")
        self.stop_button.setAccessibleName("Stop Agent")
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self.cancel_requested.emit)

        self.input_layout.addWidget(self.input_field)
        self.input_layout.addWidget(self.send_button)
        self.input_layout.addWidget(self.stop_button)
        self.layout.addLayout(self.input_layout)

        self.loading_label: QtWidgets.QLabel = QtWidgets.QLabel("")
        self.loading_label.setAccessibleName("Agent Status")
        self.layout.addWidget(self.loading_label)

        self._streaming: bool = False
        self._streaming_text: str = ""

        self._apply_theme()

    def _apply_theme(self) -> None:
        """Reapply styles derived from the current palette."""
        colors = _palette_colors()
        self._user_color = colors["user_bubble"]
        self._agent_color = colors["agent_bubble"]
        self.loading_label.setStyleSheet(
            f"color: {colors['accent']}; font-style: italic; padding: 2px;"
        )

    def changeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        """Reapply theme-derived colors when the palette changes."""
        if event.type() == QtCore.QEvent.PaletteChange:
            self._apply_theme()
        super().changeEvent(event)

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

        For agent messages, the first chunk appends a new message block
        and subsequent chunks mutate that block in-place (streaming).

        Args:
            sender: The display name of the message sender.
            text: The message content (Markdown supported).
        """
        if not text:
            return
        if sender == "Agent" and self._streaming:
            self._streaming_text += text
            html: str = self._format_message("Agent", self._streaming_text)
            self._replace_last_block(html)
        else:
            block_html: str = self._format_message(sender, text)
            self.history.append(block_html)
            if sender == "Agent":
                self._streaming_text = text
                self._streaming = True

    def _replace_last_block(self, html: str) -> None:
        """Replace the content of the last text block in the document with *html*."""
        cursor: QtGui.QTextCursor = self.history.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock, QtGui.QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(html)
        # Auto-scroll to the bottom so streaming content stays visible
        scrollbar: QtWidgets.QScrollBar | None = self.history.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def _format_message(self, sender: str, text: str) -> str:
        """Convert raw text/markdown to HTML for display in QTextBrowser."""
        color: str = self._user_color if sender == "User" else self._agent_color
        md_html: str = markdown.markdown(text, extensions=["fenced_code", "tables"])
        return f'<div><b style="color: {color};">{sender}:</b> {md_html}</div><br>'

    @QtCore.Slot()
    def set_processing(self) -> None:
        """Disable send controls and show stop button while the agent is processing."""
        self.input_field.setEnabled(False)
        self.send_button.setVisible(False)
        self.stop_button.setVisible(True)
        self.loading_label.setText("Agent is thinking...")

    @QtCore.Slot()
    def set_ready(self) -> None:
        """Re-enable send controls and hide stop button once processing finishes."""
        self._streaming = False
        self.input_field.setEnabled(True)
        self.send_button.setVisible(True)
        self.stop_button.setVisible(False)
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
        content: str = self.history.toHtml() if path.endswith(".html") else self.history.toPlainText()
        with open(path, "w") as f:
            f.write(content)
