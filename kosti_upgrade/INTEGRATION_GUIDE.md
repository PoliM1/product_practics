# 📋 Инструкция по Интеграции Системы Лобби

## Обзор изменений

Эта система лобби добавляет следующие функции в ваш проект:

1. **Создание лобби** (открытых и закрытых)
2. **Присоединение к лобби** (с поддержкой паролей)
3. **Настройки игры** (кости, очки победы)
4. **Real-time обновления** через WebSocket
5. **Управление игроками** (хост, участники)

## Шаг 1: Резервное копирование

```bash
# Создайте резервную копию вашего проекта
cp -r Kosti-app Kosti-app-backup
```

## Шаг 2: Установка зависимостей

```bash
# Установите новые зависимости
pip install -r requirements.txt
```

Новые зависимости:
- `Flask-SocketIO` - для WebSocket соединений
- `python-socketio` - клиент/сервер Socket.IO
- `python-engineio` - транспортный уровень

## Шаг 3: Интеграция файлов

### 3.1 Замена main.py

**ВАЖНО:** Сохраните логику вашей игры из старого `main.py`

1. Откройте старый `main.py` и скопируйте код игровой логики
2. Замените `main.py` новым файлом
3. Добавьте вашу игровую логику в новый `main.py`

Пример интеграции игровой логики:

```python
# В новом main.py добавьте после route /game/<lobby_id>

@socketio.on('roll_dice')
def handle_roll_dice(data):
    """Обработка броска костей"""
    lobby_id = data.get('lobby_id')
    user_id = session.get('user_id')
    
    # ВАША ИГРОВАЯ ЛОГИКА ЗДЕСЬ
    # Например:
    dice_count = lobbies[lobby_id]['game_settings']['dice_count']
    results = [random.randint(1, 6) for _ in range(dice_count)]
    total = sum(results)
    
    # Отправка результата всем в комнате
    emit('dice_rolled', {
        'user_id': user_id,
        'results': results,
        'total': total
    }, room=lobby_id)
```

### 3.2 Шаблоны (templates/)

Скопируйте новые шаблоны:

```bash
cp -r templates/* ваш_проект/templates/
```

Файлы шаблонов:
- `base.html` - базовый шаблон (может быть объединен с вашим)
- `index.html` - главная страница
- `lobby.html` - страница лобби
- `join_private.html` - ввод пароля
- `game_settings.html` - настройки игры
- `game.html` - страница игры (интегрируйте вашу игровую логику)

### 3.3 Статические файлы (static/)

Скопируйте стили и скрипты:

```bash
cp -r static/* ваш_проект/static/
```

## Шаг 4: Настройка конфигурации

### 4.1 Создайте файл .env (опционально)

```bash
# .env
FLASK_ENV=development
SECRET_KEY=ваш-секретный-ключ-для-продакшена
```

### 4.2 Настройте config.py

Отредактируйте `config.py` под ваши нужды:

```python
class Config:
    # Настройки лобби
    MAX_LOBBIES = 100
    LOBBY_TIMEOUT = 3600
    PASSWORD_LENGTH = 6
    
    # Настройки игры (измените под вашу игру)
    MIN_PLAYERS = 2
    MAX_PLAYERS = 5
    MIN_DICE = 1
    MAX_DICE = 10
    MIN_WIN_SCORE = 10
    MAX_WIN_SCORE = 1000
```

## Шаг 5: Интеграция игровой логики

### 5.1 Обновите game.html

В файле `templates/game.html` замените базовую игровую логику на вашу:

```html
<!-- Ваш существующий HTML для игры -->
<div class="your-game-container">
    <!-- Игровое поле -->
</div>

<script>
// Подключение к WebSocket
const socket = io();
const lobbyId = '{{ lobby_id }}';

socket.emit('join', { lobby_id: lobbyId });

// ВАША ИГРОВАЯ ЛОГИКА
// Например:
document.getElementById('rollDiceBtn').addEventListener('click', () => {
    socket.emit('roll_dice', { lobby_id: lobbyId });
});

socket.on('dice_rolled', (data) => {
    // Обновить UI с результатами
    updateGameUI(data);
});
</script>
```

### 5.2 Добавьте WebSocket обработчики

В `main.py` добавьте обработчики для вашей игровой логики:

