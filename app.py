"""
DriveMind WhatsApp Bot
Flask webhook handler for Twilio WhatsApp integration
"""
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import traceback

from config import Config
from firebase_service import FirebaseService
from llm_service import LLMService
from keyword_detector import KeywordDetector
from models import Message

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize services
firebase_service = FirebaseService()
llm_service = LLMService(
    claude_api_key=Config.CLAUDE_API_KEY,
    openai_api_key=Config.OPENAI_API_KEY,
    provider=Config.LLM_PROVIDER
)

# Store user preferences (model selection)
user_models = {}  # phone_number -> "haiku" or "sonnet"


@app.route('/')
def home():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "DriveMind WhatsApp Bot",
        "provider": Config.LLM_PROVIDER
    }


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Twilio WhatsApp webhook handler
    Receives incoming messages and responds with LLM-generated answers
    """
    try:
        # Get incoming message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')

        print(f"\n[Webhook] Received message from {from_number}: {incoming_msg}")

        # Create Twilio response
        resp = MessagingResponse()

        # Handle empty messages
        if not incoming_msg:
            resp.message("Please send a message to chat with DriveMind.")
            return str(resp)

        # Check for special commands
        lower_msg = incoming_msg.lower()

        # Command: Start new conversation
        if Config.ENABLE_NEW_CONVERSATION_COMMAND and lower_msg in ['new conversation', 'new', 'reset', 'start over']:
            conversation = firebase_service.start_new_conversation(from_number)
            print(f"[Webhook] Started new conversation: {conversation.id}")
            resp.message("Started a new conversation. What would you like to talk about?")
            return str(resp)

        # Get or create conversation
        conversation = firebase_service.get_or_create_active_conversation(from_number)
        print(f"[Webhook] Using conversation: {conversation.id}")

        # Get user's current model preference
        current_model = user_models.get(from_number, "haiku")

        # Process message with keyword detection
        processed = KeywordDetector.process_message(incoming_msg, current_model)

        print(f"[Webhook] Model: {processed.model}, Triggered Sonnet: {processed.triggered_sonnet}")
        print(f"[Webhook] Cleaned message: {processed.cleaned_message}")

        # Update user's model preference if Sonnet was triggered
        if processed.triggered_sonnet:
            user_models[from_number] = "sonnet"
            print(f"[Webhook] Switched to Sonnet model for user")

        # Build message history for LLM
        llm_messages = []
        for msg in conversation.messages[-10:]:  # Last 10 messages for context
            llm_messages.append(msg)

        # Add current user message
        user_message = Message(
            content=processed.cleaned_message,
            role="user",
            timestamp=datetime.now()
        )
        llm_messages.append(user_message)

        # Save user message to Firebase immediately
        firebase_service.add_message(conversation.id, user_message)

        # Call LLM with error handling
        try:
            print(f"[Webhook] Calling {Config.LLM_PROVIDER} with {processed.model} model...")
            response_text, input_tokens, output_tokens = llm_service.send_message(
                messages=llm_messages,
                model=processed.model
            )

            print(f"[Webhook] Got response ({len(response_text)} chars)")

            # Create assistant message
            assistant_message = Message(
                content=response_text,
                role="assistant",
                timestamp=datetime.now(),
                model=processed.model,
                tokens=input_tokens + output_tokens
            )

            # Save assistant message to Firebase
            firebase_service.add_message(conversation.id, assistant_message)

            # Update token count
            total_tokens = conversation.token_count + input_tokens + output_tokens
            firebase_service.update_token_count(conversation.id, total_tokens)

            print(f"[Webhook] Saved to Firebase. Total tokens: {total_tokens}")

            # Send response back to WhatsApp
            resp.message(response_text)

            # If model switched to Sonnet, add a note (optional)
            if processed.triggered_sonnet and not processed.was_modified:
                # User explicitly asked for deep thinking
                print(f"[Webhook] Used Sonnet model for deeper analysis")

            return str(resp)

        except Exception as llm_error:
            # Log LLM error details
            error_type = type(llm_error).__name__
            error_msg = str(llm_error)

            print(f"[Webhook] LLM ERROR ({error_type}): {error_msg}")
            print(traceback.format_exc())

            # Save error to Firebase as an assistant message
            error_message = Message(
                content=f"[ERROR: {error_type}] {error_msg}",
                role="assistant",
                timestamp=datetime.now(),
                model=processed.model,
                tokens=0
            )
            firebase_service.add_message(conversation.id, error_message)

            # Send user-friendly error message
            user_error_msg = "Sorry, I encountered an error communicating with the AI service. "

            if "timeout" in error_msg.lower():
                user_error_msg += "The request timed out. Please try again with a shorter message."
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                user_error_msg += "There was a network connectivity issue. Please try again."
            elif "rate" in error_msg.lower() or "429" in error_msg:
                user_error_msg += "The service is temporarily busy. Please wait a moment and try again."
            elif "401" in error_msg or "authentication" in error_msg.lower():
                user_error_msg += "API authentication failed. Please contact support."
            else:
                user_error_msg += "Please try again."

            resp.message(user_error_msg)
            return str(resp)

    except Exception as e:
        print(f"[Webhook] GENERAL ERROR: {str(e)}")
        print(traceback.format_exc())

        # Try to save error to Firebase if we have a conversation
        try:
            if 'conversation' in locals():
                error_message = Message(
                    content=f"[SYSTEM ERROR: {type(e).__name__}] {str(e)}",
                    role="assistant",
                    timestamp=datetime.now(),
                    model="system",
                    tokens=0
                )
                firebase_service.add_message(conversation.id, error_message)
        except:
            pass  # If Firebase save fails, just log to console

        # Send error message to user
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an unexpected error. Please try again.")
        return str(resp)


@app.route('/health', methods=['GET'])
def health():
    """Health check for monitoring"""
    try:
        # Test Firebase connection
        firebase_ok = firebase_service.db is not None

        # Test LLM connection (optional, can be slow)
        # llm_ok = llm_service.test_connection()

        return {
            "status": "healthy",
            "firebase": "connected" if firebase_ok else "disconnected",
            "llm_provider": Config.LLM_PROVIDER
        }, 200
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("DriveMind WhatsApp Bot Starting...")
    print(f"LLM Provider: {Config.LLM_PROVIDER}")
    print(f"Twilio Number: {Config.TWILIO_WHATSAPP_NUMBER}")
    print(f"Port: {Config.PORT}")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=Config.PORT,
        debug=Config.FLASK_DEBUG
    )
