import asyncio
import json
import os
import sys
import tempfile
import threading
import websockets
from PySide6.QtCore import QCoreApplication, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backends.bitchord_bridge import BitChordBridge


def run_test():
    app = QCoreApplication(sys.argv)
    received_commands = []
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        bridge_file = os.path.join(tmpdir, "bridge.json")
        state = {"token": "token-v1", "port": 0, "stop": False, "drop_client": False}
        server_ready = threading.Event()
        active_ws = []

        async def process_request(connection, request):
            if f"token={state['token']}" not in request.path:
                return connection.respond(401, "Unauthorized\n")
            return None

        async def handler(ws):
            active_ws.append(ws)
            try:
                await ws.send(json.dumps({
                    "status": "playing",
                    "song": {
                        "title": f"Song ({state['token']})",
                        "artist": "M83",
                        "album": "Hurry Up",
                    },
                    "progressMs": 15000,
                    "durationMs": 243000,
                    "albumArtBase64": tiny_png_b64,
                }))
                async for msg in ws:
                    received_commands.append(json.loads(msg))
            except websockets.ConnectionClosed:
                pass
            finally:
                if ws in active_ws:
                    active_ws.remove(ws)

        server_loop = None

        def run_server():
            nonlocal server_loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server_loop = loop

            async def _serve():
                async with websockets.serve(
                    handler, "127.0.0.1", 0, process_request=process_request
                ) as srv:
                    state["port"] = srv.sockets[0].getsockname()[1]
                    server_ready.set()
                    while not state["stop"]:
                        if state["drop_client"] and active_ws:
                            state["drop_client"] = False
                            for w in list(active_ws):
                                await w.close(code=1001, reason="BitChord restarting")
                        await asyncio.sleep(0.05)

            loop.run_until_complete(_serve())
            loop.close()

        srv_thread = threading.Thread(target=run_server, daemon=True)
        srv_thread.start()
        assert server_ready.wait(timeout=5), "Mock WebSocket server failed to start"

        # 1. Start with a STALE bridge.json (wrong token -> HTTP 401 Unauthorized)
        with open(bridge_file, "w", encoding="utf-8") as f:
            json.dump({"port": state["port"], "token": "stale-old-token"}, f)

        bridge = BitChordBridge(bridge_path=bridge_file, debug=False)
        bridge.WAIT_INTERVAL_SEC = 0.25  # fast retry interval for test speed

        conn_events = []
        state_events = []
        progress_events = []
        art_events = []

        bridge.connectionStatusChanged.connect(conn_events.append)
        bridge.stateChanged.connect(lambda s, t, a, al: state_events.append((s, t, a, al)))
        bridge.progressChanged.connect(lambda p, d: progress_events.append((p, d)))
        bridge.albumArtChanged.connect(art_events.append)

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("bitChordBridge", bridge)
        qml_path = os.path.join(tmpdir, "probe.qml")
        with open(qml_path, "w", encoding="utf-8") as f:
            f.write(
                "import QtQml\n"
                "QtObject {\n"
                "  property string conn: ''\n"
                "  property string title: ''\n"
                "  property int progress: -1\n"
                "  property string art: ''\n"
                "  property Connections _c: Connections {\n"
                "    target: bitChordBridge\n"
                "    function onConnectionStatusChanged(s) { conn = s }\n"
                "    function onStateChanged(st, t, a, al) { title = t }\n"
                "    function onProgressChanged(p, d) { progress = p }\n"
                "    function onAlbumArtChanged(b) { art = b }\n"
                "  }\n"
                "}\n"
            )
        engine.load(QUrl.fromLocalFile(qml_path))
        probe = engine.rootObjects()[0]

        bridge.start()

        # Step 2: Update bridge.json with valid token-v1 -> connects
        def write_v1():
            with open(bridge_file, "w", encoding="utf-8") as f:
                json.dump({"port": state["port"], "token": "token-v1"}, f)

        # Step 3: Send controls, then simulate BitChord closing & restarting with token-v2
        def send_controls_and_restart():
            bridge.togglePlay()
            bridge.nextTrack()
            bridge.previousTrack()
            bridge.seek(45000)
            QTimer.singleShot(150, simulate_restart)

        def simulate_restart():
            state["token"] = "token-v2"
            state["drop_client"] = True
            with open(bridge_file, "w", encoding="utf-8") as f:
                json.dump({"port": state["port"], "token": "token-v2"}, f)

        def finish():
            state["stop"] = True
            bridge.stop()
            app.quit()

        QTimer.singleShot(350, write_v1)
        QTimer.singleShot(1000, send_controls_and_restart)
        QTimer.singleShot(2100, finish)
        app.exec()

        assert conn_events.count("Waiting for BitChord...") >= 2, f"Expected initial + reconnect wait events: {conn_events}"
        assert conn_events.count("Connected") >= 2, f"Expected initial + restarted Connected events: {conn_events}"
        assert ("playing", "Song (token-v1)", "M83", "Hurry Up") in state_events, f"Missing v1 state: {state_events}"
        assert ("playing", "Song (token-v2)", "M83", "Hurry Up") in state_events, f"Missing v2 state after restart: {state_events}"
        assert ("stopped", "", "", "") in state_events, f"Missing disconnect reset state: {state_events}"
        assert (15000, 243000) in progress_events, f"Bad progress events: {progress_events}"
        assert any(a == f"data:image/png;base64,{tiny_png_b64}" for a in art_events), f"Bad art events: {art_events}"

        assert probe.property("title") == "Song (token-v2)", f"QML probe title after restart mismatch: {probe.property('title')}"
        assert probe.property("progress") == 15000, f"QML probe progress mismatch: {probe.property('progress')}"
        assert probe.property("art") == f"data:image/png;base64,{tiny_png_b64}", "QML probe art mismatch"

        expected_cmds = [
            {"command": "toggle_play"},
            {"command": "next"},
            {"command": "previous"},
            {"command": "seek", "positionMs": 45000},
        ]
        assert received_commands == expected_cmds, f"Command mismatch: {received_commands}"
        print("[PASS] Resilient Connect loop verified: stale 401 -> connect (token-v1) -> disconnect -> reconnect (token-v2) + QML signals + commands.")


if __name__ == "__main__":
    run_test()
