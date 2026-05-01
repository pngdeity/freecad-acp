import contextlib
import io
import json
import traceback

import FreeCAD
import FreeCADGui


def read_document_state():
    """
    Returns a dictionary representing the current document state.
    Executes on the main thread.
    """
    try:
        doc = FreeCAD.ActiveDocument
        if not doc:
            return {"error": "No active document"}

        sel = FreeCADGui.Selection.getSelection()
        sel_names = [obj.Name for obj in sel]

        state = {
            "name": doc.Name,
            "label": doc.Label,
            "objects": []
        }

        for obj in doc.Objects:
            obj_data = {
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "selected": obj.Name in sel_names
            }

            if hasattr(obj, "Visibility"):
                obj_data["visibility"] = obj.Visibility

            if hasattr(obj, "Placement") and obj.Placement:
                pl = obj.Placement
                obj_data["placement"] = {
                    "base": {"x": pl.Base.x, "y": pl.Base.y, "z": pl.Base.z},
                    "rotation": {
                        "angle": pl.Rotation.Angle,
                        "axis": {
                            "x": pl.Rotation.Axis.x,
                            "y": pl.Rotation.Axis.y,
                            "z": pl.Rotation.Axis.z,
                        },
                    },
                }

            props = {}
            if hasattr(obj, "PropertiesList"):
                for prop_name in obj.PropertiesList:
                    if prop_name in ["Length", "Width", "Height", "Radius", "Angle"]:
                        props[prop_name] = getattr(obj, prop_name)
            if props:
                obj_data["parameters"] = props

            state["objects"].append(obj_data)

        return state
    except Exception as e:
        return {"error": str(e)}

def execute_python_script_sync(script):
    """
    Executes a Python script in the FreeCAD context synchronously and captures output.
    Must be called from the main thread.
    """
    capture_stdout = io.StringIO()
    capture_stderr = io.StringIO()

    try:
        env = {"FreeCAD": FreeCAD, "FreeCADGui": FreeCADGui, "App": FreeCAD, "Gui": FreeCADGui}
        with contextlib.redirect_stdout(capture_stdout), contextlib.redirect_stderr(capture_stderr):
            exec(script, env)
        output = capture_stdout.getvalue()
        if not output.strip():
            output = "Success"
    except Exception:
        output = capture_stdout.getvalue() + "\n" + capture_stderr.getvalue() + "\n" + traceback.format_exc()

    return output

# Registry of tools that can be exposed to the ACP agent
TOOLS_REGISTRY = {
    "read_document_state": {
        "description": (
            "Get information about the current FreeCAD document, its objects, "
            "their placement, and what the user has selected."
        ),
    },
    "execute_python_script": {
        "description": (
            "Execute a Python script to modify the FreeCAD design or document. "
            "The App, Gui, FreeCAD, and FreeCADGui modules are already imported. "
            "Create objects using App.ActiveDocument.addObject(). "
            "Make sure to call App.ActiveDocument.recompute() at the end."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "The Python code to execute."}
            },
            "required": ["script"]
        }
    }
}

def get_tools_schema_markdown():
    """Returns the tools registry as a Markdown string to inject into the agent context."""
    md = "## Available FreeCAD Tools\\n\\n"
    for name, tool in TOOLS_REGISTRY.items():
        md += f"### {name}\\n"
        md += f"- **Description**: {tool['description']}\\n"
        if "parameters" in tool:
            md += f"- **Parameters**: {json.dumps(tool['parameters'])}\\n"
    return md
