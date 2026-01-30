"""
Файл конфигурации приложения
"""

import os

class Config:
    """Базовая конфигурация"""
    # Секретный ключ для Flask сессий
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Настройки Flask-SocketIO
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_PING_INTERVAL = 25
    
    # Настройки лобби
    MAX_LOBBIES = 100  # Максимальное количество одновременных лобби
    LOBBY_TIMEOUT = 3600  # Время жизни лобби в секундах (1 час)
    PASSWORD_LENGTH = 6  # Длина пароля для закрытых лобби
    
    # Настройки игры
    MIN_PLAYERS = 2
    MAX_PLAYERS = 5
    MIN_DICE = 1
    MAX_DICE = 10
    MIN_WIN_SCORE = 10
    MAX_WIN_SCORE = 1000
    DEFAULT_DICE_COUNT = 5
    DEFAULT_WIN_SCORE = 100

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    TESTING = False
    # В продакшене обязательно установите SECRET_KEY через переменную окружения
    SECRET_KEY = os.environ.get('SECRET_KEY')

class TestingConfig(Config):
    """Конфигурация для тестирования"""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False

# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Получить конфигурацию по имени"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    return config.get(config_name, config['default'])
