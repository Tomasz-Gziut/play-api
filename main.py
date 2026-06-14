from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
import json

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
async def create_room(name: str, game: str):
    if game not in AVAILABLE_GAMES:
        raise HTTPException(status_code=400, detail=f"Unknown game. Available: {AVAILABLE_GAMES}")
    room_id = manager.create_room(name, game)
    return {"room_id": room_id, "name": name, "game": game}


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

    # notify everyone (including self) about new player
    await manager.broadcast(room_id, {
        "type": "player_joined",
        "nick": nick,
        "players": manager.get_players(room_id),
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
                # forward unknown types as-is so game logic can be added later
                await manager.broadcast(room_id, {
                    "type": msg_type,
                    "from": nick,
                    **{k: v for k, v in msg.items() if k not in ("type",)},
                })

    except WebSocketDisconnect:
        manager.disconnect(room_id, nick)
        await manager.broadcast(room_id, {
            "type": "player_left",
            "nick": nick,
            "players": manager.get_players(room_id),
        })
