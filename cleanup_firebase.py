"""
Script to delete all conversations from Firebase
Use this to start with a clean slate
"""
import os
from dotenv import load_dotenv
from firebase_service import FirebaseService

load_dotenv()

def cleanup_all_conversations():
    """Delete all conversations from Firebase"""

    print("\n" + "="*60)
    print("Firebase Conversations Cleanup Script")
    print("="*60 + "\n")

    # Confirm deletion
    print("WARNING: This will DELETE ALL conversations in Firebase!")
    print("This action cannot be undone.\n")

    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("\nCancelled. No conversations were deleted.")
        return

    print("\nConnecting to Firebase...")
    firebase = FirebaseService()

    # Get all conversations
    print("Fetching all conversations...")
    conversations_ref = firebase.db.collection('conversations')
    docs = conversations_ref.stream()

    count = 0
    for doc in docs:
        print(f"Deleting conversation: {doc.id}")
        doc.reference.delete()
        count += 1

    print(f"\nSuccessfully deleted {count} conversations")
    print("="*60 + "\n")

if __name__ == "__main__":
    cleanup_all_conversations()
