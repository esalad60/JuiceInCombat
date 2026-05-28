import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'data.db')
    
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    
    SOCKETIO_ASYNC_MODE = 'eventlet'
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_PING_INTERVAL = 25