# Copyright (C) 2026 FreeCAD ACP Client Contributors
# SPDX-License-Identifier: LGPL-3.0-or-later

from __future__ import annotations

from typing import Any

import FreeCADGui
from PySide6 import QtCore, QtGui, QtWidgets

from freecad.acpclient.core.controller import ACPController
from freecad.acpclient.ui.chat_view import ACPChatView

_DOCK_WIDGET: ACPDockWidget | None = None


class ACPDockWidget(QtWidgets.QDockWidget):
    """The dockable window hosting the ACP chat interface."""

    def __init__(self) -> None:
        super().__init__("ACP Agent Chat")
        self.setObjectName("ACPAgentChatDock")
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setAccessibleName("ACP Agent Chat Dock")

        palette = QtWidgets.QApplication.instance().palette()
        dim_text = palette.color(QtGui.QPalette.PlaceholderText).name()
        mid_color = palette.color(QtGui.QPalette.Mid).name()
        self._border_color = mid_color if mid_color else "#ccc"
        self._dim_text_color = dim_text if dim_text else "#999"

        self.main_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        self.layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.main_widget)

        self.status_label: QtWidgets.QLabel = QtWidgets.QLabel("Disconnected")
        self._apply_status_style("Disconnected", self._dim_text_color)
        self.status_label.setAccessibleName("Connection Status")
        self.layout.addWidget(self.status_label)

        self.chat_view: ACPChatView = ACPChatView()
        self.layout.addWidget(self.chat_view)

        self.controller: ACPController = ACPController(self.chat_view, parent=self)
        self.controller.status_changed.connect(self._update_status)
        self.controller.start()

        self.setWidget(self.main_widget)

    def _apply_status_style(self, status: str, color: str) -> None:
        """Apply the status label style with the current border color."""
        self.status_label.setText(status)
        style = f"color: {color}; font-weight: bold; padding: 4px; border-bottom: 1px solid {self._border_color};"
        self.status_label.setStyleSheet(style)

    @QtCore.Slot(str, str)
    def _update_status(self, status: str, color: str) -> None:
        """Update the connection status label text and color."""
        self._apply_status_style(status, color)

    def changeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        """Reapply theme-derived colors when the palette changes."""
        if event.type() == QtCore.QEvent.PaletteChange:
            palette = QtWidgets.QApplication.instance().palette()
            dim_text = palette.color(QtGui.QPalette.PlaceholderText).name()
            mid_color = palette.color(QtGui.QPalette.Mid).name()
            self._border_color = mid_color if mid_color else "#ccc"
            self._dim_text_color = dim_text if dim_text else "#999"
        super().changeEvent(event)

    def closeEvent(self, event: Any) -> None:
        """Stop the controller when the dock widget is closed."""
        self.controller.stop()
        super().closeEvent(event)


def get_dock() -> ACPDockWidget:
    """Return the singleton instance of the dock widget, creating it if necessary."""
    global _DOCK_WIDGET
    mw = FreeCADGui.getMainWindow()

    if _DOCK_WIDGET is None:
        _DOCK_WIDGET = ACPDockWidget()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, _DOCK_WIDGET)

    return _DOCK_WIDGET


def toggle_dock() -> None:
    """Toggle the visibility of the ACP dock widget."""
    dock: ACPDockWidget = get_dock()
    if dock.isVisible():
        dock.hide()
    else:
        dock.show()
        dock.raise_()
