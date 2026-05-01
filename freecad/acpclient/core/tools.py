from __future__ import annotations

import contextlib
import io
import json
import traceback
from collections.abc import Callable
from typing import Any

import FreeCAD
import FreeCADGui


def read_document_state(
    app: Any = FreeCAD,
    gui: Any = FreeCADGui,
) -> dict[str, Any]:
    """Return a dictionary representing the state of the active FreeCAD document.

    Args:
        app: FreeCAD App module (injectable for testing).
        gui: FreeCAD Gui module (injectable for testing).
    """
    try:
        doc = app.ActiveDocument
        if not doc:
            return {"error": "No active document"}

        sel = gui.Selection.getSelection()
        sel_names = [obj.Name for obj in sel]

        state: dict[str, Any] = {
            "name": doc.Name,
            "label": doc.Label,
            "objects": [],
        }

        for obj in doc.Objects:
            obj_data: dict[str, Any] = {
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "selected": obj.Name in sel_names,
            }

            if hasattr(obj, "Visibility"):
                obj_data["visibility"] = bool(obj.Visibility)

            if hasattr(obj, "Placement") and obj.Placement:
                pl = obj.Placement
                obj_data["placement"] = {
                    "base": {"x": float(pl.Base.x), "y": float(pl.Base.y), "z": float(pl.Base.z)},
                    "rotation": {
                        "angle": float(pl.Rotation.Angle),
                        "axis": {
                            "x": float(pl.Rotation.Axis.x),
                            "y": float(pl.Rotation.Axis.y),
                            "z": float(pl.Rotation.Axis.z),
                        },
                    },
                }

            props: dict[str, Any] = {}
            if hasattr(obj, "PropertiesList"):
                for prop_name in obj.PropertiesList:
                    if prop_name in ("Length", "Width", "Height", "Radius", "Angle"):
                        props[prop_name] = getattr(obj, prop_name)
            if props:
                obj_data["parameters"] = props

            state["objects"].append(obj_data)

        return state
    except Exception as e:
        return {"error": str(e)}


def execute_python_script_sync(
    script: str,
    app: Any = FreeCAD,
    gui: Any = FreeCADGui,
) -> str:
    """Execute a Python script in the FreeCAD context and capture output.

    Must be called from the main thread.

    Args:
        script: Python source code to execute.
        app: FreeCAD App module (injectable for testing).
        gui: FreeCAD Gui module (injectable for testing).
    """
    capture_stdout = io.StringIO()
    capture_stderr = io.StringIO()

    try:
        env: dict[str, Any] = {"FreeCAD": app, "FreeCADGui": gui, "App": app, "Gui": gui}
        with contextlib.redirect_stdout(capture_stdout), contextlib.redirect_stderr(capture_stderr):
            exec(script, env)
        output = capture_stdout.getvalue()
        if not output.strip():
            output = "Success"
    except Exception:
        output = capture_stdout.getvalue() + "\n" + capture_stderr.getvalue() + "\n" + traceback.format_exc()

    return output


def create_primitive(
    obj_type: str,
    params: dict[str, Any],
    app: Any = FreeCAD,
) -> dict[str, Any]:
    """Create a FreeCAD primitive shape in the active document.

    Args:
        obj_type: Primitive type - Box, Cylinder, Sphere, Cone, or Torus.
        params: Shape parameters and optional placement.
        app: FreeCAD App module (injectable for testing).
    """
    doc = app.ActiveDocument
    if not doc:
        return {"error": "No active document"}

    import Part

    doc.openTransaction("ACP: Create Primitive")
    try:
        if obj_type == "Box":
            shape = Part.makeBox(
                params.get("length", 10),
                params.get("width", 10),
                params.get("height", 10),
            )
        elif obj_type == "Cylinder":
            shape = Part.makeCylinder(
                params.get("radius", 5),
                params.get("height", 10),
            )
        elif obj_type == "Sphere":
            shape = Part.makeSphere(params.get("radius", 5))
        elif obj_type == "Cone":
            shape = Part.makeCone(
                params.get("radius1", 5),
                params.get("radius2", 2),
                params.get("height", 10),
            )
        elif obj_type == "Torus":
            shape = Part.makeTorus(
                params.get("radius1", 10),
                params.get("radius2", 2),
            )
        else:
            return {"error": f"Unknown primitive type: {obj_type}"}

        name = params.get("name", obj_type)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape

        if "placement" in params:
            pl = params["placement"]
            pos = app.Vector(
                pl.get("x", 0), pl.get("y", 0), pl.get("z", 0),
            )
            rot = app.Rotation(
                app.Vector(
                    pl.get("ax", 0), pl.get("ay", 0), pl.get("az", 1),
                ),
                pl.get("angle", 0),
            )
            obj.Placement = app.Placement(pos, rot)

        doc.recompute()
        doc.commitTransaction()
        return {"result": f"Created {obj_type} '{name}'. Call recompute if further changes are needed."}
    except Exception as e:
        with contextlib.suppress(Exception):
            doc.abortTransaction()
        return {"error": str(e)}


