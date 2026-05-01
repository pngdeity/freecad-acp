from __future__ import annotations

import os

import FreeCADGui

_ADDON_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FreeCADGui.addIconPath(os.path.join(_ADDON_ROOT, "Resources", "Icons"))


class ACPClientWorkbench(FreeCADGui.Workbench):
    """The ACP Client Workbench for FreeCAD."""

    Icon: str = os.path.join(_ADDON_ROOT, "Resources", "Icons", "ACPClient.svg")
    MenuText: str = "ACP Client"
    ToolTip: str = "Interact with ACP compatible agents"

    def Initialize(self) -> None:
        """Executed when the workbench is loaded for the first time."""

        self.appendToolbar("ACP Client", ["ACP_Connect", "ACP_Disconnect", "ACP_ToggleUI"])
        self.appendMenu("ACP Client", ["ACP_Connect", "ACP_Disconnect", "ACP_ToggleUI"])

    def Activated(self) -> None:
        """Executed when the workbench is activated (selected from the dropdown)."""
        pass

    def Deactivated(self) -> None:
        """Executed when switching to another workbench."""
        pass

    def GetClassName(self) -> str:
        # This is mandatory for workbenches
        return "Gui::PythonWorkbench"

# Register the workbench
FreeCADGui.addWorkbench(ACPClientWorkbench())
