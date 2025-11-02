"""
Quick test script to verify setup before deployment
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "=" * 60)
print("DriveMind WhatsApp Bot - Configuration Test")
print("=" * 60 + "\n")

# Test environment variables
print("1. Environment Variables:")
print(f"   TWILIO_ACCOUNT_SID: {'✓ Set' if os.getenv('TWILIO_ACCOUNT_SID') else '✗ Missing'}")
print(f"   TWILIO_AUTH_TOKEN: {'✓ Set' if os.getenv('TWILIO_AUTH_TOKEN') else '✗ Missing'}")
print(f"   TWILIO_WHATSAPP_NUMBER: {os.getenv('TWILIO_WHATSAPP_NUMBER', '✗ Missing')}")
print(f"   CLAUDE_API_KEY: {'✓ Set' if os.getenv('CLAUDE_API_KEY') else '✗ Missing'}")
print(f"   LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'claude')}")
print()

# Test Firebase credentials
firebase_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
firebase_exists = os.path.exists(firebase_path)
print(f"2. Firebase Credentials:")
print(f"   Path: {firebase_path}")
print(f"   File exists: {'✓ Yes' if firebase_exists else '✗ No'}")
print()

# Test imports
print("3. Dependencies:")
try:
    from flask import Flask
    print("   Flask: ✓ Installed")
except ImportError:
    print("   Flask: ✗ Not installed")

try:
    from twilio.rest import Client
    print("   Twilio: ✓ Installed")
except ImportError:
    print("   Twilio: ✗ Not installed")

try:
    import anthropic
    print("   Anthropic: ✓ Installed")
except ImportError:
    print("   Anthropic: ✗ Not installed")

try:
    import firebase_admin
    print("   Firebase Admin: ✓ Installed")
except ImportError:
    print("   Firebase Admin: ✗ Not installed")

print()

# Test Firebase connection
if firebase_exists:
    print("4. Testing Firebase Connection...")
    try:
        from firebase_service import FirebaseService
        firebase_service = FirebaseService()
        print("   Firebase: ✓ Connected")
    except Exception as e:
        print(f"   Firebase: ✗ Error - {str(e)}")
else:
    print("4. Skipping Firebase test (credentials missing)")

print()

# Test LLM connection
if os.getenv('CLAUDE_API_KEY'):
    print("5. Testing Claude API...")
    try:
        from llm_service import LLMService
        from models import Message
        from datetime import datetime

        llm_service = LLMService(provider='claude')
        test_msg = Message(
            content="Say 'hello' in one word",
            role="user",
            timestamp=datetime.now()
        )

        response, input_tokens, output_tokens = llm_service.send_message([test_msg], "haiku")
        print(f"   Claude API: ✓ Working")
        print(f"   Response: {response[:50]}...")
        print(f"   Tokens: {input_tokens} in, {output_tokens} out")
    except Exception as e:
        print(f"   Claude API: ✗ Error - {str(e)}")
else:
    print("5. Skipping Claude test (API key missing)")

print()

# Test keyword detector
print("6. Testing Keyword Detection...")
try:
    from keyword_detector import KeywordDetector

    test_cases = [
        ("Hello there over", "haiku"),
        ("Think carefully about this", "haiku"),
        ("What's the weather?", "haiku")
    ]

    for msg, current_model in test_cases:
        processed = KeywordDetector.process_message(msg, current_model)
        print(f"   Input: '{msg}'")
        print(f"   Output: '{processed.cleaned_message}' (Model: {processed.model})")

    print("   Keyword Detection: ✓ Working")
except Exception as e:
    print(f"   Keyword Detection: ✗ Error - {str(e)}")

print()
print("=" * 60)
print("Test Complete!")
print("=" * 60 + "\n")

# Summary
if firebase_exists and os.getenv('CLAUDE_API_KEY') and os.getenv('TWILIO_ACCOUNT_SID'):
    print("✓ Ready to deploy!")
else:
    print("✗ Please fix the issues above before deploying")
    if not firebase_exists:
        print("  - Add firebase-credentials.json")
    if not os.getenv('CLAUDE_API_KEY'):
        print("  - Set CLAUDE_API_KEY in .env")
    if not os.getenv('TWILIO_ACCOUNT_SID'):
        print("  - Set Twilio credentials in .env")

print()