```python
@socketio.on('your_game_event')
def handle_game_event(data):
    lobby_id = data.get('lobby_id')
    # Обработка игрового события
    emit('response_event', {'result': 'data'}, room=lobby_id)
```

## Шаг 6: Тестирование

### 6.1 Локальное тестирование

```bash
# Запустите сервер
python main.py

# Откройте несколько вкладок браузера
# Вкладка 1: http://localhost:5000
# Вкладка 2: http://localhost:5000
```

### 6.2 Тест-кейсы

1. **Создание открытого лобби**
   - Создайте лобби
   - Присоединитесь из другой вкладки
   - Проверьте обновление списка игроков

2. **Создание закрытого лобби**
   - Создайте закрытое лобби
   - Скопируйте пароль
   - Присоединитесь используя пароль

3. **Настройки игры**
   - Измените количество костей
   - Измените очки победы
   - Проверьте обновление у второго игрока

4. **Начало игры**
   - Убедитесь, что кнопка "Начать игру" неактивна с 1 игроком
   - Добавьте второго игрока
   - Начните игру
   - Проверьте переход обоих игроков на игровую страницу

## Шаг 7: Кастомизация стилей

### 7.1 Цветовая схема

В `static/css/style.css` измените основные цвета:

```css
:root {
    --primary-color: #667eea;     /* Основной цвет */
    --secondary-color: #764ba2;   /* Вторичный цвет */
    --success-color: #4CAF50;     /* Цвет успеха */
    --danger-color: #f44336;      /* Цвет опасности */
}
```

### 7.2 Адаптация под вашу тему

Если у вас уже есть стили, объедините их:

```css
/* В вашем существующем style.css */
@import 'lobby-styles.css';  /* Импортируйте стили лобби отдельно */
```

## Шаг 8: Дополнительные функции

### 8.1 Добавление чата

```python
# В main.py
@socketio.on('send_message')
def handle_message(data):
    lobby_id = data.get('lobby_id')
    message = data.get('message')
    user_id = session.get('user_id')
    
    emit('new_message', {
        'user_id': user_id,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }, room=lobby_id)
```

### 8.2 Добавление статистики

```python
# Структура для отслеживания статистики
game_stats = {
    'user_id': {
        'games_played': 0,
        'games_won': 0,
        'total_score': 0
    }
}

@app.route('/stats/<user_id>')
def user_stats(user_id):
    stats = game_stats.get(user_id, {})
    return render_template('stats.html', stats=stats)
```

## Шаг 9: Продакшен

### 9.1 Используйте продакшен-сервер

```bash
# Установите gunicorn
pip install gunicorn eventlet

# Запустите с gunicorn
gunicorn --worker-class eventlet -w 1 main:app
```

### 9.2 Настройте переменные окружения

```bash
export FLASK_ENV=production
export SECRET_KEY=ваш-очень-секретный-ключ
```

### 9.3 Настройте NGINX (опционально)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Решение проблем

### Проблема: WebSocket не подключается

**Решение:**
```javascript
// В шаблонах, убедитесь что используете правильный путь
const socket = io({
    transports: ['websocket', 'polling']
});
```

### Проблема: Игроки не видят обновления

**Решение:**
```python
# Убедитесь что используете room в emit
emit('event_name', data, room=lobby_id)  # ✅ Правильно
emit('event_name', data)                  # ❌ Неправильно
```

### Проблема: Лобби пропадают

**Решение:** Лобби хранятся в памяти. Для постоянного хранения используйте базу данных:

```python
# Пример с SQLite
import sqlite3

def save_lobby(lobby_id, lobby_data):
    conn = sqlite3.connect('lobbies.db')
    # Сохранение в БД
    conn.close()
```

## Контрольный список интеграции

- [ ] Установлены все зависимости
- [ ] Скопированы все файлы
- [ ] Интегрирована игровая логика
- [ ] Настроен config.py
- [ ] Проведено локальное тестирование
- [ ] Протестированы все сценарии
- [ ] Кастомизированы стили
- [ ] Настроен продакшен (если нужно)

## Дополнительная помощь

Если возникли проблемы:

1. Проверьте консоль браузера на ошибки JavaScript
2. Проверьте логи Flask сервера
3. Убедитесь что все порты открыты
4. Проверьте что WebSocket соединение установлено

---

**Удачи с интеграцией! 🎲**
