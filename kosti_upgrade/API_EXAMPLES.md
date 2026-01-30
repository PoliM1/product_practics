# 🔌 API Примеры и Документация

## HTTP API

### 1. Создание Лобби

**Endpoint:** `POST /create_lobby`

**Параметры формы:**
- `lobby_type` (string): "open" или "private"
- `max_players` (integer): 2-5

**Пример запроса (JavaScript):**
```javascript
const formData = new FormData();
formData.append('lobby_type', 'private');
formData.append('max_players', '3');

const response = await fetch('/create_lobby', {
    method: 'POST',
    body: formData
});

const data = await response.json();
console.log(data);
```

**Успешный ответ:**
```json
{
    "success": true,
    "lobby_id": "a1b2c3d4e5f6g7h8",
    "password": "AB12CD",
    "redirect_url": "/game_settings/a1b2c3d4e5f6g7h8"
}
```

**Ответ с ошибкой:**
```json
{
    "error": "Количество игроков должно быть от 2 до 5"
}
```

---

### 2. Присоединение к Открытому Лобби

**Endpoint:** `GET /join_lobby/<lobby_id>`

**Пример запроса:**
```javascript
window.location.href = `/join_lobby/${lobbyId}`;
```

**Результат:** Редирект на `/game_settings/<lobby_id>`

---

### 3. Присоединение к Закрытому Лобби

**Endpoint:** `POST /join_lobby/<lobby_id>`

**Параметры формы:**
- `password` (string): пароль лобби

**Пример HTML формы:**
```html
<form method="POST" action="/join_lobby/{{ lobby_id }}">
    <input type="text" name="password" required>
    <button type="submit">Войти</button>
</form>
```

**Успешный результат:** Редирект на `/game_settings/<lobby_id>`
**Неудача:** Возврат на форму с ошибкой

---

### 4. Обновление Настроек Игры

**Endpoint:** `POST /update_settings/<lobby_id>`

**Параметры формы:**
- `dice_count` (integer): 1-10
- `win_score` (integer): 10-1000

**Пример запроса:**
```javascript
const formData = new FormData();
formData.append('dice_count', '6');
formData.append('win_score', '150');

const response = await fetch(`/update_settings/${lobbyId}`, {
    method: 'POST',
    body: formData
});

const data = await response.json();
```

**Успешный ответ:**
```json
{
    "success": true
}
```

**Примечание:** Только хост может обновлять настройки

---

### 5. Начало Игры

**Endpoint:** `POST /start_game/<lobby_id>`

**Требования:**
- Минимум 2 игрока в лобби
- Запрос от хоста

**Пример запроса:**
```javascript
const response = await fetch(`/start_game/${lobbyId}`, {
    method: 'POST'
});

const data = await response.json();

if (data.success) {
    window.location.href = data.redirect_url;
}
```

**Успешный ответ:**
```json
{
    "success": true,
    "redirect_url": "/game/a1b2c3d4e5f6g7h8"
}
```

---

### 6. Выход из Лобби

**Endpoint:** `POST /leave_lobby/<lobby_id>`

**Пример запроса:**
```javascript
await fetch(`/leave_lobby/${lobbyId}`, {
    method: 'POST'
});

window.location.href = '/lobby';
```

**Поведение:**
- Удаляет игрока из лобби
- Если лобби пустое - удаляет лобби
- Если вышел хост - назначает нового хоста

---

## WebSocket API

### Подключение

```javascript
// Подключение к Socket.IO
const socket = io();

// Присоединение к комнате лобби
socket.emit('join', { lobby_id: lobbyId });
```

---

### События от Клиента

#### 1. join
Присоединение к комнате лобби

**Отправка:**
```javascript
socket.emit('join', {
    lobby_id: 'a1b2c3d4e5f6g7h8'
});
```

---

#### 2. leave
Выход из комнаты

**Отправка:**
```javascript
socket.emit('leave', {
    lobby_id: 'a1b2c3d4e5f6g7h8'
});
```

---

### События от Сервера

#### 1. player_joined
Новый игрок присоединился

