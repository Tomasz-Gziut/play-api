from fastapi import WebSocket
from dataclasses import dataclass, field
import uuid
import json


AVAILABLE_GAMES = [
    "tictactoe",
    "checkers",
    "uno",
]


@dataclass
class Room:
    id: str
    name: str
    game: str
    connections: dict = field(default_factory=dict)  # nick -> WebSocket


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}

    def create_room(self, name: str, game: str) -> str:
        room_id = str(uuid.uuid4())[:8]
        self.rooms[room_id] = Room(id=room_id, name=name, game=game)
        return room_id

    def get_room(self, room_id: str) -> Room | None:
        return self.rooms.get(room_id)

    def get_rooms(self) -> list:
        return [
            {"id": r.id, "name": r.name, "game": r.game, "players": list(r.connections.keys())}
            for r in self.rooms.values()
        ]

    def get_players(self, room_id: str) -> list[str]:
        room = self.rooms.get(room_id)
        return list(room.connections.keys()) if room else []

    def register(self, websocket: WebSocket, room_id: str, nick: str):
        self.rooms[room_id].connections[nick] = websocket

    def disconnect(self, room_id: str, nick: str):
        room = self.rooms.get(room_id)
        if room:
            room.connections.pop(nick, None)

    async def broadcast(self, room_id: str, message: dict, exclude: str | None = None):
        room = self.rooms.get(room_id)
        if not room:
            return
        dead = []
        for nick, ws in room.connections.items():
            if nick == exclude:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(nick)
        for nick in dead:
            room.connections.pop(nick, None)

    async def send(self, room_id: str, nick: str, message: dict):
        room = self.rooms.get(room_id)
        if room and nick in room.connections:
            await room.connections[nick].send_text(json.dumps(message))
