# Quick Setup Guide

## Step 1: Create .env File

You need to create a `.env` file with your OpenAI API key. 

**If you don't have an OpenAI API key yet:**
1. Go to https://platform.openai.com
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-`)

**Create the .env file:**

```bash
cp env.example .env
```

Then edit `.env` and replace `sk-your-api-key-here` with your actual API key.

Or create it manually with:

```
OPENAI_API_KEY=sk-your-actual-key-here
NPC_MANAGER_URL=http://localhost:8001
TICKETING_API_URL=http://localhost:8000
TICKETING_DB_PATH=database/ticketing.db
NPC_MANAGER_DB_PATH=database/npc_manager.db
```

## Step 2: Install Dependencies

With the virtual environment activated:

```bash
# Activate venv (if not already activated)
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Initialize Databases

```bash
python scripts/setup_db.py
```

This creates the databases and seeds them with test data.

## Step 4: Run the Demo

```bash
python scripts/demo.py
```

The demo will walk you through all 5 acts!

---

## Alternative: Run Services Manually

If you want to run services separately:

**Terminal 1 - Ticketing API:**
```bash
source venv/bin/activate
python -m uvicorn ticketing_api.main:app --port 8000
```

**Terminal 2 - NPC Manager:**
```bash
source venv/bin/activate
python -m uvicorn npc_manager.main:app --port 8001
```

**Terminal 3 - Agent:**
```bash
source venv/bin/activate
python -m agent.agent
```