**Получение:**
```javascript
socket.on('player_joined', (data) => {
    console.log('Новый игрок!');
    console.log('Игроки:', data.players);
    console.log('Всего:', data.player_count);
    
    // Обновить UI
    updatePlayersList(data.players);
});
```

**Данные:**
```json
{
    "players": ["user1", "user2", "user3"],
    "player_count": 3
}
```

---

#### 2. player_left
Игрок вышел из лобби

**Получение:**
```javascript
socket.on('player_left', (data) => {
    console.log('Игрок вышел');
    updatePlayersList(data.players);
});
```

**Данные:**
```json
{
    "players": ["user1", "user2"],
    "player_count": 2
}
```

---

#### 3. settings_updated
Настройки игры обновлены

**Получение:**
```javascript
socket.on('settings_updated', (data) => {
    console.log('Новые настройки:', data);
    
    // Обновить отображение
    document.getElementById('diceCount').textContent = data.dice_count;
    document.getElementById('winScore').textContent = data.win_score;
});
```

**Данные:**
```json
{
    "dice_count": 6,
    "win_score": 150
}
```

---

#### 4. game_started
Игра началась

**Получение:**
```javascript
socket.on('game_started', (data) => {
    console.log('Игра началась!');
    window.location.href = data.redirect_url;
});
```

**Данные:**
```json
{
    "redirect_url": "/game/a1b2c3d4e5f6g7h8"
}
```

---

#### 5. new_host
Назначен новый хост

**Получение:**
```javascript
socket.on('new_host', (data) => {
    console.log('Новый хост:', data.new_host);
    
    const currentUserId = getCurrentUserId();
    if (data.new_host === currentUserId) {
        // Показать элементы управления хоста
        showHostControls();
    }
});
```

**Данные:**
```json
{
    "new_host": "user2"
}
```

---

## Примеры Полной Интеграции

### Пример 1: Создание и Присоединение

```javascript
// Создание лобби
async function createLobby() {
    const formData = new FormData();
    formData.append('lobby_type', 'private');
    formData.append('max_players', '4');
    
    const response = await fetch('/create_lobby', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    
    if (data.success) {
        // Показать пароль пользователю
        showPassword(data.password);
        
        // Перейти к настройкам
        setTimeout(() => {
            window.location.href = data.redirect_url;
        }, 3000);
    }
}

// Присоединение к лобби
async function joinLobby(lobbyId, password) {
    const formData = new FormData();
    formData.append('password', password);
    
    const response = await fetch(`/join_lobby/${lobbyId}`, {
        method: 'POST',
        body: formData
    });
    
    // Редирект произойдет автоматически
}
```

---

### Пример 2: Управление Настройками

```javascript
// Только для хоста
class GameSettings {
    constructor(lobbyId) {
        this.lobbyId = lobbyId;
        this.socket = io();
        this.initializeSocketListeners();
    }
    
    initializeSocketListeners() {
        // Слушаем обновления
        this.socket.on('settings_updated', (data) => {
            this.updateDisplay(data);
        });
        
        // Присоединяемся к комнате
        this.socket.emit('join', { lobby_id: this.lobbyId });
    }
    
    async updateSettings(diceCount, winScore) {
        const formData = new FormData();
        formData.append('dice_count', diceCount);
        formData.append('win_score', winScore);
        
        const response = await fetch(`/update_settings/${this.lobbyId}`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            this.showNotification('Настройки сохранены');
        }
    }
    
    updateDisplay(data) {
        document.getElementById('diceCount').textContent = data.dice_count;
        document.getElementById('winScore').textContent = data.win_score;
    }
    
    showNotification(message) {
        // Показать уведомление
        console.log(message);
    }
}

// Использование
const settings = new GameSettings('a1b2c3d4e5f6g7h8');

// Когда хост меняет настройки
document.getElementById('settingsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const diceCount = document.getElementById('dice_count').value;
    const winScore = document.getElementById('win_score').value;
    
    await settings.updateSettings(diceCount, winScore);
});
```

---

### Пример 3: Отслеживание Игроков

