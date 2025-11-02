# WhatsApp Bot - Queue-Based Message Processing

## The Problem

Render's free tier spins down after 15 minutes of inactivity. When a WhatsApp message arrives:
1. Twilio sends a webhook request to your Render app
2. Render starts waking up (cold start ~30-60 seconds)
3. Twilio times out after 15 seconds
4. Message is lost

## The Solution

**Firebase-based message queue with async processing**

### How It Works

```
User sends WhatsApp message
    ↓
Twilio webhook → /webhook endpoint
    ↓
Immediately save to Firebase queue (< 1 second)
    ↓
Return 200 OK to Twilio (no timeout!)
    ↓
Background processor picks up message
    ↓
Process with LLM
    ↓
Send response via Twilio API
```

### Key Components

1. **Fast Webhook** (`/webhook` in `app.py`)
   - Receives message from Twilio
   - Saves to Firebase `message_queue` collection
   - Returns immediately (no LLM processing)
   - **Never times out, never loses messages**

2. **Message Queue** (Firebase Firestore collection)
   - Collection: `message_queue`
   - Document ID: Twilio `MessageSid` (prevents duplicates)
   - Status: `pending`, `processing`, `completed`, `failed`

3. **Background Processor** (`process_queue.py`)
   - Polls Firebase every 3 seconds
   - Processes pending messages
   - Sends responses via Twilio REST API

## Setup Instructions

### Step 1: Verify Twilio Webhook URL

In the Twilio Console, ensure your webhook URL is set to:
```
https://drivemind-whatsapp-bot.onrender.com/webhook
```

**Make sure there are NO `#rc=...` parameters**

### Step 2: Deploy the Updated Code

Commit and push the changes to trigger Render deployment:

```bash
git add .
git commit -m "Add queue-based message processing for cold starts"
git push
```

### Step 3: Choose a Processing Method

You have **3 options** for running the background processor:

#### Option A: Render Background Worker (Recommended but Paid)

**Pros:**
- Always running
- Fastest response times (processes within seconds)
- Handles high message volume

**Cons:**
- Requires paid Render plan (~$7/month for background worker)

**Setup:**
1. In Render dashboard, add a new **Background Worker**
2. Set start command: `python process_queue.py`
3. Use same environment variables as web service

#### Option B: Render Cron Job (Free, Recommended for Low Traffic)

**Pros:**
- Completely free
- Good for occasional messages
- No code changes needed

**Cons:**
- Responses delayed by cron frequency (e.g., every 1-5 minutes)
- Maximum frequency: every minute

**Setup:**
1. In Render dashboard, click your web service
2. Go to **Settings** → **Cron Jobs**
3. Add cron job:
   - **Schedule**: `*/1 * * * *` (every minute)
   - **Command**: `curl -X POST https://your-app-name.onrender.com/process-queue`

Render free tier allows cron jobs that call your web service!

#### Option C: External Cron Service (Free Alternative)

**Pros:**
- Free
- Works with Render free tier
- Can run more frequently than Render cron

**Cons:**
- Requires external service setup
- Slightly more complex

**Setup:**
1. Sign up for free cron service:
   - https://cron-job.org (free, no signup)
   - https://www.easycron.com (free tier: 1 job/minute)
   - https://console.cron-job.org (free)

2. Create a cron job:
   - URL: `https://your-app-name.onrender.com/process-queue`
   - Method: GET or POST
   - Frequency: Every 1-5 minutes

### Step 4: Test the System

1. **Wait 15+ minutes** for Render to go to sleep
2. **Send a WhatsApp message** to your bot
3. **Check what happens:**
   - Message should be queued immediately (no timeout)
   - Within 1-5 minutes (depending on cron), you'll get a response
   - Check Render logs to see: `[Webhook] Message queued successfully`

### Step 5: Monitor the Queue

You can check the queue status by visiting:
```
https://your-app-name.onrender.com/process-queue
```

This will:
- Process any pending messages immediately
- Return JSON with status

## Monitoring & Debugging

### Check Queue in Firebase

1. Go to Firebase Console: https://console.firebase.google.com/
2. Select your project: `drivemind-742aa`
3. Go to **Firestore Database**
4. Look for collection: `message_queue`
5. Check document statuses:
   - `pending`: Waiting to be processed
   - `processing`: Currently being processed
   - `completed`: Successfully sent
   - `failed`: Error occurred

### Check Render Logs

**Webhook logs:**
```
[Webhook] Received message SMxxxxx from whatsapp:+447971278897: Hello
[Firebase] Queued message SMxxxxx
[Webhook] Message queued successfully, returning 200 OK
```

**Processor logs:**
```
[Processor] Found 1 pending messages
[Processor] Processing message SMxxxxx from whatsapp:+447971278897
[Processor] Calling claude with haiku model...
[Processor] Got response (234 chars)
[Twilio] Sent message SMyyyyy to whatsapp:+447971278897
[Processor] Completed message SMxxxxx
```

### Troubleshooting

**Problem: Messages queued but never processed**
- Check cron job is running (Render dashboard or external service)
- Manually trigger: `curl -X POST https://your-app.onrender.com/process-queue`
- Check Render logs for processor errors

**Problem: Messages processed multiple times**
- This shouldn't happen (MessageSid prevents duplicates)
- Check Firebase - look for duplicate MessageSid documents

**Problem: "Sorry, I'm having trouble..." error**
- Firebase connection issue
- Check environment variables (FIREBASE_CREDENTIALS_PATH)
- Check Render logs for Firebase errors

**Problem: Long delays (> 5 minutes)**
- Increase cron frequency
- Consider paid background worker

## Cost Comparison

| Method | Cost | Response Time | Best For |
|--------|------|---------------|----------|
| Background Worker | ~$7/month | 3-10 seconds | High traffic, instant responses |
| Render Cron Job | Free | 1-5 minutes | Low traffic, casual use |
| External Cron | Free | 1-5 minutes | Low traffic, more flexibility |

## Advanced: Manual Queue Processing

You can also process the queue manually via code:

```python
from process_queue import QueueProcessor

processor = QueueProcessor()
processor.run(poll_interval=3)  # Run continuously
```

Or process once:

```bash
curl -X POST https://your-app-name.onrender.com/process-queue
```

## Fallback: Synchronous Processing

If you need to temporarily disable the queue, you can use the synchronous endpoint:

1. In Twilio console, change webhook URL to:
   ```
   https://your-app-name.onrender.com/webhook-sync
   ```

2. This processes messages immediately (old behavior)
3. Will timeout on cold starts, but works when app is warm

## Summary

**What you need to do:**

1. ✅ Revert Twilio webhook URL to: `https://your-app.onrender.com/webhook`
2. ✅ Deploy code to Render (git push)
3. ✅ Set up cron job (Render or external service) to call `/process-queue` every 1-5 minutes
4. ✅ Test by sending message after 15+ minute sleep

**Result:**
- No more lost messages!
- Messages queued instantly
- Responses delivered within 1-5 minutes (depending on cron frequency)
- Completely free (with Render cron or external cron)

---

Need help? Check the logs or reach out!
