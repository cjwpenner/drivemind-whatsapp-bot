"""
Firebase integration for conversation storage
Uses the same Firebase database as DriveMind Android app
"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from models import Conversation, Message
from typing import Optional, List
import os


class FirebaseService:
    """Service for managing conversations in Firestore"""

    def __init__(self):
        """Initialize Firebase Admin SDK"""
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Use service account key file
            cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                # For Render.com deployment, use environment variable
                firebase_admin.initialize_app()

        self.db = firestore.client()

    def get_or_create_active_conversation(self, user_id: str) -> Conversation:
        """
        Get or create the active conversation for a user
        user_id is the WhatsApp phone number (e.g., 'whatsapp:+447971278897')
        """
        # Try to get existing active conversation
        active_conv = self.get_active_conversation(user_id)
        if active_conv:
            return active_conv

        # Create new conversation
        return self.create_conversation(user_id, "WhatsApp Conversation")

    def get_active_conversation(self, user_id: str) -> Optional[Conversation]:
        """Get the active conversation for a user"""
        try:
            docs = self.db.collection('conversations') \
                .where('userId', '==', user_id) \
                .where('isActive', '==', True) \
                .limit(1) \
                .stream()

            for doc in docs:
                data = doc.to_dict()
                conversation = Conversation(
                    id=doc.id,
                    user_id=data.get('userId', ''),
                    title=data.get('title', 'WhatsApp Conversation'),
                    created_at=data.get('createdAt'),
                    updated_at=data.get('updatedAt'),
                    is_active=data.get('isActive', True),
                    token_count=data.get('tokenCount', 0),
                    messages=self._parse_messages(data.get('messages', []))
                )
                return conversation

            return None
        except Exception as e:
            print(f"Error getting active conversation: {e}")
            return None

    def create_conversation(self, user_id: str, title: str) -> Conversation:
        """Create a new conversation with timestamp-based ID"""
        try:
            # Mark all existing conversations as inactive
            existing_docs = self.db.collection('conversations') \
                .where('userId', '==', user_id) \
                .where('isActive', '==', True) \
                .stream()

            for doc in existing_docs:
                doc.reference.update({'isActive': False})

            # Create new conversation with timestamp-based ID
            now = datetime.now()
            # Format: YYYY-MM-DD_HH-MM-SS
            timestamp_id = now.strftime('%Y-%m-%d_%H-%M-%S')

            conversation = Conversation(
                id=timestamp_id,
                user_id=user_id,
                title=title,
                created_at=now,
                updated_at=now,
                is_active=True,
                token_count=0,
                messages=[]
            )

            # Use timestamp as document ID
            doc_ref = self.db.collection('conversations').document(timestamp_id)
            doc_ref.set(conversation.to_dict())

            return conversation
        except Exception as e:
            print(f"Error creating conversation: {e}")
            raise

    def add_message(self, conversation_id: str, message: Message) -> bool:
        """Add a message to a conversation"""
        try:
            doc_ref = self.db.collection('conversations').document(conversation_id)
            doc = doc_ref.get()

            if not doc.exists:
                print(f"Conversation {conversation_id} not found")
                return False

            data = doc.to_dict()
            messages = data.get('messages', [])
            messages.append(message.to_dict())

            doc_ref.update({
                'messages': messages,
                'updatedAt': datetime.now()
            })

            return True
        except Exception as e:
            print(f"Error adding message: {e}")
            return False

    def update_token_count(self, conversation_id: str, token_count: int) -> bool:
        """Update conversation token count"""
        try:
            doc_ref = self.db.collection('conversations').document(conversation_id)
            doc_ref.update({'tokenCount': token_count})
            return True
        except Exception as e:
            print(f"Error updating token count: {e}")
            return False

    def start_new_conversation(self, user_id: str) -> Conversation:
        """Start a new conversation (marks current as inactive)"""
        return self.create_conversation(user_id, "New WhatsApp Conversation")

    def _parse_messages(self, messages_data: List) -> List[Message]:
        """Parse messages from Firestore data"""
        messages = []
        for msg_data in messages_data:
            if isinstance(msg_data, dict):
                messages.append(Message(
                    content=msg_data.get('content', ''),
                    role=msg_data.get('role', 'user'),
                    timestamp=msg_data.get('timestamp', datetime.now()),
                    model=msg_data.get('model'),
                    tokens=msg_data.get('tokens', 0)
                ))
        return messages

    def enqueue_message(self, from_number: str, message_body: str, message_sid: str) -> bool:
        """
        Queue an incoming message for async processing
        Returns True if successfully queued
        """
        try:
            queue_item = {
                'from_number': from_number,
                'message_body': message_body,
                'message_sid': message_sid,  # Twilio's unique message ID
                'status': 'pending',  # pending, processing, completed, failed
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'retry_count': 0
            }

            # Use message_sid as document ID to prevent duplicates
            doc_ref = self.db.collection('message_queue').document(message_sid)
            doc_ref.set(queue_item)

            print(f"[Firebase] Queued message {message_sid}")
            return True
        except Exception as e:
            print(f"[Firebase] Error queuing message: {e}")
            return False

    def get_pending_messages(self, limit: int = 10) -> List[dict]:
        """Get pending messages from the queue"""
        try:
            docs = self.db.collection('message_queue') \
                .where('status', '==', 'pending') \
                .order_by('created_at') \
                .limit(limit) \
                .stream()

            messages = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                messages.append(data)

            return messages
        except Exception as e:
            print(f"[Firebase] Error getting pending messages: {e}")
            return []

    def update_message_status(self, message_sid: str, status: str, error_msg: str = None) -> bool:
        """Update the status of a queued message"""
        try:
            doc_ref = self.db.collection('message_queue').document(message_sid)
            update_data = {
                'status': status,
                'updated_at': datetime.now()
            }

            if error_msg:
                update_data['error'] = error_msg

            if status == 'processing':
                # Increment retry count
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    update_data['retry_count'] = data.get('retry_count', 0) + 1

            doc_ref.update(update_data)
            return True
        except Exception as e:
            print(f"[Firebase] Error updating message status: {e}")
            return False
