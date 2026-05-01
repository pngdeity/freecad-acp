import asyncio
import os
import threading
import uuid

from acp import PROTOCOL_VERSION, RequestError, spawn_agent_process, text_block
from acp.interfaces import Client
from acp.schema import (
    AgentMessageChunk,
    AllowedOutcome,
    ClientCapabilities,
    DeniedOutcome,
    FileSystemCapabilities,
    ReadTextFileResponse,
    RequestPermissionResponse,
    TextContentBlock,
)
from PySide6 import QtCore


class FreeCADACPClient(Client):
    """Implementation of the ACP Client interface for FreeCAD.

    Handles tool calls and session updates.
    """

    def __init__(self, thread_bridge):
        self.thread_bridge = thread_bridge

    async def session_update(self, session_id: str, update, **kwargs) -> None:
        if isinstance(update, AgentMessageChunk) and isinstance(update.content, TextContentBlock):
            self.thread_bridge.message_received.emit("Agent", update.content.text)

    async def read_text_file(self, path: str, session_id: str, **kwargs) -> ReadTextFileResponse:
        try:
            with open(path) as f:
                content = f.read()
            return ReadTextFileResponse(content=content)
        except Exception as e:
            raise RequestError.invalid_params(str(e)) from e

    async def write_text_file(self, content, path, session_id, **kwargs):
        raise RequestError.method_not_found("write_text_file")

    async def create_terminal(self, command, session_id, **kwargs):
        raise RequestError.method_not_found("create_terminal")

    async def terminal_output(self, session_id, terminal_id, **kwargs):
        raise RequestError.method_not_found("terminal_output")

    async def release_terminal(self, session_id, terminal_id, **kwargs):
        raise RequestError.method_not_found("release_terminal")

    async def wait_for_terminal_exit(self, session_id, terminal_id, **kwargs):
        raise RequestError.method_not_found("wait_for_terminal_exit")

    async def kill_terminal(self, session_id, terminal_id, **kwargs):
        raise RequestError.method_not_found("kill_terminal")

    async def ext_notification(self, method, params):
        pass

    async def request_permission(self, options, session_id, tool_call, **kwargs):
        title = "Permission Requested"
        description = f"The agent wants to use tool: {tool_call.get('title', 'Unknown')}"
        allowed = await self.thread_bridge.run_on_main_thread(
            self.thread_bridge.request_permission_signal, title, description
        )
        if allowed:
            return RequestPermissionResponse(
                outcome=AllowedOutcome(option_id=options[0].option_id, outcome="selected")
            )
        return RequestPermissionResponse(outcome=DeniedOutcome(outcome="denied"))

    async def ext_method(self, method, params):
        """Handle custom FreeCAD tools via extension methods."""
        import json

        if method == "read_document_state":
            result = await self.thread_bridge.run_on_main_thread(self.thread_bridge.request_read_document)
            return {"result": result}

        if method == "execute_python_script":
            script = params.get("script", "")
            title = "Python Execution Requested"
            description = f"The agent wants to execute the following Python script:\n\n{script}"
            allowed = await self.thread_bridge.run_on_main_thread(
                self.thread_bridge.request_permission_signal, title, description
            )
            if not allowed:
                return {"error": "User denied permission to execute the script."}
            result = await self.thread_bridge.run_on_main_thread(
                self.thread_bridge.request_execute_script, script
            )
            return {"result": result}

        # Generic tool dispatch for all other tools
        result_json = await self.thread_bridge.run_on_main_thread(
            self.thread_bridge.request_run_tool, method, json.dumps(params)
        )
        result = json.loads(result_json)
        if "error" in result:
            raise RequestError.method_not_found(method)
        return result


class ACPClientThread(QtCore.QThread):
    """Background thread running the asyncio event loop for ACP SDK."""

    message_received = QtCore.Signal(str, str)
    error_occurred = QtCore.Signal(str)
    connected = QtCore.Signal()
    disconnected = QtCore.Signal()
    processing_started = QtCore.Signal()
    processing_finished = QtCore.Signal()

    request_execute_script = QtCore.Signal(str, str)
    request_read_document = QtCore.Signal(str)
    request_permission_signal = QtCore.Signal(str, str, str)
    request_run_tool = QtCore.Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.loop = None
        self._stop_event = threading.Event()
        self.conn = None
        self.session = None
        self.ctx_mgr = None
        self.proc = None
        self.pending_requests: dict = {}

    async def run_on_main_thread(self, signal, *args):
        req_id = str(uuid.uuid4())
        fut = self.loop.create_future()
        self.pending_requests[req_id] = fut
        signal.emit(req_id, *args)
        return await fut

    @QtCore.Slot(str, str)
    def resolve_execute_script(self, req_id, result):
        if req_id in self.pending_requests:
            fut = self.pending_requests.pop(req_id)
            self.loop.call_soon_threadsafe(fut.set_result, result)

    @QtCore.Slot(str, str)
    def resolve_read_document(self, req_id, result):
        if req_id in self.pending_requests:
            fut = self.pending_requests.pop(req_id)
            self.loop.call_soon_threadsafe(fut.set_result, result)

    @QtCore.Slot(str, bool)
    def resolve_permission(self, req_id, allowed):
        if req_id in self.pending_requests:
            fut = self.pending_requests.pop(req_id)
            self.loop.call_soon_threadsafe(fut.set_result, allowed)

    @QtCore.Slot(str, str)
    def resolve_run_tool(self, req_id, result_json):
        if req_id in self.pending_requests:
            fut = self.pending_requests.pop(req_id)
            self.loop.call_soon_threadsafe(fut.set_result, result_json)

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def stop(self):
        self._stop_event.set()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait()

    def send_prompt(self, text):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_send_prompt(text), self.loop)

    async def _async_send_prompt(self, text):
        if not self.conn or not self.session:
            self.error_occurred.emit("Not connected to any agent.")
            self.processing_finished.emit()
            return
        self.processing_started.emit()
        try:
            await self.conn.prompt(
                session_id=self.session.session_id,
                prompt=[text_block(text)],
            )
        except Exception as e:
            self.error_occurred.emit(f"Error: {e}")
        finally:
            self.processing_finished.emit()

    def connect_to_agent(self, command_path):
        """Spawns a local agent process via stdio."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._async_connect(command_path), self.loop)

    async def _async_connect(self, command_path):
        try:
            client = FreeCADACPClient(self)
            args = command_path.split()
            cmd = args[0]
            cmd_args = args[1:]

            self.ctx_mgr = spawn_agent_process(client, cmd, *cmd_args)
            self.conn, self.proc = await self.ctx_mgr.__aenter__()

            await self.conn.initialize(
                protocol_version=PROTOCOL_VERSION,
                client_capabilities=ClientCapabilities(
                    fs=FileSystemCapabilities(read_text_file=True),
                    terminal=False,
                ),
            )
            self.session = await self.conn.new_session(cwd=os.getcwd(), mcp_servers=[])
            self.connected.emit()

        except Exception as e:
            self.error_occurred.emit(f"Failed to spawn agent: {e}")

    def disconnect_from_agent(self):
        """Disconnect from the current agent and clean up resources."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_disconnect(), self.loop)

    async def _async_disconnect(self):
        try:
            if self.conn and self.session:
                await self.conn.close_session(self.session.session_id)
        except Exception:
            pass
        try:
            if self.ctx_mgr:
                await self.ctx_mgr.__aexit__(None, None, None)
        except Exception:
            pass
        self.conn = None
        self.proc = None
        self.session = None
        self.ctx_mgr = None
        self.disconnected.emit()
