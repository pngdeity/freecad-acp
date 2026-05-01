"""Test fixtures for FreeCAD ACP Client tests.

Provides mock objects for FreeCAD modules that accept dependency injection.
"""

import sys
from unittest.mock import MagicMock


class _MockSignal:
    """Mock Qt Signal usable as a class attribute descriptor."""

    def __init__(self, *types):
        self._types = types

    def __get__(self, instance, owner):
        if instance is None:
            return self
        attr = "_sig_" + str(id(self))
        if not hasattr(instance, attr):
            setattr(instance, attr, MagicMock())
        return getattr(instance, attr)

    def emit(self, *args, **kwargs):
        pass

    def connect(self, slot):
        pass


class _MockQObject:
    """Mock QObject base class that accepts arbitrary init args."""

    def __init__(self, parent=None, **kwargs):
        pass


class _MockQThread(_MockQObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loop = MagicMock()
        self._stop_event = MagicMock()
        self.pending_requests = {}

    def start(self):
        pass

    def wait(self):
        pass

    def stop(self):
        pass


# --- PySide6 mocks (needed for UI/controller modules) ---
_QtCore = MagicMock()
_QtCore.Signal = _MockSignal
_QtCore.Slot = lambda *args, **kwargs: lambda f: f
_QtCore.QObject = _MockQObject
_QtCore.QThread = _MockQThread


class _Qt:
    LeftDockWidgetArea = 1
    RightDockWidgetArea = 2


_QtCore.Qt = _Qt

_QtWidgets = MagicMock()
_QtWidgets.QDockWidget = type("QDockWidget", (_MockQObject,), {})
_QtWidgets.QWidget = type("QWidget", (_MockQObject,), {})
_QtWidgets.QVBoxLayout = type("QVBoxLayout", (), {})
_QtWidgets.QHBoxLayout = type("QHBoxLayout", (), {})
_QtWidgets.QLabel = type("QLabel", (_MockQObject,), {})
_QtWidgets.QLineEdit = type("QLineEdit", (_MockQObject,), {})
_QtWidgets.QPushButton = type("QPushButton", (_MockQObject,), {})
_QtWidgets.QTextBrowser = type("QTextBrowser", (_MockQObject,), {})
_QtWidgets.QMessageBox = MagicMock()
_QtWidgets.QInputDialog = MagicMock()
_QtWidgets.QFileDialog = MagicMock()

sys.modules["PySide6"] = MagicMock()
sys.modules["PySide6.QtCore"] = _QtCore
sys.modules["PySide6.QtWidgets"] = _QtWidgets

# --- ACP SDK mock ---
_acp = MagicMock()
_acp.PROTOCOL_VERSION = 1
_acp.spawn_agent_process = MagicMock()
_acp.text_block = MagicMock(return_value={"type": "text", "text": ""})
_acp.RequestError = type(
    "RequestError",
    (Exception,),
    {
        "invalid_params": classmethod(lambda cls, msg: Exception(msg)),
        "method_not_found": classmethod(lambda cls, msg: Exception(msg)),
    },
)
_acp.interfaces = MagicMock()
_acp.interfaces.Client = type("Client", (), {})
_acp.schema = MagicMock()
_acp.schema.AgentMessageChunk = MagicMock
_acp.schema.TextContentBlock = MagicMock
_acp.schema.AllowedOutcome = MagicMock
_acp.schema.DeniedOutcome = MagicMock
_acp.schema.ClientCapabilities = MagicMock
_acp.schema.FileSystemCapabilities = MagicMock
_acp.schema.ReadTextFileResponse = MagicMock
_acp.schema.RequestPermissionResponse = MagicMock

sys.modules["acp"] = _acp
sys.modules["acp.interfaces"] = _acp.interfaces
sys.modules["acp.schema"] = _acp.schema

sys.modules["qasync"] = MagicMock()

# --- FreeCAD module stubs (only needed for module-level imports in tools.py, not used by tests) ---
sys.modules["FreeCAD"] = MagicMock()
sys.modules["FreeCADGui"] = MagicMock()
sys.modules["Part"] = MagicMock()
sys.modules["Mesh"] = MagicMock()
