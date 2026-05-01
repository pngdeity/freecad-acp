from __future__ import annotations

import FreeCAD
import FreeCADGui
from PySide6 import QtWidgets


class ConnectCommand:
    """Command to connect to an ACP agent."""

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": "ACPClient.svg",
            "MenuText": "Connect to Agent",
            "ToolTip": "Open connection to an ACP agent",
        }

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        from freecad.acpclient.ui import dock_widget

        dock = dock_widget.get_dock()
        if not dock.isVisible():
            dock.show()

        mw = FreeCADGui.getMainWindow()
        command_path, ok = QtWidgets.QInputDialog.getText(
            mw,
            "Connect to Agent",
            "Enter agent command (e.g. 'gemini --experimental-acp'):",
            QtWidgets.QLineEdit.Normal,
            "gemini --experimental-acp",
        )

        if ok and command_path:
            FreeCAD.Console.PrintMessage(f"ACP: Connecting via '{command_path}'...\n")
            dock.controller.connect_to_agent(command_path)


class DisconnectCommand:
    """Command to disconnect from the current ACP agent."""

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": "ACPClient.svg",
            "MenuText": "Disconnect from Agent",
            "ToolTip": "Close connection to the current ACP agent",
        }

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        from freecad.acpclient.ui import dock_widget

        dock = dock_widget.get_dock()
        FreeCAD.Console.PrintMessage("ACP: Disconnecting...\n")
        dock.controller.disconnect_from_agent()


class ToggleUICommand:
    """Command to toggle the ACP Chat DockWidget."""

    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": "ACPClient.svg",
            "MenuText": "Toggle Chat UI",
            "ToolTip": "Show or hide the ACP Agent chat interface",
        }

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        FreeCAD.Console.PrintMessage("ACP: Toggle UI activated\n")
        from freecad.acpclient.ui import dock_widget

        dock_widget.toggle_dock()


FreeCADGui.addCommand("ACP_Connect", ConnectCommand())
FreeCADGui.addCommand("ACP_Disconnect", DisconnectCommand())
FreeCADGui.addCommand("ACP_ToggleUI", ToggleUICommand())
