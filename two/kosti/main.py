# main.py - FastAPI сервер с WebSocket для онлайн игры в кости
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random
import json
from typing import Dict, List
import uuid
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище лобби и подключений
lobbies: Dict[str, dict] = {}
connections: Dict[str, WebSocket] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, lobby_id: str, player_id: str):
        await websocket.accept()
        if lobby_id not in self.active_connections:
            self.active_connections[lobby_id] = []
        self.active_connections[lobby_id].append(websocket)
        connections[player_id] = websocket

    def disconnect(self, websocket: WebSocket, lobby_id: str, player_id: str):
        if lobby_id in self.active_connections:
            if websocket in self.active_connections[lobby_id]:
                self.active_connections[lobby_id].remove(websocket)
        if player_id in connections:
            del connections[player_id]

    async def broadcast_to_lobby(self, lobby_id: str, message: dict):
        if lobby_id in self.active_connections:
            for connection in self.active_connections[lobby_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

    async def send_personal_message(self, player_id: str, message: dict):
        if player_id in connections:
            try:
                await connections[player_id].send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/roll")
async def roll_dice():
    return {"dice": random.randint(1, 6)}

@app.post("/create-lobby")
async def create_lobby(request: Request):
    data = await request.json()
    lobby_id = str(uuid.uuid4())[:8]
    
    lobbies[lobby_id] = {
        "id": lobby_id,
        "host": data.get("host_name", "Игрок"),
        "max_players": data.get("max_players", 2),
        "dice_count": data.get("dice_count", 1),
        "win_score": data.get("win_score", 1),
        "is_private": data.get("is_private", False),
        "password": data.get("password", ""),
        "players": [],
        "created_at": datetime.now().isoformat(),
        "status": "waiting",  # waiting, playing, finished
        "game_state": {
            "current_round": 0,
            "player_scores": {},
            "current_rolls": {}
        }
    }
    
    return {"success": True, "lobby_id": lobby_id, "lobby": lobbies[lobby_id]}

@app.get("/lobbies")
async def get_lobbies():
    # Возвращаем только открытые лобби и те, что в статусе ожидания
    public_lobbies = {
        lid: {
            "id": lobby["id"],
            "host": lobby["host"],
            "max_players": lobby["max_players"],
            "current_players": len(lobby["players"]),
            "dice_count": lobby["dice_count"],
            "win_score": lobby["win_score"],
            "is_private": lobby["is_private"],
            "status": lobby["status"]
        }
        for lid, lobby in lobbies.items()
        if lobby["status"] == "waiting"
    }
    return {"lobbies": public_lobbies}

@app.post("/join-lobby")
async def join_lobby(request: Request):
    data = await request.json()
    lobby_id = data.get("lobby_id")
    player_name = data.get("player_name", "Игрок")
    password = data.get("password", "")
    
    if lobby_id not in lobbies:
        return {"success": False, "error": "Лобби не найдено"}
    
    lobby = lobbies[lobby_id]
    
    # Проверка пароля для приватных лобби
    if lobby["is_private"] and lobby["password"] != password:
        return {"success": False, "error": "Неверный пароль"}
    
    # Проверка количества игроков
    if len(lobby["players"]) >= lobby["max_players"]:
        return {"success": False, "error": "Лобби заполнено"}
    
    player_id = str(uuid.uuid4())[:8]
    player = {
        "id": player_id,
        "name": player_name,
        "joined_at": datetime.now().isoformat()
    }
    
    lobby["players"].append(player)
    lobby["game_state"]["player_scores"][player_id] = 0
    
    return {
        "success": True,
        "player_id": player_id,
        "lobby": lobby
    }

@app.websocket("/ws/{lobby_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str, player_id: str):
    await manager.connect(websocket, lobby_id, player_id)
    
    try:
        # Отправляем приветственное сообщение
        await websocket.send_json({
            "type": "connected",
            "player_id": player_id,
            "lobby_id": lobby_id
        })
        
        # Уведомляем всех о новом игроке
        if lobby_id in lobbies:
            await manager.broadcast_to_lobby(lobby_id, {
                "type": "player_joined",
                "lobby": lobbies[lobby_id]
            })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "start_game":
                if lobby_id in lobbies:
                    lobbies[lobby_id]["status"] = "playing"
                    await manager.broadcast_to_lobby(lobby_id, {
                        "type": "game_started",
                        "lobby": lobbies[lobby_id]
                    })
            
            elif message["type"] == "roll_dice":
                player_id = message["player_id"]
                dice_count = lobbies[lobby_id]["dice_count"]
                
                # Бросаем кости
                rolls = [random.randint(1, 6) for _ in range(dice_count)]
                total = sum(rolls)
                
                lobbies[lobby_id]["game_state"]["current_rolls"][player_id] = {
                    "rolls": rolls,
                    "total": total
                }
                
                # Отправляем результат броска всем игрокам
                await manager.broadcast_to_lobby(lobby_id, {
                    "type": "dice_rolled",
                    "player_id": player_id,
                    "rolls": rolls,
                    "total": total,
                    "game_state": lobbies[lobby_id]["game_state"]
                })
            
            elif message["type"] == "end_round":
                # Определяем победителя раунда
                current_rolls = lobbies[lobby_id]["game_state"]["current_rolls"]
                if current_rolls:
                    winner_id = max(current_rolls.keys(), key=lambda k: current_rolls[k]["total"])
                    lobbies[lobby_id]["game_state"]["player_scores"][winner_id] += 1
                    
                    # Проверяем победителя игры
                    win_score = lobbies[lobby_id]["win_score"]
                    game_winner = None
                    for pid, score in lobbies[lobby_id]["game_state"]["player_scores"].items():
                        if score >= win_score:
                            game_winner = pid
                            break
                    
                    lobbies[lobby_id]["game_state"]["current_rolls"] = {}
                    lobbies[lobby_id]["game_state"]["current_round"] += 1
                    
                    await manager.broadcast_to_lobby(lobby_id, {
                        "type": "round_ended",
                        "round_winner": winner_id,
                        "game_winner": game_winner,
                        "game_state": lobbies[lobby_id]["game_state"]
                    })
            
            elif message["type"] == "new_game":
                lobbies[lobby_id]["game_state"]["current_round"] = 0
                lobbies[lobby_id]["game_state"]["player_scores"] = {
                    p["id"]: 0 for p in lobbies[lobby_id]["players"]
                }
                lobbies[lobby_id]["game_state"]["current_rolls"] = {}
                
                await manager.broadcast_to_lobby(lobby_id, {
                    "type": "game_reset",
                    "lobby": lobbies[lobby_id]
                })
            
            elif message["type"] == "chat_message":
                await manager.broadcast_to_lobby(lobby_id, {
                    "type": "chat_message",
                    "player_id": player_id,
                    "message": message["message"],
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, lobby_id, player_id)
        
        # Удаляем игрока из лобби
        if lobby_id in lobbies:
            lobbies[lobby_id]["players"] = [
                p for p in lobbies[lobby_id]["players"] if p["id"] != player_id
            ]
            
            # Если лобби пусто, удаляем его
            if len(lobbies[lobby_id]["players"]) == 0:
                del lobbies[lobby_id]
            else:
                # Уведомляем остальных игроков
                await manager.broadcast_to_lobby(lobby_id, {
                    "type": "player_left",
                    "player_id": player_id,
                    "lobby": lobbies[lobby_id]
                })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)