# Render.com Deployment Guide

Step-by-step guide to deploy DriveMind WhatsApp Bot to Render.com

## Prerequisites Checklist

- [ ] Render.com account created
- [ ] GitHub repository ready
- [ ] Firebase service account JSON downloaded
- [ ] Claude API key ready
- [ ] Twilio credentials ready

## Step 1: Prepare Firebase Credentials

### Option A: Get Your Firebase Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select project: **drivemind-742aa**
3. Click gear icon → Project Settings
4. Go to "Service Accounts" tab
5. Click "Generate New Private Key"
6. Save the JSON file
7. **IMPORTANT**: Keep this file secure, don't commit it to git

### Option B: Use Existing Android App Credentials

If your Android app already has Firebase configured, you can reuse those credentials by finding the `google-services.json` file. However, the service account key (above) is preferred for server-side apps.

## Step 2: Prepare Your Repository

```bash
cd C:\Users\Chris\AndroidStudioProjects\DriveLLM

# Initialize git if not already done
git init
git add whatsapp-bot/
git commit -m "Add WhatsApp bot"

# Push to GitHub (if not already)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## Step 3: Create .env File Locally (for testing)

```bash
cd whatsapp-bot
cp .env.example .env
```

Edit `.env` with your credentials:
```env
TWILIO_ACCOUNT_SID=YOUR_TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=YOUR_TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
CLAUDE_API_KEY=YOUR_CLAUDE_KEY_HERE
OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE
LLM_PROVIDER=claude
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

## Step 4: Test Locally (Optional but Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Place your Firebase JSON in the whatsapp-bot directory
# Name it: firebase-credentials.json

# Run test script
python test_local.py

# If all tests pass, run the app
python app.py

# In another terminal, use ngrok
ngrok http 5000

# Configure Twilio sandbox webhook to your ngrok URL
# Test by sending a WhatsApp message
```

## Step 5: Create Render Web Service

### 5.1: Log in to Render

1. Go to [https://render.com](https://render.com)
2. Log in or create account
3. Click "New +" button → "Web Service"

### 5.2: Connect Repository

1. Click "Connect account" to link GitHub
2. Select your repository
3. Click "Connect"

### 5.3: Configure Service

Fill in the following settings:

**Basic Settings:**
- **Name**: `drivemind-whatsapp-bot` (or any name you prefer)
- **Region**: Select closest to your location (e.g., Oregon (US West))
- **Branch**: `main` (or your branch name)
- **Root Directory**: `whatsapp-bot`

**Build & Deploy:**
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

**Plan:**
- **Instance Type**: Free (or Starter $7/month for better performance)

### 5.4: Add Environment Variables

Click "Environment" (or "Advanced" → "Environment Variables")

Add the following variables:

```
TWILIO_ACCOUNT_SID = YOUR_TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = YOUR_TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER = whatsapp:+14155238886
CLAUDE_API_KEY = your_claude_api_key_here
OPENAI_API_KEY = your_openai_api_key_here
LLM_PROVIDER = claude
FLASK_ENV = production
FLASK_DEBUG = False
PORT = 10000
```

**IMPORTANT**: Replace `your_claude_api_key_here` with your actual key!

### 5.5: Add Firebase Credentials as Secret File

This is the MOST IMPORTANT step!

1. In Render Dashboard, find "Secret Files" section
2. Click "Add Secret File"
3. Configure:
   - **Filename**: `firebase-credentials.json`
   - **Contents**: Paste the ENTIRE contents of your Firebase service account JSON
4. Click "Save"

5. Add one more environment variable:
   ```
   FIREBASE_CREDENTIALS_PATH = /etc/secrets/firebase-credentials.json
   ```

### 5.6: Deploy

1. Click "Create Web Service"
2. Wait 2-3 minutes for deployment
3. Check logs for any errors
4. Copy your service URL (e.g., `https://drivemind-whatsapp-bot.onrender.com`)

## Step 6: Configure Twilio Webhook

### 6.1: Update Twilio

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to: Messaging → Try it out → Send a WhatsApp message
3. Click on "Sandbox Settings"
4. Find "When a message comes in"
5. Set the webhook URL to:
   ```
   https://YOUR-RENDER-URL.onrender.com/webhook
   ```
6. Method: POST
7. Click "Save"

### 6.2: Test the Integration

1. Send a WhatsApp message to your Twilio number: `+14155238886`
2. Join the sandbox first (Twilio will give you a code to send)
3. Once joined, send: `Hello DriveMind!`
4. You should get a response within a few seconds

