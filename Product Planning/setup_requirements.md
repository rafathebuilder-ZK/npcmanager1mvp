# Setup Requirements Summary

## What Was Added to the Plan

The implementation plan has been updated to include all necessary setup steps for a fresh machine with minimal setup.

## External Services Required

### ✅ OpenAI API Key (Only External Service)

**Required**: Yes  
**Cost**: Pay-as-you-go (~$0.01-0.10 for MVP demo)  
**Setup Time**: ~5 minutes  
**Steps**:
1. Go to https://platform.openai.com
2. Sign up (free account works)
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-`)
6. Add to `.env` file when we create it: `OPENAI_API_KEY=sk-...`

**Why**: The LangChain agent needs an LLM to reason about which actions to take. OpenAI provides the API.

**Note**: This is the ONLY external service. Everything else runs locally on your machine.

## Local Prerequisites

### Required
- **Python 3.10+** - Check with `python3 --version`
- **Internet connection** - Only for installing packages and OpenAI API calls

### Optional
- Git (for version control)
- Code editor (you're using Cursor, so you're set!)

## New Setup Todos Added

The plan now includes these setup todos (to be executed first):

1. **Project Structure** - Create all directories
2. **Python Environment** - Verify Python, create virtual environment
3. **Requirements File** - List all Python dependencies
4. **Environment Config** - Create `.env.example` and `.env` files
5. **OpenAI API Key Setup** - Document the API key acquisition process
6. **README** - Complete setup instructions

## What Runs Locally

All of these run on your machine (no external services):
- ✅ Ticketing API (FastAPI on port 8000)
- ✅ NPC Manager (FastAPI on port 8001)
- ✅ SQLite databases (local files)
- ✅ Agent script (Python process)
- ✅ Demo script (Python process)

## Setup Order

When we implement, the order will be:

1. Create project structure
2. Set up Python virtual environment
3. Create requirements.txt
4. Install dependencies (`pip install -r requirements.txt`)
5. Create .env file with OpenAI API key
6. Then proceed with implementation

## Cost Estimate

- **OpenAI API**: ~$0.01-0.10 per demo run (depends on number of LLM calls)
- **Everything else**: Free (runs locally)

## Summary

**You need to get**: One OpenAI API key  
**You need installed**: Python 3.10+  
**Everything else**: We'll set up as part of implementation  

The plan is now complete with all setup steps included!

