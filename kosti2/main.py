# main.py - Полный код FastAPI сервера для игры в кости с лобби
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List
import random
import string

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Лобби данные
lobbies: Dict[str, dict] = {}

class LobbyCreate(BaseModel):
    type: str  # "public" или "private"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/lobbies")
async def get_lobbies():
    public = []
    for lobby_id, data in lobbies.items():
        if data["type"] == "public":
            public.append({"id": lobby_id, "players": len(data["players"])})
    return public

@app.post("/api/lobbies")
async def create_lobby(lobby: LobbyCreate):
    lobby_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    password = ''.join(random.choices(string.digits, k=4)) if lobby.type == "private" else None
    lobbies[lobby_id] = {
        "type": lobby.type,
        "password": password,
        "players": []
    }
    return {"id": lobby_id, "password": password}

@app.post("/api/lobbies/{lobby_id}/join")
async def join_lobby(lobby_id: str, password: str = None):
    if lobby_id not in lobbies:
        return JSONResponse({"error": "Лобби не найдено"}, status_code=404)
    lobby = lobbies[lobby_id]
    if lobby["type"] == "private" and password != lobby["password"]:
        return JSONResponse({"error": "Неверный пароль"}, status_code=400)
    lobby["players"].append("Player")  # TODO: имя игрока
    return {"status": "ok", "ready": len(lobby["players"]) >= 2}

@app.get("/roll")
async def roll_dice():
    return {"dice": random.randint(1, 6)}

@app.get("/game")
async def get_game_state(player1: int = 0, player2: int = 0):
    return {"player1": player1, "player2": player2}

@app.get("/game/{lobby_id}", response_class=HTMLResponse)
async def game_page(lobby_id: str, request: Request):
    if lobby_id not in lobbies:
        return HTMLResponse("<h1>❌ Лобби не найдено</h1><a href='/'>← Назад</a>", status_code=404)
    return templates.TemplateResponse("game.html", {"request": request, "lobby_id": lobby_id})

if __name__ == "__main__":
    import uvicorn
    print("🚀 Kosti сервер: http://localhost:8010")
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