## Step 7: Verify Deployment

### Check Health Endpoint

Visit: `https://YOUR-RENDER-URL.onrender.com/health`

You should see:
```json
{
  "status": "healthy",
  "firebase": "connected",
  "llm_provider": "claude"
}
```

### Check Logs

1. In Render Dashboard → Your Service → Logs
2. You should see:
   ```
   DriveMind WhatsApp Bot Starting...
   LLM Provider: claude
   ```

### Send Test Messages

Try these test messages via WhatsApp:

1. **Basic test**: `What's 2 + 2?`
2. **Sonnet trigger**: `Think carefully about AI safety`
3. **End keyword**: `What is Python over`
4. **New conversation**: `new conversation`

## Troubleshooting

### Bot Not Responding

**Check Render Logs:**
1. Dashboard → Logs
2. Look for errors

**Common Issues:**
- Firebase credentials not uploaded → Check Secret Files
- Wrong webhook URL → Verify Twilio configuration
- API key invalid → Check environment variables

### Firebase Connection Failed

**Error**: `Firebase: disconnected` in health endpoint

**Solutions:**
1. Verify Secret File uploaded correctly
2. Check filename is exactly `firebase-credentials.json`
3. Verify `FIREBASE_CREDENTIALS_PATH=/etc/secrets/firebase-credentials.json`
4. Check Firebase project ID matches (drivemind-742aa)

### Claude API Errors

**Error**: `Claude API error: 401`

**Solution**: Check `CLAUDE_API_KEY` is set correctly

**Error**: `Claude API error: 429`

**Solution**: Rate limit exceeded, wait or upgrade API plan

### Webhook Not Being Called

1. Check Twilio webhook is set to your Render URL
2. Verify method is POST
3. Make sure URL ends with `/webhook`
4. Test manually:
   ```bash
   curl -X POST https://your-url.onrender.com/webhook \
     -d "Body=test&From=whatsapp:+1234567890"
   ```

### Free Tier Limitations

Render's free tier:
- Spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds
- **Solution**: Upgrade to Starter ($7/month) for always-on service

## Monitoring

### View Logs in Real-Time

```bash
# Using Render CLI (optional)
render logs -s drivemind-whatsapp-bot --tail
```

Or view in Dashboard → Logs (auto-refreshes)

### Check Usage

1. **Twilio**: Console → Usage
2. **Render**: Dashboard → Metrics
3. **Claude API**: Anthropic Console → Usage
4. **Firebase**: Console → Usage

## Updating Your Deployment

When you make changes:

```bash
git add .
git commit -m "Update WhatsApp bot"
git push

# Render will auto-deploy on push
```

To force redeploy:
1. Dashboard → Manual Deploy → Deploy Latest Commit

## Security Best Practices

1. **Never commit secrets** to git
2. **Use Render's Secret Files** for Firebase JSON
3. **Set environment variables** in Render, not in code
4. **Rotate API keys** regularly
5. **Monitor usage** to prevent unexpected costs

## Cost Estimates

- **Render Free**: $0/month (with limitations)
- **Render Starter**: $7/month (recommended)
- **Twilio WhatsApp**: $0.005/message
- **Claude Haiku**: ~$0.001 per conversation
- **Claude Sonnet**: ~$0.01 per conversation
- **Firebase**: Free tier sufficient for moderate use

## Next Steps After Deployment

1. **Apply for Twilio WhatsApp Business** to remove sandbox:
   - Go to Twilio Console → WhatsApp → Request Access
   - Fill application
   - Wait 1-2 weeks for approval

2. **Set up monitoring alerts**:
   - Render → Notifications
   - Set up Slack/email alerts for errors

3. **Create backup strategy**:
   - Firebase automatic backups enabled
   - Export conversations regularly

4. **Test in car**:
   - Send WhatsApp voice messages
   - Let text-to-speech read responses
   - Verify Android Auto WhatsApp integration works

## Support

If you encounter issues:
1. Check Render logs first
2. Verify all environment variables
3. Test Firebase connection manually
4. Check Twilio webhook logs in Twilio Console

## Success Criteria

✓ Health endpoint returns "healthy"
✓ WhatsApp messages get responses
✓ Conversation history saved to Firebase
✓ Keyword detection works (try "think carefully")
✓ Can start new conversations (send "new")
✓ Logs show no errors

---

**You're all set!** Your DriveMind WhatsApp bot is now live and ready to use in your car via WhatsApp's Android Auto integration.