def delete_object(
    name: str,
    app: Any = FreeCAD,
) -> dict[str, Any]:
    """Remove an object from the active document by name.

    Args:
        name: Name of the object to delete.
        app: FreeCAD App module (injectable for testing).
    """
    doc = app.ActiveDocument
    if not doc:
        return {"error": "No active document"}

    try:
        obj = doc.getObject(name)
        if obj is None:
            return {"error": f"Object '{name}' not found"}
        doc.openTransaction("ACP: Delete Object")
        doc.removeObject(name)
        doc.recompute()
        doc.commitTransaction()
        return {"result": f"Deleted object '{name}'"}
    except Exception as e:
        with contextlib.suppress(Exception):
            doc.abortTransaction()
        return {"error": str(e)}


def get_selection(
    gui: Any = FreeCADGui,
) -> dict[str, Any]:
    """Return information about the currently selected objects.

    Args:
        gui: FreeCAD Gui module (injectable for testing).
    """
    try:
        sel = gui.Selection.getSelection()
        if not sel:
            return {"result": "No objects selected.", "count": 0, "objects": []}

        objects: list[dict[str, Any]] = []
        for obj in sel:
            obj_info: dict[str, Any] = {
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
            }
            if hasattr(obj, "Placement") and obj.Placement:
                pl = obj.Placement
                obj_info["placement"] = {
                    "base": {"x": float(pl.Base.x), "y": float(pl.Base.y), "z": float(pl.Base.z)},
                }
            objects.append(obj_info)

        return {"result": f"{len(objects)} object(s) selected.", "count": len(objects), "objects": objects}
    except Exception as e:
        return {"error": str(e)}


def export_file(
    filepath: str,
    fmt: str = "",
    app: Any = FreeCAD,
) -> dict[str, Any]:
    """Export the active document to a file (STL or STEP format).

    Args:
        filepath: Full path for the output file.
        fmt: Format ('stl' or 'step').
        app: FreeCAD App module (injectable for testing).
    """
    doc = app.ActiveDocument
    if not doc:
        return {"error": "No active document"}

    try:
        import Mesh
        import Part

        if fmt.lower() in ("stl", "stl ascii", ".stl"):
            objs = [obj for obj in doc.Objects if hasattr(obj, "Shape") and obj.Shape]
            if not objs:
                return {"error": "No shape objects to export"}
            Mesh.export(objs, filepath)
        elif fmt.lower() in ("step", "stp", ".step", ".stp"):
            Part.export(list(doc.Objects), filepath)
        else:
            return {"error": f"Unsupported format: {fmt}. Use 'stl' or 'step'."}

        return {"result": f"Exported to {filepath}"}
    except Exception as e:
        return {"error": str(e)}


# --- Tool dispatch map ---

TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "read_document_state": read_document_state,
    "create_primitive": create_primitive,
    "delete_object": delete_object,
    "get_selection": get_selection,
    "export_file": export_file,
}


def run_tool(method: str, params: dict[str, Any], app: Any = None, gui: Any = None) -> dict[str, Any]:
    """Route a tool method name and params to the correct handler.

    Args:
        method: Tool method name.
        params: Parameters dict to pass to the tool function.
        app: Optional FreeCAD App override (for testing).
        gui: Optional FreeCAD Gui override (for testing).

    Returns:
        Result dict from the tool function.
    """
    func = TOOL_DISPATCH.get(method)
    if func is None:
        return {"error": f"Unknown tool: {method}"}

    kwargs: dict[str, Any] = {}
    if app is not None:
        kwargs["app"] = app
    if gui is not None:
        kwargs["gui"] = gui
    return func(**params, **kwargs)


# --- Tool registry for agent context injection ---

TOOLS_REGISTRY: dict[str, dict[str, Any]] = {
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
                "script": {"type": "string", "description": "The Python code to execute."},
            },
            "required": ["script"],
        },
    },
    "create_primitive": {
        "description": (
            "Create a primitive 3D shape in the active document. "
            "Supported types: Box, Cylinder, Sphere, Cone, Torus."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "obj_type": {
                    "type": "string",
                    "description": "Primitive type: Box, Cylinder, Sphere, Cone, or Torus.",
                },
                "params": {
                    "type": "object",
                    "description": (
                        "Shape parameters. Box: length, width, height. "
                        "Cylinder: radius, height. Sphere: radius. "
                        "Cone: radius1, radius2, height. Torus: radius1, radius2. "
                        "All also accept 'name' and 'placement'."
                    ),
                },
            },
            "required": ["obj_type", "params"],
        },
    },
    "delete_object": {
        "description": "Remove an object from the active document by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the object to delete."},
            },
            "required": ["name"],
        },
    },
    "get_selection": {
        "description": "Get information about the currently selected objects.",
    },
    "export_file": {
        "description": "Export the active document to a file (STL or STEP format).",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Full path to the output file."},
                "fmt": {"type": "string", "description": "Format: 'stl' or 'step'."},
            },
            "required": ["filepath", "fmt"],
        },
    },
}


def get_tools_schema_markdown() -> str:
    """Return the tools registry as a Markdown string for agent context injection."""
    md = "## Available FreeCAD Tools\\n\\n"
    for name, tool in TOOLS_REGISTRY.items():
        md += f"### {name}\\n"
        md += f"- **Description**: {tool['description']}\\n"
        if "parameters" in tool:
            md += f"- **Parameters**: {json.dumps(tool['parameters'])}\\n"
    return md
