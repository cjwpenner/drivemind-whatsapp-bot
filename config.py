"""
Configuration for WhatsApp Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings"""

    # Twilio credentials
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

    # LLM API keys
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

    # LLM Provider: "claude" or "openai"
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'claude')

    # Firebase credentials
    FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')

    # Flask settings
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))

    # Feature flags
    ENABLE_NEW_CONVERSATION_COMMAND = True  # Allow "new conversation" command
    ENABLE_MODEL_SWITCHING = True  # Allow model switching via keywords
