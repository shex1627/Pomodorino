# Pomodorino Backend

## Quick Start - Testing Discovery Agent

### 1. Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...your_key_here

# Optional (for YouTube video search)
YOUTUBE_API_KEY=...your_key_here

# Development
DEBUG=True
LOG_LEVEL=INFO
```

**Getting API Keys:**
- **Anthropic**: https://console.anthropic.com/ (Required for testing)
- **YouTube**: https://console.cloud.google.com/ → Enable YouTube Data API v3 (Optional)

### 3. Run Discovery Agent Test

```bash
python tests/test_discovery_agent.py
```

This will test the Discovery Agent with 3 sample interests:
1. Learning to cook beef cuts
2. AI agent memory management
3. Plumbing basics

### Expected Output

The test will:
1. Analyze each interest with LLM
2. Generate search queries
3. Search YouTube for relevant videos (if API key provided)
4. Suggest 3-5 learning "Things" with task breakdowns
5. Save results to `tests/discovery_result_N.json`

### Sample Output

```
🎯 INTEREST: Learn to cook different parts of beef (prefer dishes under 15 min)
   Priority: 7/10

📊 ANALYSIS:
   Difficulty: beginner
   Key Topics: beef cuts, quick cooking methods, meat selection
   Learning Goals:
     - Identify different beef cuts
     - Learn quick cooking techniques
     - Understand which cuts work best for fast meals

📹 RESOURCES FOUND: 8
   - [video] Beef Cuts Explained by a Butcher
     URL: https://youtube.com/watch?v=...
     Duration: 12 min

📚 SUGGESTED THINGS: 5
   📖 Understanding Beef Cuts - Quick Reference
      Type: learning_material
      Total Time: 15 min
      Tasks: 2
      Tasks outline:
         1. Read about primary cuts (8 min)
         2. Learn secondary cuts (7 min)
```

## Project Structure

```
backend/
├── app/
│   ├── agents/
│   │   ├── base_agent.py          # Base class for all agents
│   │   └── discovery_agent.py     # Content discovery agent
│   ├── core/
│   │   └── config.py               # Configuration management
│   ├── models/                     # Database models (coming soon)
│   └── services/                   # Business logic (coming soon)
├── tests/
│   └── test_discovery_agent.py    # Discovery agent test script
├── .env.example                    # Example environment file
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Next Steps

After validating the Discovery Agent:
1. Implement other agents (Generation, Decomposition, Quiz, Recommendation)
2. Set up database with PostgreSQL
3. Build FastAPI endpoints
4. Create agent orchestrator

## Troubleshooting

**Import errors:**
```bash
# Make sure you're in the backend directory and venv is activated
cd backend
source venv/bin/activate
```

**Missing API key error:**
```
pydantic_core._pydantic_core.ValidationError: ANTHROPIC_API_KEY field required
```
→ Create `.env` file with your Anthropic API key

**YouTube API quota exceeded:**
→ The agent will still work, just without video search results

## Development

**Run with debug logging:**
```bash
LOG_LEVEL=DEBUG python tests/test_discovery_agent.py
```

**Test with single interest:**
Edit `test_discovery_agent.py` and comment out test cases you don't want to run.
