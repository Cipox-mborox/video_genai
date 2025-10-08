import os
from dotenv import load_dotenv

if os.path.exists('.env'):
    load_dotenv()

class Config:
    # Telegram Bot
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    
    # Google AI Studio (Gemini API)
    GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')
    
    # Fallback APIs
    STABILITY_API_KEY = os.getenv('STABILITY_API_KEY', '')
    LUMA_API_KEY = os.getenv('LUMA_API_KEY', '')
    
    # Bot Settings
    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_VIDEO_DURATION = 10
    REQUEST_TIMEOUT = 180
    
    # Supported Formats
    SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/jpg']
    
    @classmethod
    def validate_config(cls):
        required = ['TELEGRAM_TOKEN', 'GOOGLE_AI_API_KEY']
        missing = [var for var in required if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing required config: {missing}")
        
        return True