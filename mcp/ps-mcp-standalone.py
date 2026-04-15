"""
Standalone Photoshop MCP Server with built-in proxy.
Combines proxy server (replaces Node.js proxy) + MCP HTTP/SSE server in one process.
Usage: uv run python ps-mcp-standalone.py
"""

import sys
import os
import threading
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import socketio
import uvicorn

PROXY_PORT = 3001
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))

# --- Built-in Proxy Server (async) ---
application_clients = {}

proxy_sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    max_http_buffer_size=50 * 1024 * 1024,
)

proxy_app = socketio.ASGIApp(proxy_sio)

@proxy_sio.event
async def connect(sid, environ):
    print(f"[Proxy] Client connected: {sid}")

@proxy_sio.on('register')
async def on_register(sid, data):
    application = data.get('application', '')
    print(f"[Proxy] Client {sid} registered for: {application}")
    await proxy_sio.save_session(sid, {'application': application})
    if application not in application_clients:
        application_clients[application] = set()
    application_clients[application].add(sid)
    await proxy_sio.emit('registration_response', {
        'type': 'registration',
        'status': 'success',
        'message': f'Registered for {application}',
    }, to=sid)

@proxy_sio.on('command_packet')
async def on_command_packet(sid, data):
    application = data.get('application', '')
    command = data.get('command', {})
    print(f"[Proxy] Command from {sid} for {application}")
    packet = {
        'senderId': sid,
        'application': application,
        'command': command,
    }
    if application in application_clients:
        for client_id in application_clients[application]:
            await proxy_sio.emit('command_packet', packet, to=client_id)
    else:
        print(f"[Proxy] No clients registered for: {application}")

@proxy_sio.on('command_packet_response')
async def on_command_packet_response(sid, data):
    packet = data.get('packet', {})
    sender_id = packet.get('senderId')
    if sender_id:
        await proxy_sio.emit('packet_response', packet, to=sender_id)
        print(f"[Proxy] Response sent to {sender_id}")

@proxy_sio.event
async def disconnect(sid):
    print(f"[Proxy] Client disconnected: {sid}")
    for app in list(application_clients.keys()):
        application_clients[app].discard(sid)
        if not application_clients[app]:
            del application_clients[app]

def run_proxy():
    print(f"[Proxy] adb-mcp Command proxy server running on ws://0.0.0.0:{PROXY_PORT}")
    sys.stdout.flush()
    uvicorn.run(proxy_app, host='0.0.0.0', port=PROXY_PORT, log_level='warning')

# --- MCP Server ---
def run_mcp():
    # Resolve base dir: works both as .py script and PyInstaller exe
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Add base_dir to sys.path so core, fonts, logger, socket_client can be found
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ps_mcp",
        os.path.join(base_dir, "ps-mcp.py"),
    )
    ps_mcp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ps_mcp)
    ps_mcp.mcp.run(transport="sse")

# --- Main ---
if __name__ == "__main__":
    print("=" * 60)
    print("Photoshop MCP Standalone Server")
    print(f"  Proxy:  ws://0.0.0.0:{PROXY_PORT}")
    print(f"  MCP:    http://0.0.0.0:{MCP_PORT}/sse")
    print("=" * 60)

    proxy_thread = threading.Thread(target=run_proxy, daemon=True)
    proxy_thread.start()

    time.sleep(1)

    run_mcp()
