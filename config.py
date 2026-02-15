import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    SEP_PASSWORD = os.getenv('SEP_PASSWORD', '')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    # Available Gemini models
    GEMINI_MODELS = {
        'gemini-3-flash-preview': {
            'name': 'Gemini 3 Flash',
            'description': 'room here to add other models, if needed'
        }
    }
    DEFAULT_MODEL = 'gemini-3-flash-preview'
