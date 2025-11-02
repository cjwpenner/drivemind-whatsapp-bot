"""
Background processor for queued WhatsApp messages
Processes messages from Firebase queue and sends responses via Twilio
"""
import time
import traceback
from datetime import datetime
from twilio.rest import Client

from config import Config
from firebase_service import FirebaseService
from llm_service import LLMService
from keyword_detector import KeywordDetector
from models import Message


class QueueProcessor:
    """Process queued messages and send responses via Twilio"""

    def __init__(self):
        self.firebase = FirebaseService()
        self.llm = LLMService(
            claude_api_key=Config.CLAUDE_API_KEY,
            openai_api_key=Config.OPENAI_API_KEY,
            provider=Config.LLM_PROVIDER
        )
        self.twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        self.user_models = {}  # phone_number -> model preference

    def send_whatsapp_message(self, to_number: str, message_text: str):
        """Send a WhatsApp message via Twilio"""
        try:
            message = self.twilio_client.messages.create(
                body=message_text,
                from_=Config.TWILIO_WHATSAPP_NUMBER,
                to=to_number
            )
            print(f"[Twilio] Sent message {message.sid} to {to_number}")
            return True
        except Exception as e:
            print(f"[Twilio] Error sending message: {e}")
            return False

    def split_message(self, text: str, max_length: int = 1600) -> list:
        """Split long text into chunks at sentence boundaries"""
        import re

        chunk_size = max_length - 20

        chunks = []
        current_chunk = ""

        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            if len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                parts = sentence.split(', ')
                for part in parts:
                    if len(current_chunk) + len(part) + 2 > chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = part + ', '
                    else:
                        current_chunk += part + ', '
            elif len(current_chunk) + len(sentence) + 1 > chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
            else:
                current_chunk += sentence + " "

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def process_message(self, queue_item: dict):
        """Process a single queued message"""
        message_sid = queue_item['id']
        from_number = queue_item['from_number']
        incoming_msg = queue_item['message_body']

        print(f"\n[Processor] Processing message {message_sid} from {from_number}")

        try:
            # Mark as processing
            self.firebase.update_message_status(message_sid, 'processing')

            # Check for special commands
            lower_msg = incoming_msg.lower()

            if Config.ENABLE_NEW_CONVERSATION_COMMAND and lower_msg in ['new conversation', 'new', 'reset', 'start over']:
                conversation = self.firebase.start_new_conversation(from_number)
                print(f"[Processor] Started new conversation: {conversation.id}")
                self.send_whatsapp_message(from_number, "Started a new conversation. What would you like to talk about?")
                self.firebase.update_message_status(message_sid, 'completed')
                return

            # Get or create conversation
            conversation = self.firebase.get_or_create_active_conversation(from_number)
            print(f"[Processor] Using conversation: {conversation.id}")

            # Get user's current model preference
            current_model = self.user_models.get(from_number, "haiku")

            # Process message with keyword detection
            processed = KeywordDetector.process_message(incoming_msg, current_model)

            print(f"[Processor] Model: {processed.model}, Triggered Sonnet: {processed.triggered_sonnet}")

            # Update user's model preference if Sonnet was triggered
            if processed.triggered_sonnet:
                self.user_models[from_number] = "sonnet"
                print(f"[Processor] Switched to Sonnet model for user")

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

            # Save user message to Firebase
            self.firebase.add_message(conversation.id, user_message)

            # Call LLM
            print(f"[Processor] Calling {Config.LLM_PROVIDER} with {processed.model} model...")
            response_text, input_tokens, output_tokens = self.llm.send_message(
                messages=llm_messages,
                model=processed.model
            )

            print(f"[Processor] Got response ({len(response_text)} chars)")

            # Create assistant message
            assistant_message = Message(
                content=response_text,
                role="assistant",
                timestamp=datetime.now(),
                model=processed.model,
                tokens=input_tokens + output_tokens
            )

            # Save assistant message to Firebase
            self.firebase.add_message(conversation.id, assistant_message)

            # Update token count
            total_tokens = conversation.token_count + input_tokens + output_tokens
            self.firebase.update_token_count(conversation.id, total_tokens)

            print(f"[Processor] Saved to Firebase. Total tokens: {total_tokens}")

            # Send response back to WhatsApp
            if len(response_text) <= 1600:
                self.send_whatsapp_message(from_number, response_text)
            else:
                # Split into chunks
                chunks = self.split_message(response_text, 1600)
                print(f"[Processor] Splitting into {len(chunks)} messages")

                for i, chunk in enumerate(chunks):
                    if i == 0:
                        msg = f"{chunk}\n\n[Part {i+1}/{len(chunks)}]"
                    else:
                        msg = f"[Part {i+1}/{len(chunks)}]\n\n{chunk}"
                    self.send_whatsapp_message(from_number, msg)
                    time.sleep(0.5)  # Small delay between chunks

            # Mark as completed
            self.firebase.update_message_status(message_sid, 'completed')
            print(f"[Processor] Completed message {message_sid}")

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            print(f"[Processor] ERROR: {error_msg}")
            print(traceback.format_exc())

            # Mark as failed
            self.firebase.update_message_status(message_sid, 'failed', error_msg)

            # Send error message to user
            self.send_whatsapp_message(
                from_number,
                "Sorry, I encountered an error processing your message. Please try again."
            )

    def run(self, poll_interval: int = 5):
        """
        Main loop: poll for pending messages and process them
        poll_interval: seconds between checks
        """
        print("\n" + "=" * 60)
        print("Queue Processor Starting...")
        print(f"LLM Provider: {Config.LLM_PROVIDER}")
        print(f"Poll Interval: {poll_interval}s")
        print("=" * 60 + "\n")

        while True:
            try:
                # Get pending messages
                pending = self.firebase.get_pending_messages(limit=5)

                if pending:
                    print(f"[Processor] Found {len(pending)} pending messages")

                    for queue_item in pending:
                        self.process_message(queue_item)

                # Wait before next check
                time.sleep(poll_interval)

            except KeyboardInterrupt:
                print("\n[Processor] Shutting down...")
                break
            except Exception as e:
                print(f"[Processor] Loop error: {e}")
                print(traceback.format_exc())
                time.sleep(poll_interval)


if __name__ == '__main__':
    processor = QueueProcessor()
    processor.run(poll_interval=3)  # Check every 3 seconds
