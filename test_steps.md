# Arabic Menu Extractor — Complete Testing Guide

> **This file is gitignored.** It contains step-by-step instructions for
> setting up, running, and testing the entire application locally.

---

## Prerequisites

- **Docker Desktop** installed and running
- **Python 3.11+** with `uv` package manager
- **Postman** installed
- **DBeaver** installed (for inspecting PostgreSQL)
- Your **Kaggle notebook** running with the OCR model (ngrok URL ready)
- An **OpenAI API key** with access to `gpt-5` and `text-embedding-3-small`

---

## Step 1: Start Infrastructure (Docker)

Open a terminal in the project root and run:

```bash
docker compose -f docker/docker-compose.yml up -d
```

**Verify both services are running:**

```bash
docker compose -f docker/docker-compose.yml ps
```

You should see:
- `menu-extractor-postgres` — running on port `5423`
- `menu-extractor-qdrant` — running on port `6333`

**Quick checks:**
- Qdrant dashboard: Open `http://localhost:6333/dashboard` in your browser
- PostgreSQL: Use DBeaver (see Step 2)

---

## Step 2: Connect DBeaver to PostgreSQL

1. Open DBeaver
2. Click **New Database Connection** → choose **PostgreSQL**
3. Fill in:
   - **Host**: `localhost`
   - **Port**: `5423`
   - **Database**: `menu_extractor_sessions`
   - **Username**: `menu_user`
   - **Password**: `menu_password`
4. Click **Test Connection** → should say "Connected"
5. Click **Finish**

After starting the FastAPI server, you'll see these tables:
- `menus` — menu metadata (our app table)
- `menu_items` — extracted items (our app table)
- `adk_*` tables — ADK auto-created session/state/event tables

---

## Step 3: Configure Environment

```bash
# Copy the example env file
copy src\.env.example src\.env
```

Edit `src/.env` and fill in:
```env
KAGGLE_OCR_URL=https://YOUR-NGROK-URL.ngrok-free.dev/generate
OPENAI_API_KEY=sk-your-actual-key
```

The other values can stay as defaults. Notable defaults:
- `DATABASE_URL` uses port `5423` (matching docker-compose)
- `SESSION_TTL_HOURS=24` (sessions expire after 24h of inactivity)
- `SESSION_CLEANUP_INTERVAL_MINUTES=60` (cleanup runs every hour)

---

## Step 4: Install Dependencies

```bash
uv sync
```

If you haven't added packages yet:
```bash
uv add fastapi "uvicorn[standard]" python-multipart httpx openai qdrant-client json-repair pydantic-settings google-adk python-dotenv asyncpg "sqlalchemy[asyncio]"
```

---

## Step 5: Start the Kaggle Notebook

1. Open your Kaggle notebook with the Qwen2.5-VL OCR model
2. Run all cells
3. Copy the ngrok URL it prints (something like `https://xxxx.ngrok-free.dev/generate`)
4. Paste it into `src/.env` as the `KAGGLE_OCR_URL` value

---

## Step 6: Start the FastAPI Server

From the project root:

```bash
uv run uvicorn src.main:app --reload --port 5000
```

You should see:
```
INFO | Initializing application...
INFO | PostgreSQL tables ready
INFO | Qdrant collection ready
INFO | Session cleanup loop started (TTL=24h, interval=60m)
INFO | Application started successfully
INFO | Uvicorn running on http://127.0.0.1:5000
```

**FastAPI Swagger Docs:** Open `http://localhost:5000/docs` in your browser.

---

## Step 7: Start the Frontend UI

Open a **new terminal** in the `frontend` folder:

```bash
cd frontend
npm install
npm run dev
```

You should see:
```
  VITE v8.0.3  ready in 524 ms

  ➜  Local:   http://localhost:5173/
```

Open `http://localhost:5173` in your browser. You can now test the entire end-to-end flow using the beautiful dark-mode UI! (If you prefer Postman APIs, see Step 8).

---

## Step 8: Test All Endpoints in Postman

### Create a new Postman Collection called "Menu Extractor API"

Set the base URL variable: `{{base_url}}` = `http://localhost:5000`

---