```javascript
class PlayerManager {
    constructor(lobbyId, maxPlayers) {
        this.lobbyId = lobbyId;
        this.maxPlayers = maxPlayers;
        this.players = [];
        this.socket = io();
        this.initializeSocket();
    }
    
    initializeSocket() {
        this.socket.emit('join', { lobby_id: this.lobbyId });
        
        this.socket.on('player_joined', (data) => {
            this.players = data.players;
            this.updateUI();
            this.checkCanStart();
        });
        
        this.socket.on('player_left', (data) => {
            this.players = data.players;
            this.updateUI();
            this.checkCanStart();
        });
    }
    
    updateUI() {
        const container = document.getElementById('playersList');
        container.innerHTML = '';
        
        this.players.forEach((player, index) => {
            const div = document.createElement('div');
            div.className = 'player-item';
            div.innerHTML = `
                <span class="player-icon">👤</span>
                <span class="player-name">Игрок ${index + 1}</span>
            `;
            container.appendChild(div);
        });
        
        document.getElementById('playerCount').textContent = 
            `${this.players.length}/${this.maxPlayers}`;
    }
    
    checkCanStart() {
        const startBtn = document.getElementById('startGameBtn');
        if (this.players.length >= 2) {
            startBtn.disabled = false;
            startBtn.classList.add('ready');
        } else {
            startBtn.disabled = true;
            startBtn.classList.remove('ready');
        }
    }
}

// Использование
const playerManager = new PlayerManager('a1b2c3d4e5f6g7h8', 4);
```

---

### Пример 4: Начало Игры

```javascript
class GameStarter {
    constructor(lobbyId, isHost) {
        this.lobbyId = lobbyId;
        this.isHost = isHost;
        this.socket = io();
        this.initializeSocket();
    }
    
    initializeSocket() {
        this.socket.emit('join', { lobby_id: this.lobbyId });
        
        this.socket.on('game_started', (data) => {
            this.redirectToGame(data.redirect_url);
        });
    }
    
    async startGame() {
        if (!this.isHost) {
            console.error('Только хост может начать игру');
            return;
        }
        
        try {
            const response = await fetch(`/start_game/${this.lobbyId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Редирект произойдет через WebSocket событие
                console.log('Игра начинается...');
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Ошибка при начале игры:', error);
        }
    }
    
    redirectToGame(url) {
        // Показать экран загрузки
        showLoadingScreen();
        
        // Редирект через небольшую задержку
        setTimeout(() => {
            window.location.href = url;
        }, 500);
    }
}

// Использование
const gameStarter = new GameStarter('a1b2c3d4e5f6g7h8', true);

document.getElementById('startGameBtn').addEventListener('click', () => {
    gameStarter.startGame();
});
```

---

## Тестирование API

### Используя curl

```bash
# Создание лобби
curl -X POST http://localhost:5000/create_lobby \
  -F "lobby_type=private" \
  -F "max_players=3"

# Обновление настроек
curl -X POST http://localhost:5000/update_settings/LOBBY_ID \
  -F "dice_count=7" \
  -F "win_score=200" \
  -b cookies.txt

# Начало игры
curl -X POST http://localhost:5000/start_game/LOBBY_ID \
  -b cookies.txt
```

### Используя Postman

1. Создайте новый Request
2. Выберите метод POST
3. URL: `http://localhost:5000/create_lobby`
4. Body → form-data:
   - `lobby_type`: private
   - `max_players`: 3
5. Send

---

## Обработка Ошибок

### Пример обработки ошибок

```javascript
async function apiCall(url, options) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showErrorNotification(error.message);
        return null;
    }
}

// Использование
const result = await apiCall('/create_lobby', {
    method: 'POST',
    body: formData
});

if (result && result.success) {
    // Успех
}
```

---

## Лимиты и Ограничения

- **Максимум лобби:** 100 одновременных лобби (настраивается в config.py)
- **Таймаут лобби:** 1 час (настраивается в config.py)
- **Длина пароля:** 6 символов
- **Игроков в лобби:** 2-5
- **Количество костей:** 1-10
- **Очки победы:** 10-1000

---

**Примечание:** Все примеры предполагают наличие активной сессии Flask. Убедитесь что cookies включены в браузере.
