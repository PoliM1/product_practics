from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets
import string
from datetime import datetime
from config import get_config

# Инициализация приложения
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Инициализация SocketIO
socketio = SocketIO(app, cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'])

# Хранилище лобби
lobbies = {}
# Структура лобби:
# {
#     'lobby_id': {
#         'host': 'user_id',
#         'password': 'xxxx' или None,
#         'type': 'open' или 'private',
#         'max_players': 2-5,
#         'players': ['user_id1', 'user_id2'],
#         'game_settings': {
#             'dice_count': 5,
#             'win_score': 100
#         },
#         'game_started': False,
#         'created_at': datetime
#     }
# }

def generate_password(length=None):
    """Генерация случайного пароля для закрытого лобби"""
    if length is None:
        length = app.config.get('PASSWORD_LENGTH', 6)
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_lobby_id():
    """Генерация уникального ID для лобби"""
    return secrets.token_hex(8)

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/lobby')
def lobby_page():
    """Страница выбора/создания лобби"""
    # Получаем список открытых лобби
    open_lobbies = []
    for lobby_id, lobby_data in lobbies.items():
        if lobby_data['type'] == 'open' and not lobby_data['game_started']:
            open_lobbies.append({
                'id': lobby_id,
                'host': lobby_data['host'],
                'current_players': len(lobby_data['players']),
                'max_players': lobby_data['max_players'],
                'created_at': lobby_data['created_at'].strftime('%H:%M:%S')
            })
    
    return render_template('lobby.html', open_lobbies=open_lobbies)

@app.route('/create_lobby', methods=['POST'])
def create_lobby():
    """Создание нового лобби"""
    lobby_type = request.form.get('lobby_type')  # 'open' или 'private'
    max_players = int(request.form.get('max_players', 2))
    
    # Валидация
    if max_players < 2 or max_players > 5:
        return jsonify({'error': 'Количество игроков должно быть от 2 до 5'}), 400
    
    # Создаем ID для лобби
    lobby_id = generate_lobby_id()
    
    # Генерируем пароль для закрытого лобби
    password = generate_password() if lobby_type == 'private' else None
    
    # Создаем уникальный ID для хоста
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(8)
    
    user_id = session['user_id']
    
    # Создаем лобби
    lobbies[lobby_id] = {
        'host': user_id,
        'password': password,
        'type': lobby_type,
        'max_players': max_players,
        'players': [user_id],
        'game_settings': {
            'dice_count': 5,
            'win_score': 100
        },
        'game_started': False,
        'created_at': datetime.now()
    }
    
    # Сохраняем ID лобби в сессии
    session['current_lobby'] = lobby_id
    
    return jsonify({
        'success': True,
        'lobby_id': lobby_id,
        'password': password,
        'redirect_url': url_for('game_settings', lobby_id=lobby_id)
    })

@app.route('/join_lobby/<lobby_id>', methods=['GET', 'POST'])
def join_lobby(lobby_id):
    """Присоединение к лобби"""
    if lobby_id not in lobbies:
        return "Лобби не найдено", 404
    
    lobby = lobbies[lobby_id]
    
    # Проверяем, не заполнено ли лобби
    if len(lobby['players']) >= lobby['max_players']:
        return "Лобби заполнено", 400
    
    # Если это закрытое лобби, проверяем пароль
    if lobby['type'] == 'private':
        if request.method == 'GET':
            return render_template('join_private.html', lobby_id=lobby_id)
        
        password = request.form.get('password')
        if password != lobby['password']:
            return render_template('join_private.html', 
                                 lobby_id=lobby_id, 
                                 error='Неверный пароль')
    
    # Создаем ID для игрока, если его нет
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(8)
    
    user_id = session['user_id']
    
    # Добавляем игрока в лобби
    if user_id not in lobby['players']:
        lobby['players'].append(user_id)
    
    session['current_lobby'] = lobby_id
    
    return redirect(url_for('game_settings', lobby_id=lobby_id))

@app.route('/game_settings/<lobby_id>')
def game_settings(lobby_id):
    """Страница настроек игры"""
    if lobby_id not in lobbies:
        return redirect(url_for('lobby_page'))
    
    lobby = lobbies[lobby_id]
    
    # Проверяем, что пользователь в лобби
    if 'user_id' not in session or session['user_id'] not in lobby['players']:
        return redirect(url_for('lobby_page'))
    
    is_host = session['user_id'] == lobby['host']
    
    return render_template('game_settings.html', 
                         lobby_id=lobby_id,
                         lobby=lobby,
                         is_host=is_host,
                         user_id=session['user_id'])

@app.route('/update_settings/<lobby_id>', methods=['POST'])
def update_settings(lobby_id):
    """Обновление настроек игры (только для хоста)"""
    if lobby_id not in lobbies:
        return jsonify({'error': 'Лобби не найдено'}), 404
    
    lobby = lobbies[lobby_id]
    
    # Проверяем, что это хост
    if 'user_id' not in session or session['user_id'] != lobby['host']:
        return jsonify({'error': 'Только хост может менять настройки'}), 403
    
    dice_count = int(request.form.get('dice_count', 5))
    win_score = int(request.form.get('win_score', 100))
    
    # Валидация
    if dice_count < 1 or dice_count > 10:
        return jsonify({'error': 'Количество костей должно быть от 1 до 10'}), 400
    
    if win_score < 10 or win_score > 1000:
        return jsonify({'error': 'Счет победы должен быть от 10 до 1000'}), 400
    
    lobby['game_settings']['dice_count'] = dice_count
    lobby['game_settings']['win_score'] = win_score
    
    # Уведомляем всех игроков в лобби через WebSocket
    socketio.emit('settings_updated', {
        'dice_count': dice_count,
        'win_score': win_score
    }, room=lobby_id)
    
    return jsonify({'success': True})

@app.route('/start_game/<lobby_id>', methods=['POST'])
def start_game(lobby_id):
    """Начало игры (только для хоста)"""
    if lobby_id not in lobbies:
        return jsonify({'error': 'Лобби не найдено'}), 404
    
    lobby = lobbies[lobby_id]
    
    # Проверяем, что это хост
    if 'user_id' not in session or session['user_id'] != lobby['host']:
        return jsonify({'error': 'Только хост может начать игру'}), 403
    
    # Проверяем, что есть минимум 2 игрока
    if len(lobby['players']) < 2:
        return jsonify({'error': 'Нужно минимум 2 игрока для начала игры'}), 400
    
    lobby['game_started'] = True
    
    # Уведомляем всех игроков
    socketio.emit('game_started', {
        'redirect_url': url_for('game', lobby_id=lobby_id)
    }, room=lobby_id)
    
    return jsonify({
        'success': True,
        'redirect_url': url_for('game', lobby_id=lobby_id)
    })

@app.route('/game/<lobby_id>')
def game(lobby_id):
    """Страница игры"""
    if lobby_id not in lobbies:
        return redirect(url_for('lobby_page'))
    
    lobby = lobbies[lobby_id]
    
    if not lobby['game_started']:
        return redirect(url_for('game_settings', lobby_id=lobby_id))
    
    return render_template('game.html', 
                         lobby_id=lobby_id,
                         lobby=lobby,
                         user_id=session.get('user_id'))

@app.route('/leave_lobby/<lobby_id>', methods=['POST'])
def leave_lobby(lobby_id):
    """Выход из лобби"""
    if lobby_id not in lobbies:
        return jsonify({'error': 'Лобби не найдено'}), 404
    
    lobby = lobbies[lobby_id]
    user_id = session.get('user_id')
    
    if user_id in lobby['players']:
        lobby['players'].remove(user_id)
        
        # Если лобби пустое, удаляем его
        if len(lobby['players']) == 0:
            del lobbies[lobby_id]
        # Если вышел хост, назначаем нового хоста
        elif user_id == lobby['host'] and len(lobby['players']) > 0:
            lobby['host'] = lobby['players'][0]
            socketio.emit('new_host', {'new_host': lobby['host']}, room=lobby_id)
    
    if 'current_lobby' in session:
        session.pop('current_lobby')
    
    return jsonify({'success': True})

# WebSocket события
@socketio.on('join')
def on_join(data):
    """Присоединение к комнате WebSocket"""
    lobby_id = data.get('lobby_id')
    if lobby_id in lobbies:
        join_room(lobby_id)
        # Отправляем обновленный список игроков
        emit('player_joined', {
            'players': lobbies[lobby_id]['players'],
            'player_count': len(lobbies[lobby_id]['players'])
        }, room=lobby_id)

@socketio.on('leave')
def on_leave(data):
    """Выход из комнаты WebSocket"""
    lobby_id = data.get('lobby_id')
    if lobby_id in lobbies:
        leave_room(lobby_id)
        emit('player_left', {
            'players': lobbies[lobby_id]['players'],
            'player_count': len(lobbies[lobby_id]['players'])
        }, room=lobby_id)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