### 7.1 — Health Check

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/health` |
| **Body** | None |

**Expected Response (200):**
```json
{
    "status": "healthy",
    "service": "arabic-menu-extractor",
    "version": "0.1.0",
    "session_ttl_hours": 24
}
```

---

### 7.2 — Upload Menu

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **URL** | `{{base_url}}/api/v1/menus/upload` |
| **Body** | `form-data` |

**Form-data fields:**

| Key | Type | Value |
|-----|------|-------|
| `file` | File | Select a menu image (jpg/png/jpeg) |
| `restaurant_name` | Text | `مطعم الشامي` (or any name) |

**Expected Response (200):**
```json
{
    "menu_id": "550e8400-e29b-41d4-a716-446655440000",
    "restaurant_name": "مطعم الشامي",
    "item_count": 15,
    "status": "success"
}
```

> **⚠️ Save the `menu_id` from the response — you'll need it for the next tests!**

**What to verify after this call:**
- Qdrant dashboard (`http://localhost:6333/dashboard`) → collection `menu_items` should have points
- DBeaver → `menus` table should have a new row
- DBeaver → `menu_items` table should have rows with names and prices

---

### 7.3 — List All Menus

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/menus` |
| **Body** | None |

**Expected Response (200):**
```json
{
    "menus": [
        {
            "menu_id": "550e8400-e29b-41d4-a716-446655440000",
            "restaurant_name": "مطعم الشامي",
            "item_count": 15,
            "created_at": "2026-04-05T01:30:00Z"
        }
    ],
    "total": 1
}
```

---

### 7.4 — Get Menu Detail

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/menus/{menu_id}` |
| **Body** | None |

Replace `{menu_id}` with the actual ID from step 7.2.

**Expected Response (200):**
```json
{
    "menu_id": "550e8400-e29b-41d4-a716-446655440000",
    "restaurant_name": "مطعم الشامي",
    "item_count": 15,
    "created_at": "2026-04-05T01:30:00Z",
    "items": [
        {"name": "كباب مشوي", "price": "45"},
        {"name": "شاورما دجاج", "price": "30"}
    ]
}
```

---

### 7.5 — Chat with Menu

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **URL** | `{{base_url}}/api/v1/chat` |
| **Body** | `raw` → `JSON` |

**Request body (first message — creates a new session):**
```json
{
    "message": "ايه اكتر حاجة غالية في المنيو؟",
    "menu_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "test-user-1"
}
```

**Expected Response (200):**
```json
{
    "response": "أغلى طبق في المنيو هو ...",
    "session_id": "abc123-session-id"
}
```

> **Save the `session_id` for follow-up messages and history!**

**Follow-up message (same session):**
```json
{
    "message": "وايه ارخص حاجة؟",
    "menu_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "test-user-1",
    "session_id": "abc123-session-id"
}
```

