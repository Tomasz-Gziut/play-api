from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.staticfiles import StaticFiles
import json
import os

from manager import RoomManager, AVAILABLE_GAMES

app = FastAPI(title="Turn-based Game API")
manager = RoomManager()


@app.get("/games")
async def list_games():
    return AVAILABLE_GAMES


@app.get("/rooms")
async def list_rooms():
    return manager.get_rooms()


@app.post("/rooms")
async def create_room(name: str, game: str, nick: str):
    if game not in AVAILABLE_GAMES:
        raise HTTPException(status_code=400, detail=f"Unknown game. Available: {AVAILABLE_GAMES}")
    if not nick.strip():
        raise HTTPException(status_code=400, detail="Nick required")
    room_id = manager.create_room(name, game, host=nick.strip())
    return {"room_id": room_id, "name": name, "game": game, "host": nick.strip()}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    nick: str = Query(...),
):
    room = manager.get_room(room_id)
    if room is None:
        await websocket.accept()
        await websocket.close(code=4004, reason="Room not found")
        return

    await websocket.accept()
    if nick in room.connections:
        await websocket.close(code=4001, reason="Nick already taken")
        return
    manager.register(websocket, room_id, nick)

    await manager.broadcast(room_id, {
        "type": "player_joined",
        "nick": nick,
        "players": manager.get_players(room_id),
        "host": room.host,
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send(room_id, nick, {"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "message":
                await manager.broadcast(room_id, {
                    "type": "message",
                    "from": nick,
                    "data": msg.get("data"),
                })
            else:
                await manager.broadcast(room_id, {
                    "type": msg_type,
                    "from": nick,
                    **{k: v for k, v in msg.items() if k != "type"},
                })

    except WebSocketDisconnect:
        manager.disconnect(room_id, nick)
        await manager.broadcast(room_id, {
            "type": "player_left",
            "nick": nick,
            "players": manager.get_players(room_id),
            "host": room.host,
        })


# Serve built Svelte app — must be last (catches remaining paths)
_static_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="frontend")
