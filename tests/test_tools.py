"""Unit tests for tool functions in freecad.acpclient.core.tools.

Each test injects mock app/gui objects via optional parameters rather than
relying on sys.modules monkeypatching.
"""

from unittest.mock import MagicMock

from freecad.acpclient.core.tools import (
    create_primitive,
    delete_object,
    export_file,
    get_selection,
    get_tools_schema_markdown,
    read_document_state,
    run_tool,
)


def _mock_doc(objects=None, name="Doc", label="Document"):
    doc = MagicMock()
    doc.Name = name
    doc.Label = label
    doc.Objects = objects or []
    doc.openTransaction = MagicMock()
    doc.commitTransaction = MagicMock()
    doc.recompute = MagicMock()
    doc.abortTransaction = MagicMock()
    return doc


def _mock_app(doc=None):
    app = MagicMock()
    app.ActiveDocument = doc
    return app


def _mock_gui(selection=None):
    gui = MagicMock()
    gui.Selection = MagicMock()
    gui.Selection.getSelection.return_value = selection or []
    return gui


def _mock_object(name="Box", label="Box", type_id="Part::Box", placement=None, visibility=True):
    obj = MagicMock()
    obj.Name = name
    obj.Label = label
    obj.TypeId = type_id
    obj.Visibility = visibility
    obj.Placement = placement
    obj.PropertiesList = ()
    return obj


class TestReadDocumentState:
    def test_no_document(self):
        result = read_document_state(app=_mock_app(doc=None), gui=_mock_gui())
        assert result == {"error": "No active document"}

    def test_with_objects(self):
        obj = _mock_object(name="MyBox", type_id="Part::Box")
        doc = _mock_doc(objects=[obj], name="MyDoc")
        state = read_document_state(app=_mock_app(doc=doc), gui=_mock_gui())

        assert state["name"] == "MyDoc"
        assert len(state["objects"]) == 1
        assert state["objects"][0]["name"] == "MyBox"
        assert state["objects"][0]["selected"] is False


class TestCreatePrimitive:
    def test_no_document(self):
        result = create_primitive("Box", {}, app=_mock_app(doc=None))
        assert "error" in result
        assert "No active document" in result["error"]

    def test_unknown_type(self):
        doc = _mock_doc()
        result = create_primitive("Dodecahedron", {}, app=_mock_app(doc=doc))
        assert "error" in result

    def test_box_success(self):
        doc = _mock_doc()
        doc.addObject = MagicMock(return_value=MagicMock())
        result = create_primitive("Box", {"length": 2, "width": 3, "height": 4}, app=_mock_app(doc=doc))
        assert "Created Box" in result["result"]
        doc.openTransaction.assert_called_once()
        doc.commitTransaction.assert_called_once()
        doc.addObject.assert_called_once_with("Part::Feature", "Box")


class TestDeleteObject:
    def test_no_document(self):
        result = delete_object("X", app=_mock_app(doc=None))
        assert result == {"error": "No active document"}

    def test_not_found(self):
        doc = _mock_doc()
        doc.getObject = MagicMock(return_value=None)
        result = delete_object("X", app=_mock_app(doc=doc))
        assert result == {"error": "Object 'X' not found"}

    def test_success(self):
        doc = _mock_doc()
        doc.getObject = MagicMock(return_value=MagicMock())
        result = delete_object("Y", app=_mock_app(doc=doc))
        assert "Deleted object" in result["result"]
        doc.removeObject.assert_called_once_with("Y")
        doc.recompute.assert_called_once()


class TestGetSelection:
    def test_empty(self):
        result = get_selection(gui=_mock_gui(selection=[]))
        assert result["count"] == 0
        assert "No objects selected" in result["result"]

    def test_with_objects(self):
        obj = _mock_object(name="SelBox", type_id="Part::Box")
        obj.Placement = None
        result = get_selection(gui=_mock_gui(selection=[obj]))
        assert result["count"] == 1
        assert result["objects"][0]["name"] == "SelBox"


class TestExportFile:
    def test_no_document(self):
        result = export_file("/tmp/test.stl", "stl", app=_mock_app(doc=None))
        assert result == {"error": "No active document"}

    def test_unsupported_format(self):
        doc = _mock_doc()
        result = export_file("/tmp/test.obj", "obj", app=_mock_app(doc=doc))
        assert "Unsupported format" in result["error"]


class TestRunTool:
    def test_unknown(self):
        result = run_tool("bogus_tool", {}, app=_mock_app(), gui=_mock_gui())
        assert result == {"error": "Unknown tool: bogus_tool"}

    def test_known(self):
        doc = _mock_doc(objects=[])
        result = run_tool("read_document_state", {}, app=_mock_app(doc=doc), gui=_mock_gui())
        assert result["name"] == "Doc"
        assert result["objects"] == []


class TestGetToolsSchemaMarkdown:
    def test_returns_markdown(self):
        md = get_tools_schema_markdown()
        assert "## Available FreeCAD Tools" in md
        assert "read_document_state" in md
        assert "create_primitive" in md
        assert "execute_python_script" in md


class TestExecutePythonScriptSync:
    def test_success(self):
        import sys

        _mod = MagicMock()
        sys.modules["freecad.acpclient.core.tools.execute_python_script_sync"] = None
        try:
            from freecad.acpclient.core.tools import execute_python_script_sync

            result = execute_python_script_sync("x = 1\nprint('ok')")
            assert "ok" in result
        finally:
            sys.modules.pop("freecad.acpclient.core.tools.execute_python_script_sync", None)

    def test_error(self):
        sys_mod = __import__("sys")
        try:
            from freecad.acpclient.core.tools import execute_python_script_sync

            result = execute_python_script_sync("raise ValueError('bad')")
            assert "ValueError" in result
            assert "bad" in result
        finally:
            sys_mod.modules.pop("freecad.acpclient.core.tools.execute_python_script_sync", None)
