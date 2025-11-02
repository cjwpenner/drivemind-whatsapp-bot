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


def split_message(text: str, max_length: int) -> list:
    """
    Split long text into chunks at sentence boundaries
    Twilio WhatsApp has a 1600 character limit per message
    """
    import re

    # Leave room for part indicator "[Part X/Y]"
    chunk_size = max_length - 20

    chunks = []
    current_chunk = ""

    # Split by sentences (periods, question marks, exclamation points)
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        # If single sentence is too long, split by commas or spaces
        if len(sentence) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # Split long sentence by commas
            parts = sentence.split(', ')
            for part in parts:
                if len(current_chunk) + len(part) + 2 > chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = part + ', '
                else:
                    current_chunk += part + ', '
        elif len(current_chunk) + len(sentence) + 1 > chunk_size:
            # Adding this sentence would exceed limit
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
        else:
            # Add sentence to current chunk
            current_chunk += sentence + " "

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


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
    Twilio WhatsApp webhook handler - FAST QUEUE VERSION
    Immediately queues message to Firebase and returns, preventing timeout on cold starts
    """
    try:
        # Get incoming message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        message_sid = request.values.get('MessageSid', '')  # Unique message ID from Twilio

        print(f"\n[Webhook] Received message {message_sid} from {from_number}: {incoming_msg}")

        # Create Twilio response
        resp = MessagingResponse()

        # Handle empty messages
        if not incoming_msg:
            resp.message("Please send a message to chat with DriveMind.")
            return str(resp)

        # FAST PATH: Queue message and return immediately (prevents timeout)
        queued = firebase_service.enqueue_message(from_number, incoming_msg, message_sid)

        if queued:
            # Message queued successfully - acknowledge receipt
            # Empty response means no immediate reply (processing async)
            print(f"[Webhook] Message queued successfully, returning 200 OK")
            return str(resp)  # Return empty TwiML - we'll send response later
        else:
            # Fallback: If queueing fails, respond with error
            resp.message("Sorry, I'm having trouble processing messages right now. Please try again in a moment.")
            return str(resp)

    except Exception as e:
        print(f"[Webhook] ERROR: {str(e)}")
        print(traceback.format_exc())

        # Always return 200 OK to Twilio to prevent retries
        resp = MessagingResponse()
        return str(resp)


@app.route('/webhook-sync', methods=['POST'])
def webhook_sync():
    """
    Original synchronous webhook handler (kept as fallback)
    Process message immediately and respond
    """
    try:
        # Get incoming message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')

        print(f"\n[Webhook-Sync] Received message from {from_number}: {incoming_msg}")

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
            print(f"[Webhook-Sync] Started new conversation: {conversation.id}")
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

            # Send response back to WhatsApp (Twilio has 1600 char limit)
            # Split long messages into chunks
            max_msg_length = 1600
            if len(response_text) <= max_msg_length:
                resp.message(response_text)
                print(f"[Webhook] Sent single message ({len(response_text)} chars)")
            else:
                # Split into chunks at sentence boundaries
                chunks = split_message(response_text, max_msg_length)
                print(f"[Webhook] Splitting into {len(chunks)} messages")

                for i, chunk in enumerate(chunks):
                    if i == 0:
                        # First chunk includes part indicator
                        resp.message(f"{chunk}\n\n[Part {i+1}/{len(chunks)}]")
                    else:
                        resp.message(f"[Part {i+1}/{len(chunks)}]\n\n{chunk}")
                    print(f"[Webhook] Sent part {i+1}/{len(chunks)} ({len(chunk)} chars)")

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

            # Send user-friendly error message with technical details for debugging
            if "timeout" in error_msg.lower():
                user_error_msg = f"⏱️ Request timed out after 180 seconds. The AI is taking too long to respond. This was logged to the conversation history for debugging.\n\nError: {error_type}"
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                user_error_msg = f"🌐 Network connectivity issue. Please check your connection and try again.\n\nError: {error_type}"
            elif "rate" in error_msg.lower() or "429" in error_msg:
                user_error_msg = f"⚠️ The AI service is temporarily busy (rate limit). Please wait a moment and try again.\n\nError: {error_type}"
            elif "401" in error_msg or "authentication" in error_msg.lower():
                user_error_msg = f"🔑 API authentication failed. Please contact support.\n\nError: {error_type}"
            else:
                user_error_msg = f"❌ Error communicating with AI service. Please try again.\n\nError: {error_type}: {error_msg[:100]}"

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


@app.route('/process-queue', methods=['POST', 'GET'])
def process_queue_endpoint():
    """
    Manually trigger queue processing
    This endpoint can be called by Render cron job or manually
    """
    try:
        from process_queue import QueueProcessor

        processor = QueueProcessor()
        pending = firebase_service.get_pending_messages(limit=10)

        if not pending:
            return {
                "status": "success",
                "processed": 0,
                "message": "No pending messages"
            }

        # Process all pending messages
        processed_count = 0
        for queue_item in pending:
            try:
                processor.process_message(queue_item)
                processed_count += 1
            except Exception as e:
                print(f"[ProcessQueue] Error processing {queue_item['id']}: {e}")

        return {
            "status": "success",
            "processed": processed_count,
            "total_pending": len(pending)
        }

    except Exception as e:
        print(f"[ProcessQueue] Error: {e}")
        return {
            "status": "error",
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