**What to verify:**
- The agent remembers the previous message (same session)
- DBeaver → Check the ADK session tables for stored events
- The response is in Arabic (matching the user's language)

---

### 7.6 — Get Chat History

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/v1/chat/sessions/{session_id}/history` |
| **Body** | None |

Replace `{session_id}` with the ID from step 7.5.

**Expected Response (200):**
```json
{
    "session_id": "abc123-session-id",
    "messages": [
        {
            "role": "user",
            "content": "ايه اكتر حاجة غالية في المنيو؟",
            "timestamp": "2026-04-05T01:35:00Z"
        },
        {
            "role": "model",
            "content": "أغلى طبق في المنيو هو ...",
            "timestamp": "2026-04-05T01:35:02Z"
        },
        {
            "role": "user",
            "content": "وايه ارخص حاجة؟",
            "timestamp": "2026-04-05T01:36:00Z"
        },
        {
            "role": "model",
            "content": "أرخص حاجة هي ...",
            "timestamp": "2026-04-05T01:36:02Z"
        }
    ]
}
```

---

### 7.7 — Delete Menu

| Field | Value |
|-------|-------|
| **Method** | `DELETE` |
| **URL** | `{{base_url}}/api/v1/menus/{menu_id}` |
| **Body** | None |

Replace `{menu_id}` with the actual ID.

**Expected Response (200):**
```json
{
    "menu_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "deleted"
}
```

**What to verify:**
- DBeaver → `menus` table → row removed
- DBeaver → `menu_items` table → related rows removed (cascade)
- Qdrant dashboard → points for this menu_id removed

---

## Step 9: Test Context Compaction

Context compaction automatically kicks in after every 5 invocations (messages).
To test this:

1. **Send 6+ messages** to the same session (step 7.5 with same `session_id`)
2. After the 5th message, check DBeaver:
   - Look at the ADK events table for your session
   - You should see a **compaction event** — a row where the `actions` column
     contains `compacted_content` with a summary of the first 5 messages
3. **Send message #6** — the agent should still understand context from messages 1-5
   even though the LLM only sees the compaction summary + messages 5-6

**Example test sequence:**
```
Message 1: "ايه الأكلات اللي عندكم؟"
Message 2: "ايه اغلى حاجة؟"
Message 3: "وايه ارخص حاجة؟"
Message 4: "فيه حلويات؟"
Message 5: "طيب ايه المشروبات؟"    ← Compaction triggers here
Message 6: "ايه اول حاجة سألت عنها؟" ← Should recall from compaction summary
```

**What to see in DBeaver (events table):**

| event # | author | content (summary) | actions |
|---------|--------|-------------------|---------|
| 1-10 | user/agent | Original messages | normal |
| 11 | system | — | `compaction: {compacted_content: "Summary of messages 1-5..."}` |
| 12+ | user/agent | New messages | normal |

> The old events (1-10) still exist in the DB but the LLM won't see them.
> It will only see: compaction summary + overlap (message 5) + messages 6+.

---

## Step 10: Test Session TTL Cleanup

The session cleanup loop runs every 60 minutes by default (configurable via
`SESSION_CLEANUP_INTERVAL_MINUTES`). To test it quickly:

### Quick Test (override TTL for testing)

1. **Temporarily set a short TTL** in `src/.env`:
   ```env
   SESSION_TTL_HOURS=0
   SESSION_CLEANUP_INTERVAL_MINUTES=1
   ```

2. **Restart the server**:
   ```bash
   uv run uvicorn src.main:app --reload --port 5000
   ```

3. **Create a chat session** (step 7.5) — note the `session_id`

4. **Wait 2 minutes** for the cleanup loop to run

5. **Check server logs** — you should see:
   ```
   INFO | Session abc123 for user test-user-1 expired (last activity: ...)
   INFO | Cleaning up session abc123 — summary: Recent conversation:..., user_state keys: ['user:last_session_summary']
   INFO | Session cleanup complete: 1 sessions removed
   ```

6. **Verify in DBeaver:**
   - The old session row should be **deleted** from the ADK sessions table
   - All associated events should be **cascade deleted**

7. **Send a new message** with the same `user_id` (step 7.5, no session_id):
   ```json
   {
       "message": "مرحبا",
       "menu_id": "...",
       "user_id": "test-user-1"
   }
   ```
   - A **new session** should be created (new `session_id`)
   - The `user:last_session_summary` key is carried over as user-level state

8. **Reset TTL back to 24 hours** in `src/.env`:
   ```env
   SESSION_TTL_HOURS=24
   SESSION_CLEANUP_INTERVAL_MINUTES=60
   ```

### What Happens Under the Hood

```
Session Lifecycle with TTL:

User chats → Session created → Events accumulate
                                    ↓
                         Every 5 msgs: compaction runs
                         (old events summarized, LLM stays fast)
                                    ↓
                         24h of inactivity passes...
                                    ↓
                         Cleanup loop detects expired session
                                    ↓
                         1. Extract last compaction summary
                         2. Extract user:-prefixed state keys
                         3. DELETE old session (CASCADE events)
                         4. user:last_session_summary saved
                                    ↓
                         User returns → new session auto-created
                         → user: state carried over by ADK
```

---

## Step 11: Persistence Verification

1. **Stop the server** (Ctrl+C)
2. **Restart the server**: `uv run uvicorn src.main:app --reload --port 5000`
3. **Call GET /api/v1/menus** → menus should still be there (PostgreSQL)
4. **Call POST /api/v1/chat** with the same `user_id` and `session_id` →
   should continue the conversation (session persisted in PostgreSQL)
5. Menus survive restarts (PostgreSQL)
6. Vectors survive restarts (Qdrant persistent volume)
7. Chat sessions survive restarts (PostgreSQL via DatabaseSessionService)

---

## Troubleshooting

### "Connection refused" on startup
- Make sure Docker containers are running: `docker compose -f docker/docker-compose.yml ps`
- Wait 10-15 seconds after starting Docker for PostgreSQL to initialize
- PostgreSQL is on port **5423** (not default 5432)

### "Kaggle Error" on menu upload
- Make sure your Kaggle notebook is running and the ngrok URL is active
- Update `KAGGLE_OCR_URL` in `src/.env` if the URL changed

### "OpenAI error" on chat or upload
- Verify your `OPENAI_API_KEY` in `src/.env` is correct
- Check you have access to `gpt-5` and `text-embedding-3-small`

### "No items found" after upload
- The image may be unclear or not a menu
- Try with a clearer menu image

### Session not found after TTL cleanup
- This is expected! The old session was deleted
- Send a new message without `session_id` → a new session will be created
- The `user:last_session_summary` carries context forward

### Resetting everything
```bash
# Stop everything
docker compose -f docker/docker-compose.yml down -v --remove-orphans

# Restart fresh
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml down -v # jsut cleaning up old containers
```
