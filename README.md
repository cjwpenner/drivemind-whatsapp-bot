# DriveMind WhatsApp Bot

WhatsApp integration for DriveMind - chat with Claude AI through WhatsApp for hands-free voice conversations in your car.

## Features

- **Voice-Optimized Responses**: Responses formatted for text-to-speech playback
- **Automatic Model Switching**: Use keywords like "think carefully" to trigger Claude Sonnet for deeper analysis
- **Conversation History**: Maintains context across messages using shared Firebase database
- **Keyword Cleanup**: Removes "over", "done", "send" from message endings
- **Same Backend as DriveMind App**: Uses the same Firebase database and logic as the Android app

## Architecture

```
WhatsApp User → Twilio WhatsApp API → Flask Server → Claude/OpenAI → Firebase
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- Twilio account with WhatsApp enabled
- Claude API key and/or OpenAI API key
- Firebase project (same as DriveMind Android app)
- Render.com account (for hosting)

### 2. Local Development Setup

**Install Dependencies:**
```bash
cd whatsapp-bot
pip install -r requirements.txt
```

**Configure Environment:**
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add your credentials:
- `TWILIO_ACCOUNT_SID`: From Twilio Console
- `TWILIO_AUTH_TOKEN`: From Twilio Console
- `CLAUDE_API_KEY`: Your Anthropic API key
- `OPENAI_API_KEY`: (Optional) Your OpenAI API key
- `FIREBASE_CREDENTIALS_PATH`: Path to your Firebase service account JSON

**Get Firebase Credentials:**
1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate New Private Key"
3. Save the JSON file as `firebase-credentials.json` in the whatsapp-bot directory
4. **IMPORTANT**: Add `firebase-credentials.json` to `.gitignore`

**Run Locally:**
```bash
python app.py
```

**Expose with ngrok (for testing):**
```bash
ngrok http 5000
```

**Configure Twilio Webhook:**
1. Go to Twilio Console → Messaging → Try it Out → Send a WhatsApp message
2. In "Sandbox Settings", set the webhook URL to: `https://your-ngrok-url.ngrok.io/webhook`
3. Test by sending a WhatsApp message to your Twilio number

### 3. Render.com Deployment

**Step 1: Prepare Your Code**
```bash
# Create .gitignore if not exists
echo "firebase-credentials.json" >> .gitignore
echo ".env" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Commit your code
git add .
git commit -m "Add WhatsApp bot"
git push
```

**Step 2: Create Render Web Service**

1. Log in to [Render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `drivemind-whatsapp-bot`
   - **Environment**: Python 3
   - **Region**: Choose closest to your location
   - **Branch**: main (or your branch name)
   - **Root Directory**: `whatsapp-bot`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (or Starter for better performance)

**Step 3: Set Environment Variables**

In Render Dashboard → Environment:

```
TWILIO_ACCOUNT_SID=YOUR_TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=YOUR_TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
CLAUDE_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here
LLM_PROVIDER=claude
FLASK_ENV=production
FLASK_DEBUG=False
PORT=10000
```

**Step 4: Add Firebase Credentials**

Option A: Upload as Secret File (Recommended)
1. In Render Dashboard → Secret Files
2. Add new secret file:
   - **Filename**: `firebase-credentials.json`
   - **Contents**: Paste your Firebase JSON
3. Set environment variable: `FIREBASE_CREDENTIALS_PATH=/etc/secrets/firebase-credentials.json`

Option B: Use Environment Variable
1. Copy your firebase-credentials.json content
2. Minify it (remove whitespace): `cat firebase-credentials.json | jq -c`
3. Add as environment variable: `FIREBASE_CREDENTIALS_JSON=<minified json>`
4. Update `firebase_service.py` to read from env var

**Step 5: Deploy**

1. Click "Create Web Service"
2. Wait for deployment (2-3 minutes)
3. Copy your Render URL: `https://drivemind-whatsapp-bot.onrender.com`

**Step 6: Configure Twilio Production Webhook**

1. Go to Twilio Console → Messaging → Settings → WhatsApp Sandbox
2. Set "When a message comes in" to: `https://your-render-url.onrender.com/webhook`
3. Save

### 4. Testing

**Send a test message:**
```
WhatsApp to: +14155238886
Message: "Hello, what's the weather like today?"
```

**Test model switching:**
```
Message: "Think carefully about the implications of AI in society"
```
This will automatically use Claude Sonnet for deeper analysis.

**Start new conversation:**
```
Message: "new conversation"
```

**Check health:**
```
curl https://your-render-url.onrender.com/health
```

## How It Works

### Keyword Detection

The bot automatically detects keywords to switch between models:

**Sonnet Triggers** (uses Claude Sonnet 4.5 for deeper analysis):
- "think carefully"
- "think deeply"
- "analyze"
- "be thorough"
- "explain in detail"
- "deep dive"

**End Keywords** (removed from message):
- "over"
- "done"
- "send"
- "that's it"

### Example Conversations

```
User: "What's the capital of France over"
Bot receives: "What's the capital of France"
Model: Haiku (fast)

User: "Think carefully about climate change"
Bot receives: "Think carefully about climate change"
Model: Sonnet (thoughtful)
```

## Firebase Integration

The bot shares the same Firebase database as the DriveMind Android app:
- Project: `drivemind-742aa`
- Collection: `conversations`
- User ID: WhatsApp phone number (e.g., `whatsapp:+447971278897`)

## Cost Estimate

- **Twilio WhatsApp**: $0.005 per message (~$5 for 1000 messages)
- **Render.com**: Free tier (or $7/month for Starter)
- **Claude API**: Your existing usage costs
- **Firebase**: Free tier (likely sufficient)

## Troubleshooting

**Bot not responding:**
1. Check Render logs: Dashboard → Logs
2. Verify environment variables are set
3. Test webhook: `curl -X POST https://your-url/webhook -d "Body=test&From=whatsapp:+1234567890"`

**Firebase errors:**
1. Verify firebase-credentials.json is correctly uploaded
2. Check Firebase project ID matches
3. Ensure Firestore database exists

**LLM errors:**
1. Verify API keys are correct
2. Check API key has sufficient credits
3. Review error logs in Render

## Commands

- `new conversation` - Start a fresh conversation
- `new` - Same as above
- `reset` - Same as above

## Development

**Run tests:**
```bash
python -m pytest tests/
```

**View logs:**
```bash
# Local
tail -f app.log

# Render
# View in dashboard → Logs
```

## Security Notes

- Never commit `.env` or `firebase-credentials.json` to git
- Use Render's Secret Files for sensitive data
- Rotate API keys regularly
- Monitor usage to prevent unexpected costs

## Next Steps

1. Apply for Twilio WhatsApp Business Account (to remove sandbox limitations)
2. Add conversation export feature
3. Implement usage analytics
4. Add support for voice messages
5. Create web dashboard for conversation management

## Support

For issues or questions, check the logs and verify all credentials are correct.
