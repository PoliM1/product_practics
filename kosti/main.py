# main.py - Полный код FastAPI сервера для игры в кости с онлайн режимом
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict
import random
import string
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище для онлайн-игр
lobbies: Dict[str, dict] = {}
connections: Dict[str, WebSocket] = {}

def generate_room_id():
    """Генерирует уникальный ID комнаты"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Оффлайн режим
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/roll")
async def roll_dice():
    return {"dice": random.randint(1, 6)}

@app.get("/game")
async def get_game_state(player1: int = 0, player2: int = 0):
    return {"player1": player1, "player2": player2}

# Онлайн режим
@app.get("/online", response_class=HTMLResponse)
async def online_lobbies(request: Request):
    return templates.TemplateResponse("lobbies.html", {"request": request})

@app.get("/waiting/{room_id}", response_class=HTMLResponse)
async def waiting_room(request: Request, room_id: str):
    if room_id not in lobbies:
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("waiting.html", {"request": request, "room_id": room_id})

@app.get("/online-game/{room_id}", response_class=HTMLResponse)
async def online_game(request: Request, room_id: str):
    if room_id not in lobbies:
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("game-online.html", {"request": request, "room_id": room_id})

# WebSocket для онлайн-игры
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    connections[client_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'get_lobbies':
                await handle_get_lobbies(websocket)
            
            elif message['type'] == 'create_lobby':
                await handle_create_lobby(websocket, client_id, message['data'])
            
            elif message['type'] == 'join_lobby':
                await handle_join_lobby(websocket, client_id, message['data'])
            
            elif message['type'] == 'start_game':
                await handle_start_game(message['data']['room_id'])
            
            elif message['type'] == 'roll_dice':
                await handle_roll_dice(message['data']['room_id'], client_id)
            
            elif message['type'] == 'leave_lobby':
                await handle_leave_lobby(client_id, message['data'].get('room_id'))
                
    except WebSocketDisconnect:
        await handle_disconnect(client_id)
        if client_id in connections:
            del connections[client_id]

async def handle_get_lobbies(websocket: WebSocket):
    """Отправить список публичных лобби"""
    public_lobbies = []
    for room_id, lobby in lobbies.items():
        if not lobby['is_private'] and not lobby['game_started']:
            public_lobbies.append({
                'room_id': room_id,
                'host_name': lobby['host_name'],
                'players_count': len(lobby['players']),
                'max_players': lobby['max_players'],
                'dice_count': lobby['dice_count'],
                'max_score': lobby['max_score']
            })
    
    await websocket.send_json({
        'type': 'lobbies_list',
        'lobbies': public_lobbies
    })

async def handle_create_lobby(websocket: WebSocket, client_id: str, data: dict):
    """Создать новое лобби"""
    room_id = generate_room_id()
    password = data.get('password', None)  # Берем пароль от пользователя
    
    lobby = {
        'room_id': room_id,
        'host_id': client_id,
        'host_name': data['host_name'],
        'is_private': data['is_private'],
        'password': password,
        'max_players': data['max_players'],
        'dice_count': data['dice_count'],
        'max_score': data['max_score'],
        'players': [{
            'id': client_id,
            'name': data['host_name'],
            'is_host': True,
            'score': 0
        }],
        'game_started': False,
        'current_turn': 0
    }
    
    lobbies[room_id] = lobby
    
    # Уведомляем создателя
    await websocket.send_json({
        'type': 'lobby_created',
        'room_id': room_id,
        'password': password
    })
    
    # Уведомляем всех о новом публичном лобби
    if not data['is_private']:
        await broadcast_all({
            'type': 'new_lobby',
            'lobby': {
                'room_id': room_id,
                'host_name': data['host_name'],
                'players_count': 1,
                'max_players': data['max_players'],
                'dice_count': data['dice_count'],
                'max_score': data['max_score']
            }
        })

async def handle_join_lobby(websocket: WebSocket, client_id: str, data: dict):
    """Присоединиться к лобби"""
    room_id = data['room_id']
    
    if room_id not in lobbies:
        await websocket.send_json({'type': 'join_error', 'message': 'Лобби не найдено'})
        return
    
    lobby = lobbies[room_id]
    
    # Проверка пароля
    if lobby['is_private'] and lobby['password'] != data.get('password'):
        await websocket.send_json({'type': 'join_error', 'message': 'Неверный пароль'})
        return
    
    # Проверка количества игроков
    if len(lobby['players']) >= lobby['max_players']:
        await websocket.send_json({'type': 'join_error', 'message': 'Лобби полное'})
        return
    
    # Проверка, не началась ли игра
    if lobby['game_started']:
        await websocket.send_json({'type': 'join_error', 'message': 'Игра уже началась'})
        return
    
    # Добавляем игрока
    player = {
        'id': client_id,
        'name': data['player_name'],
        'is_host': False,
        'score': 0
    }
    lobby['players'].append(player)
    
    # Уведомляем всех в комнате
    await broadcast_to_room(room_id, {
        'type': 'player_joined',
        'player_name': data['player_name'],
        'players': lobby['players']
    })
    
    # Отправляем подтверждение
    await websocket.send_json({
        'type': 'join_success',
        'room_id': room_id,
        'players': lobby['players'],
        'settings': {
            'max_players': lobby['max_players'],
            'dice_count': lobby['dice_count'],
            'max_score': lobby['max_score']
        }
    })

async def handle_start_game(room_id: str):
    """Начать игру"""
    if room_id not in lobbies:
        return
    
    lobby = lobbies[room_id]
    
    if len(lobby['players']) < 2:
        return
    
    lobby['game_started'] = True
    
    # Уведомляем всех игроков
    await broadcast_to_room(room_id, {
        'type': 'game_starting',
        'room_id': room_id,
        'players': lobby['players'],
        'settings': {
            'dice_count': lobby['dice_count'],
            'max_score': lobby['max_score']
        }
    })

async def handle_roll_dice(room_id: str, client_id: str):
    """Бросить кости"""
    if room_id not in lobbies:
        return
    
    lobby = lobbies[room_id]
    dice_count = lobby['dice_count']
    
    # Проверяем, чей сейчас ход
    current_player = lobby['players'][lobby['current_turn']]
    if current_player['id'] != client_id:
        return
    
    # Генерируем результаты бросков
    dice_results = [random.randint(1, 6) for _ in range(dice_count)]
    total = sum(dice_results)
    
    # Обновляем счет
    current_player['score'] += total
    
    # Отправляем результаты
    await broadcast_to_room(room_id, {
        'type': 'dice_rolled',
        'player_name': current_player['name'],
        'dice_results': dice_results,
        'total': total,
        'new_score': current_player['score'],
        'players': lobby['players']
    })
    
    # Проверяем победителя
    if current_player['score'] >= lobby['max_score']:
        await broadcast_to_room(room_id, {
            'type': 'game_over',
            'winner': current_player['name'],
            'final_scores': lobby['players']
        })
        
        # Сбрасываем игру
        lobby['game_started'] = False
        for player in lobby['players']:
            player['score'] = 0
        lobby['current_turn'] = 0
    else:
        # Переход хода
        lobby['current_turn'] = (lobby['current_turn'] + 1) % len(lobby['players'])
        
        await broadcast_to_room(room_id, {
            'type': 'turn_changed',
            'current_player': lobby['players'][lobby['current_turn']]['name'],
            'player_index': lobby['current_turn']
        })

async def handle_leave_lobby(client_id: str, room_id: str = None):
    """Покинуть лобби"""
    if not room_id:
        # Ищем комнату игрока
        for rid, lobby in lobbies.items():
            for player in lobby['players']:
                if player['id'] == client_id:
                    room_id = rid
                    break
    
    if not room_id or room_id not in lobbies:
        return
    
    lobby = lobbies[room_id]
    
    # Находим и удаляем игрока
    player_name = None
    for player in lobby['players']:
        if player['id'] == client_id:
            player_name = player['name']
            lobby['players'].remove(player)
            break
    
    if not player_name:
        return
    
    # Если хост покинул или комната пустая
    if lobby['host_id'] == client_id or len(lobby['players']) == 0:
        await broadcast_to_room(room_id, {
            'type': 'lobby_closed',
            'message': 'Хост покинул лобби'
        })
        del lobbies[room_id]
        await broadcast_all({
            'type': 'lobby_deleted',
            'room_id': room_id
        })
    else:
        # Назначаем нового хоста
        if len(lobby['players']) > 0:
            lobby['host_id'] = lobby['players'][0]['id']
            lobby['players'][0]['is_host'] = True
        
        await broadcast_to_room(room_id, {
            'type': 'player_left',
            'player_name': player_name,
            'players': lobby['players']
        })

async def handle_disconnect(client_id: str):
    """Обработка отключения"""
    await handle_leave_lobby(client_id)

async def broadcast_to_room(room_id: str, message: dict):
    """Отправить сообщение всем в комнате"""
    if room_id not in lobbies:
        return
    
    lobby = lobbies[room_id]
    for player in lobby['players']:
        if player['id'] in connections:
            try:
                await connections[player['id']].send_json(message)
            except:
                pass

async def broadcast_all(message: dict):
    """Отправить сообщение всем подключенным"""
    for client_id, ws in connections.items():
        try:
            await ws.send_json(message)
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    # Запуск на всех интерфейсах для доступа по WiFi
    uvicorn.run(app, host="0.0.0.0", port=8100)
