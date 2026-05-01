import FreeCADGui
from PySide6 import QtCore, QtWidgets

from freecad.acpclient.core.controller import ACPController
from freecad.acpclient.ui.chat_view import ACPChatView

_DOCK_WIDGET = None

class ACPDockWidget(QtWidgets.QDockWidget):
    """The dockable window hosting the ACP chat interface."""

    def __init__(self):
        super().__init__("ACP Agent Chat")
        self.setObjectName("ACPAgentChatDock")
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        # Main layout widget
        self.main_widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Chat View
        self.chat_view = ACPChatView()
        self.layout.addWidget(self.chat_view)

        # Controller
        self.controller = ACPController(self.chat_view, parent=self)
        self.controller.start()

        self.setWidget(self.main_widget)

    def closeEvent(self, event):
        self.controller.stop()
        super().closeEvent(event)

def get_dock():
    """Returns the singleton instance of the dock widget, creating it if necessary."""
    global _DOCK_WIDGET
    mw = FreeCADGui.getMainWindow()

    if _DOCK_WIDGET is None:
        _DOCK_WIDGET = ACPDockWidget()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, _DOCK_WIDGET)

    return _DOCK_WIDGET

def toggle_dock():
    """Toggles the visibility of the ACP dock widget."""
    dock = get_dock()
    if dock.isVisible():
        dock.hide()
    else:
        dock.show()
        dock.raise_()
