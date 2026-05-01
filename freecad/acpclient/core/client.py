# Copyright (C) 2026 FreeCAD ACP Client Contributors
# SPDX-License-Identifier: LGPL-3.0-or-later

from __future__ import annotations

import asyncio
import os
import threading
import uuid
from typing import Any

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

    def __init__(self, thread_bridge: ACPClientThread) -> None:
        self.thread_bridge: ACPClientThread = thread_bridge

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        """Receive and relay agent message chunks to the UI thread."""
        if isinstance(update, AgentMessageChunk) and isinstance(update.content, TextContentBlock):
            self.thread_bridge.message_received.emit("Agent", update.content.text)

    async def read_text_file(self, path: str, session_id: str, **kwargs: Any) -> ReadTextFileResponse:
        """Read and return the contents of a text file."""
        try:
            with open(path) as f:
                content = f.read()
            return ReadTextFileResponse(content=content)
        except Exception as e:
            raise RequestError.invalid_params(str(e)) from e

    async def write_text_file(self, content: Any, path: str, session_id: str, **kwargs: Any) -> Any:
        """Write text file (not supported)."""
        raise RequestError.method_not_found("write_text_file")

    async def create_terminal(self, command: str, session_id: str, **kwargs: Any) -> Any:
        """Create a terminal (not supported)."""
        raise RequestError.method_not_found("create_terminal")

    async def terminal_output(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        """Terminal output handling (not supported)."""
        raise RequestError.method_not_found("terminal_output")

    async def release_terminal(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        """Release a terminal (not supported)."""
        raise RequestError.method_not_found("release_terminal")

    async def wait_for_terminal_exit(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        """Wait for terminal exit (not supported)."""
        raise RequestError.method_not_found("wait_for_terminal_exit")

    async def kill_terminal(self, session_id: str, terminal_id: str, **kwargs: Any) -> Any:
        """Kill a terminal (not supported)."""
        raise RequestError.method_not_found("kill_terminal")

    async def ext_notification(self, method: Any, params: Any) -> None:
        """Handle external notifications (no-op)."""
        pass

    async def request_permission(
        self, options: Any, session_id: str, tool_call: Any, **kwargs: Any
    ) -> RequestPermissionResponse:
        """Request user permission for a tool invocation via a dialog."""
        title = "Permission Requested"
        description = f"The agent wants to use tool: {tool_call.get('title', 'Unknown')}"
        allowed = await self.thread_bridge.run_on_main_thread(
            self.thread_bridge.request_permission_signal, title, description
        )
        if allowed:
            return RequestPermissionResponse(outcome=AllowedOutcome(option_id=options[0].option_id, outcome="selected"))
        return RequestPermissionResponse(outcome=DeniedOutcome(outcome="denied"))

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle custom FreeCAD tools via extension methods."""
        import json

        if method == "read_document_state":
            doc_result: str = await self.thread_bridge.run_on_main_thread(self.thread_bridge.request_read_document)
            return {"result": doc_result}

        if method == "execute_python_script":
            script: str = params.get("script", "")
            title = "Python Execution Requested"
            description = f"The agent wants to execute the following Python script:\n\n{script}"
            allowed: bool = await self.thread_bridge.run_on_main_thread(
                self.thread_bridge.request_permission_signal, title, description
            )
            if not allowed:
                return {"error": "User denied permission to execute the script."}
            script_result: str = await self.thread_bridge.run_on_main_thread(
                self.thread_bridge.request_execute_script, script
            )
            return {"result": script_result}

        # Generic tool dispatch for all other tools
        result_json: str = await self.thread_bridge.run_on_main_thread(
            self.thread_bridge.request_run_tool, method, json.dumps(params)
        )
        result: dict[str, Any] = json.loads(result_json)
        if "error" in result:
            raise RequestError.method_not_found(method)
        return result


class ACPClientThread(QtCore.QThread):
    """Background thread running the asyncio event loop for ACP SDK."""

    message_received: QtCore.SignalInstance = QtCore.Signal(str, str)
    error_occurred: QtCore.SignalInstance = QtCore.Signal(str)
    connected: QtCore.SignalInstance = QtCore.Signal()
    disconnected: QtCore.SignalInstance = QtCore.Signal()
    processing_started: QtCore.SignalInstance = QtCore.Signal()
    processing_finished: QtCore.SignalInstance = QtCore.Signal()

    request_execute_script: QtCore.SignalInstance = QtCore.Signal(str, str)
    request_read_document: QtCore.SignalInstance = QtCore.Signal(str)
    request_permission_signal: QtCore.SignalInstance = QtCore.Signal(str, str, str)
    request_run_tool: QtCore.SignalInstance = QtCore.Signal(str, str, str)

    def __init__(self) -> None:
        super().__init__()
        self.loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: threading.Event = threading.Event()
        self.conn: Any = None
        self.session: Any = None
        self.ctx_mgr: Any = None
        self.proc: Any = None
        self.pending_requests: dict[str, asyncio.Future[Any]] = {}
        self._prompt_lock: asyncio.Lock | None = None

    async def run_on_main_thread(self, signal: QtCore.SignalInstance, *args: Any) -> Any:
        """Schedule execution on the main thread and return the result via a future."""
        assert self.loop is not None
        req_id: str = str(uuid.uuid4())
        fut: asyncio.Future[Any] = self.loop.create_future()
        self.pending_requests[req_id] = fut
        signal.emit(req_id, *args)
        return await fut

    def _resolve_request(self, req_id: str, result: Any) -> None:
        """Set the result on a pending future identified by req_id."""
        if req_id in self.pending_requests:
            assert self.loop is not None
            fut: asyncio.Future[Any] = self.pending_requests.pop(req_id)
            self.loop.call_soon_threadsafe(fut.set_result, result)

    @QtCore.Slot(str, str)
    def resolve_execute_script(self, req_id: str, result: str) -> None:
        """Resolve the pending future for a script execution request."""
        self._resolve_request(req_id, result)

    @QtCore.Slot(str, str)
    def resolve_read_document(self, req_id: str, result: str) -> None:
        """Resolve the pending future for a document read request."""
        self._resolve_request(req_id, result)

    @QtCore.Slot(str, bool)
    def resolve_permission(self, req_id: str, allowed: bool) -> None:
        """Resolve the pending future for a permission request."""
        self._resolve_request(req_id, allowed)

    @QtCore.Slot(str, str)
    def resolve_run_tool(self, req_id: str, result_json: str) -> None:
        """Resolve the pending future for a tool execution request."""
        self._resolve_request(req_id, result_json)

    def run(self) -> None:
        """Start the asyncio event loop on this thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._prompt_lock = asyncio.Lock()
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def stop(self) -> None:
        """Signal the event loop to stop and wait for the thread to finish."""
        self._stop_event.set()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait()

    def send_prompt(self, text: str) -> None:
        """Send a user prompt to the connected agent."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_send_prompt(text), self.loop)

    def cancel_prompt(self) -> None:
        """Cancel the currently processing agent prompt."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_cancel_prompt(), self.loop)

    async def _async_cancel_prompt(self) -> None:
        """Asynchronously cancel the current agent prompt."""
        if self.conn and self.session:
            await self.conn.cancel(self.session.session_id)

    async def _async_send_prompt(self, text: str) -> None:
        """Asynchronously send a prompt to the agent session."""
        assert self._prompt_lock is not None
        async with self._prompt_lock:
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

    def connect_to_agent(self, command_path: str) -> None:
        """Spawn a local agent process via stdio transport."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._async_connect(command_path), self.loop)

    async def _async_connect(self, command_path: str) -> None:
        """Asynchronously spawn and initialize an ACP agent process."""
        try:
            client: FreeCADACPClient = FreeCADACPClient(self)
            args: list[str] = command_path.split()
            cmd: str = args[0]
            cmd_args: list[str] = args[1:]

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

    def disconnect_from_agent(self) -> None:
        """Disconnect from the current agent and clean up resources."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_disconnect(), self.loop)

    async def _async_disconnect(self) -> None:
        """Asynchronously close the agent session and clean up resources."""
        try:
            if self.conn and self.session:
                await self.conn.close_session(self.session.session_id)
        except Exception as e:
            import sys

            print(f"ACP: Warning during close_session: {e}", file=sys.stderr)
        try:
            if self.ctx_mgr:
                await self.ctx_mgr.__aexit__(None, None, None)
        except Exception as e:
            import sys

            print(f"ACP: Warning during ctx_mgr teardown: {e}", file=sys.stderr)
        self.conn = None
        self.proc = None
        self.session = None
        self.ctx_mgr = None
        self.disconnected.emit()
