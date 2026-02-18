#!/usr/bin/env python3
"""
Простой HTTP сервер для игры в кости с WebSocket поддержкой
Запуск: python3 simple_server.py
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import random
import threading
import socket
from urllib.parse import parse_qs, urlparse

lobbies = {}

class DiceGameHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open('templates/index.html', 'rb') as f:
                self.wfile.write(f.read())
        
        elif self.path == '/roll':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            dice = random.randint(1, 6)
            self.wfile.write(json.dumps({"dice": dice}).encode())
        
        elif self.path == '/lobbies':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
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
            self.wfile.write(json.dumps({"lobbies": public_lobbies}).encode())
        
        elif self.path.startswith('/lobby-status/'):
            # Получаем статус конкретного лобби
            lobby_id = self.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if lobby_id in lobbies:
                self.wfile.write(json.dumps({
                    "success": True,
                    "lobby": lobbies[lobby_id]
                }).encode())
            else:
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби не найдено"
                }).encode())
        
        elif self.path.startswith('/game-state/'):
            # Получаем состояние игры
            lobby_id = self.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if lobby_id in lobbies:
                self.wfile.write(json.dumps({
                    "success": True,
                    "lobby": lobbies[lobby_id]
                }).encode())
            else:
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби не найдено"
                }).encode())
        
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/create-lobby':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            import uuid
            from datetime import datetime
            
            lobby_id = str(uuid.uuid4())[:8]
            player_id = str(uuid.uuid4())[:8]  # ID для хоста
            
            lobbies[lobby_id] = {
                "id": lobby_id,
                "host": data.get("host_name", "Игрок"),
                "host_id": player_id,
                "max_players": data.get("max_players", 2),
                "dice_count": data.get("dice_count", 1),
                "win_score": data.get("win_score", 1),
                "is_private": data.get("is_private", False),
                "password": data.get("password", ""),
                "players": [{
                    "id": player_id,
                    "name": data.get("host_name", "Игрок"),
                    "is_host": True
                }],
                "created_at": datetime.now().isoformat(),
                "status": "waiting",
                "game_state": {
                    "current_round": 0,
                    "player_scores": {player_id: 0},
                    "current_rolls": {},
                    "players_rolled": []
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "lobby_id": lobby_id,
                "player_id": player_id,
                "lobby": lobbies[lobby_id]
            }).encode())
        
        elif self.path == '/join-lobby':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            lobby_id = data.get("lobby_id")
            player_name = data.get("player_name", "Игрок")
            password = data.get("password", "")
            
            if lobby_id not in lobbies:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби не найдено"
                }).encode())
                return
            
            lobby = lobbies[lobby_id]
            
            if lobby["is_private"] and lobby["password"] != password:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Неверный пароль"
                }).encode())
                return
            
            if len(lobby["players"]) >= lobby["max_players"]:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби заполнено"
                }).encode())
                return
            
            import uuid
            from datetime import datetime
            
            player_id = str(uuid.uuid4())[:8]
            player = {
                "id": player_id,
                "name": player_name,
                "joined_at": datetime.now().isoformat()
            }
            
            lobby["players"].append(player)
            lobby["game_state"]["player_scores"][player_id] = 0
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "player_id": player_id,
                "lobby": lobby
            }).encode())
        
        elif self.path == '/start-game':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            lobby_id = data.get("lobby_id")
            
            if lobby_id not in lobbies:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби не найдено"
                }).encode())
                return
            
            # Меняем статус лобби на "playing"
            lobbies[lobby_id]["status"] = "playing"
            
            # Инициализируем game_state если нужно
            if "game_state" not in lobbies[lobby_id]:
                lobbies[lobby_id]["game_state"] = {
                    "current_round": 0,
                    "player_scores": {},
                    "current_rolls": {},
                    "players_rolled": [],
                    "round_winner": None,
                    "game_winner": None,
                    "round_complete": False
                }
            
            # Инициализируем очки для всех игроков
            for player in lobbies[lobby_id]["players"]:
                if player["id"] not in lobbies[lobby_id]["game_state"]["player_scores"]:
                    lobbies[lobby_id]["game_state"]["player_scores"][player["id"]] = 0
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "lobby": lobbies[lobby_id]
            }).encode())
        
        elif self.path == '/roll-dice':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            lobby_id = data.get("lobby_id")
            player_id = data.get("player_id")
            
            if lobby_id not in lobbies:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби не найдено"
                }).encode())
                return
            
            lobby = lobbies[lobby_id]
            dice_count = lobby["dice_count"]
            
            # Бросаем кости
            rolls = [random.randint(1, 6) for _ in range(dice_count)]
            total = sum(rolls)
            
            # Сохраняем результат
            if "current_rolls" not in lobby["game_state"]:
                lobby["game_state"]["current_rolls"] = {}
            
            lobby["game_state"]["current_rolls"][player_id] = {
                "rolls": rolls,
                "total": total
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "rolls": rolls,
                "total": total
            }).encode())
        
        elif self.path == '/complete-round':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            lobby_id = data.get("lobby_id")
            
            if lobby_id not in lobbies:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби не найдено"
                }).encode())
                return
            
            lobby = lobbies[lobby_id]
            current_rolls = lobby["game_state"].get("current_rolls", {})
            
            if not current_rolls:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Нет бросков"
                }).encode())
                return
            
            # Определяем победителя раунда (максимальная сумма)
            winner_id = max(current_rolls.keys(), key=lambda k: current_rolls[k]["total"])
            winner_total = current_rolls[winner_id]["total"]
            
            # Добавляем сумму костей к общему счёту победителя
            if winner_id in lobby["game_state"]["player_scores"]:
                lobby["game_state"]["player_scores"][winner_id] += winner_total
            else:
                lobby["game_state"]["player_scores"][winner_id] = winner_total
            
            # Сохраняем победителя раунда
            lobby["game_state"]["round_winner"] = winner_id
            lobby["game_state"]["round_complete"] = True
            
            # Проверяем победителя игры (кто первым набрал нужное количество очков)
            win_score = lobby["win_score"]
            game_winner = None
            for pid, score in lobby["game_state"]["player_scores"].items():
                if score >= win_score:
                    game_winner = pid
                    break
            
            if game_winner:
                lobby["game_state"]["game_winner"] = game_winner
                lobby["status"] = "finished"
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "lobby": lobby
            }).encode())
        
        elif self.path == '/next-round':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            lobby_id = data.get("lobby_id")
            
            if lobby_id not in lobbies:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Лобби не найдено"
                }).encode())
                return
            
            lobby = lobbies[lobby_id]
            
            # Сбрасываем раунд
            lobby["game_state"]["current_rolls"] = {}
            lobby["game_state"]["round_winner"] = None
            lobby["game_state"]["round_complete"] = False
            lobby["game_state"]["current_round"] += 1
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "lobby": lobby
            }).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def get_ip():
    """Получить локальный IP адрес"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    PORT = 8000
    local_ip = get_ip()
    
    server = HTTPServer(('0.0.0.0', PORT), DiceGameHandler)
    
    print('=' * 60)
    print('🎲 СЕРВЕР ИГРЫ В КОСТИ ЗАПУЩЕН!')
    print('=' * 60)
    print(f'\n📍 Локальный доступ:')
    print(f'   http://localhost:{PORT}')
    print(f'   http://127.0.0.1:{PORT}')
    print(f'\n🌐 Доступ по сети:')
    print(f'   http://{local_ip}:{PORT}')
    print(f'\n💡 Другие устройства в вашей сети могут подключиться по адресу:')
    print(f'   http://{local_ip}:{PORT}')
    print(f'\n🛑 Для остановки сервера нажмите Ctrl+C')
    print('=' * 60)
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\n🛑 Сервер остановлен')
        server.shutdown()