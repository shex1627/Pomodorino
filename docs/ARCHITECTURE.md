# Pomodorino Technical Architecture

**Version:** 1.0
**Last Updated:** October 29, 2025
**Status:** Design Document

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [High-Level Architecture](#high-level-architecture)
4. [Backend Components](#backend-components)
5. [LLM Agent System](#llm-agent-system)
6. [Database Architecture](#database-architecture)
7. [API Layer Design](#api-layer-design)
8. [External Integrations](#external-integrations)
9. [Security & Authentication](#security--authentication)
10. [Deployment Architecture](#deployment-architecture)
11. [Monitoring & Observability](#monitoring--observability)
12. [Scalability Considerations](#scalability-considerations)

---

## System Overview

Pomodorino is a micro-learning platform that transforms fidget time into productive 5-10 minute learning sessions. The system consists of:

- **Backend API** (Python/FastAPI): Core business logic, LLM orchestration, data management
- **iOS App** (SwiftUI): User interface for task consumption and completion
- **LLM Agents**: Intelligent agents for content discovery, generation, and recommendations
- **Database Layer**: PostgreSQL for relational data, Vector DB for semantic search
- **External Services**: LLM APIs, YouTube API, cloud storage

### Core User Flows

```
1. Interest Creation Flow
   User → iOS App → API → Database
   └─> Stores interest with priority

2. Content Generation Flow
   User triggers generation → API → Agent Orchestrator
   └─> Content Discovery Agent → External APIs (YouTube, web search)
   └─> Generation Agent → LLM API → Generated content
   └─> Decomposition Agent → LLM API → Tasks breakdown
   └─> Quiz Agent → LLM API → Quiz questions
   └─> Store all in Database

3. Task Recommendation Flow
   User requests task → API → Recommendation Agent
   └─> Queries database (user history, priorities)
   └─> LLM analyzes patterns
   └─> Returns optimized task recommendation

4. Task Completion Flow
   User completes task → Takes quiz → API
   └─> Stores completion data
   └─> Updates user statistics
   └─> May trigger Action Item creation
```

---

## Architecture Principles

### 1. **Separation of Concerns**
- Clear boundaries between API, business logic, agents, and data layers
- Each LLM agent has a single responsibility
- No business logic in API routes

### 2. **Agent-First Design**
- LLM agents are first-class citizens
- Orchestrator pattern for complex multi-agent workflows
- Agents are stateless and composable

### 3. **Cost Optimization**
- Cache LLM outputs aggressively
- Use smaller/cheaper models for simple tasks
- Batch operations where possible

### 4. **Offline-First iOS Experience**
- Tasks cached locally after generation
- Sync when network available
- Graceful degradation

### 5. **Data-Driven Iteration**
- Extensive telemetry and logging
- A/B test framework ready
- User feedback loops

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         iOS App (SwiftUI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Interests│  │  Tasks   │  │  Quizzes │  │  Actions │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST API
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    API Gateway / Load Balancer               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend (Python)                   │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  API Routes  │  │   Services   │  │ Agent        │      │
│  │  (Endpoints) │─▶│  (Business   │─▶│ Orchestrator │      │
│  │              │  │   Logic)     │  │              │      │
│  └──────────────┘  └──────────────┘  └──────┬───────┘      │
│                                              │               │
│  ┌──────────────────────────────────────────▼──────────┐   │
│  │           LLM Agent System                          │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐     │   │
│  │  │ Discovery  │ │ Generation │ │Decomposition│     │   │
│  │  │   Agent    │ │   Agent    │ │   Agent    │     │   │
│  │  └────────────┘ └────────────┘ └────────────┘     │   │
│  │  ┌────────────┐ ┌────────────┐                     │   │
│  │  │    Quiz    │ │Recommendation│                   │   │
│  │  │   Agent    │ │   Agent    │                     │   │
│  │  └────────────┘ └────────────┘                     │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────┬──────────────────────┬─────────────────────────┘
             │                      │
    ┌────────▼────────┐    ┌────────▼────────┐
    │   PostgreSQL    │    │   Vector DB     │
    │   (Relational)  │    │  (Embeddings)   │
    └─────────────────┘    └─────────────────┘
             │
    ┌────────▼────────┐
    │  Redis Cache    │
    │  (Sessions,     │
    │   LLM outputs)  │
    └─────────────────┘

External Services:
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  OpenAI/       │  │  YouTube API   │  │  Cloud Storage │
│  Anthropic API │  │                │  │  (S3/R2)       │
└────────────────┘  └────────────────┘  └────────────────┘
```

---

## Backend Components

### 1. API Layer (`/app/api/`)

**Purpose:** HTTP request handling, validation, response formatting

**Structure:**
```
app/api/
├── v1/
│   ├── __init__.py
│   ├── interests.py      # Interest CRUD endpoints
│   ├── things.py         # Thing generation & management
│   ├── tasks.py          # Task retrieval & completion
│   ├── quizzes.py        # Quiz generation & attempts
│   ├── action_items.py   # Action item management
│   ├── recommendations.py # Task recommendation endpoint
│   └── stats.py          # User statistics & analytics
├── dependencies.py       # Dependency injection (auth, db)
├── middleware.py         # Request logging, CORS, rate limiting
└── errors.py            # Custom exception handlers
```

**Key Patterns:**
- **Dependency Injection** for database sessions, auth
- **Pydantic models** for request/response validation
- **Async/await** for all routes (non-blocking I/O)
- **Router prefixing** (`/api/v1/interests`)

**Example Route:**
```python
@router.post("/interests/{id}/generate-things")
async def generate_things(
    interest_id: UUID,
    count: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Generate Things from an Interest using LLM agents."""
    interest = await interest_service.get_by_id(db, interest_id, current_user.id)
    things = await agent_service.generate_things(interest, count)
    return {"things": things}
```

### 2. Service Layer (`/app/services/`)

**Purpose:** Business logic, orchestration, validation

**Structure:**
```
app/services/
├── __init__.py
├── interest_service.py    # Interest business logic
├── thing_service.py       # Thing management
├── task_service.py        # Task lifecycle
├── quiz_service.py        # Quiz generation & scoring
├── action_item_service.py # Action item tracking
├── recommendation_service.py # Task recommendation logic
├── agent_orchestrator.py  # Coordinates multiple agents
└── analytics_service.py   # User stats & insights
```

**Key Responsibilities:**
- Data validation beyond API layer
- Transaction management
- Multi-step workflows
- Error handling and retry logic
- Business rule enforcement

**Example Service:**
```python
class InterestService:
    def __init__(self, db: Session):
        self.db = db

    async def create(self, user_id: UUID, data: InterestCreate) -> Interest:
        """Create a new interest with validation."""
        # Validate priority range
        if not 1 <= data.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")

        # Check user's interest limit (if free tier)
        count = await self.count_user_interests(user_id)
        if count >= MAX_FREE_INTERESTS and not user.is_premium:
            raise LimitExceededError("Free tier limited to 5 interests")

        interest = Interest(
            user_id=user_id,
            description=data.description,
            priority=data.priority
        )
        self.db.add(interest)
        await self.db.commit()
        return interest
```

### 3. Agent System (`/app/agents/`)

**Purpose:** LLM-powered intelligent operations

See [LLM Agent System](#llm-agent-system) section below.

### 4. Database Layer (`/app/db/`)

**Purpose:** Database connections, models, migrations

**Structure:**
```
app/db/
├── __init__.py
├── session.py           # Database connection & session management
├── base.py              # SQLAlchemy declarative base
└── migrations/          # Alembic migration files
    └── versions/
```

See [Database Architecture](#database-architecture) section below.

### 5. Models (`/app/models/`)

**Purpose:** SQLAlchemy ORM models

**Structure:**
```
app/models/
├── __init__.py
├── user.py              # User model
├── interest.py          # Interest model
├── thing.py             # Thing model
├── task.py              # Task model
├── quiz.py              # Quiz & QuizAttempt models
├── action_item.py       # ActionItem model
└── task_completion.py   # TaskCompletion tracking
```

### 6. Core Utilities (`/app/core/`)

**Purpose:** Configuration, security, helpers

**Structure:**
```
app/core/
├── __init__.py
├── config.py            # Environment config (Pydantic Settings)
├── security.py          # JWT, password hashing
├── logger.py            # Logging configuration
└── exceptions.py        # Custom exceptions
```

---

## LLM Agent System

### Overview

The agent system is the intelligence layer that generates content, breaks down tasks, and makes recommendations. Each agent is specialized and stateless.

### Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Agent Orchestrator                          │
│  (Coordinates multi-agent workflows)                     │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────┬─────────┐
        │           │           │           │         │
┌───────▼──┐  ┌────▼────┐  ┌───▼─────┐  ┌─▼──────┐ ┌▼────────┐
│Discovery │  │Generation│  │Decomp.  │  │  Quiz  │ │Recommend│
│  Agent   │  │  Agent   │  │ Agent   │  │ Agent  │ │ Agent   │
└──────────┘  └──────────┘  └─────────┘  └────────┘ └─────────┘
     │             │              │            │          │
     └─────────────┴──────────────┴────────────┴──────────┘
                              │
                    ┌─────────▼─────────┐
                    │   LLM Provider    │
                    │  (OpenAI/Anthropic)│
                    └───────────────────┘
```

### Base Agent Class

```python
# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Any, Dict
import anthropic
from app.core.config import settings

class BaseAgent(ABC):
    """Base class for all LLM agents."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.cache_ttl = 3600  # 1 hour default

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's primary function."""
        pass

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Call LLM with prompt."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text

    async def _call_with_cache(self, cache_key: str, *args, **kwargs) -> str:
        """Call LLM with caching layer."""
        # Check Redis cache first
        cached = await redis.get(cache_key)
        if cached:
            return cached

        # Call LLM
        result = await self._call_llm(*args, **kwargs)

        # Cache result
        await redis.setex(cache_key, self.cache_ttl, result)
        return result
```

### 1. Content Discovery Agent

**Purpose:** Search for relevant online resources (YouTube videos, articles, tutorials)

**Input:**
```python
{
    "interest_description": "Learn to cook different parts of beef (dishes under 15 min)",
    "priority": 7,
    "count": 10  # How many Things to find
}
```

**Process:**
1. Analyze interest description with LLM to extract key topics
2. Generate search queries for different resource types
3. Call YouTube API with queries
4. Search for articles (web search API or curated sources)
5. Filter and rank results by relevance
6. Return structured resource list

**Output:**
```python
{
    "resources": [
        {
            "type": "video",
            "title": "Beef Cuts Explained by a Butcher",
            "url": "https://youtube.com/watch?v=...",
            "duration_minutes": 8,
            "relevance_score": 0.95
        },
        {
            "type": "article",
            "title": "Quick Beef Recipes Under 15 Minutes",
            "url": "https://...",
            "estimated_read_time": 7,
            "relevance_score": 0.88
        }
        # ... more resources
    ],
    "suggested_things": [
        {
            "title": "Understanding Beef Cuts - Quick Reference",
            "type": "learning_material",
            "resources": [...]
        }
    ]
}
```

**Implementation:**
```python
# app/agents/discovery_agent.py
class ContentDiscoveryAgent(BaseAgent):
    async def execute(self, input_data: Dict) -> Dict:
        interest = input_data["interest_description"]
        count = input_data.get("count", 10)

        # Step 1: Analyze interest with LLM
        analysis = await self._analyze_interest(interest)

        # Step 2: Generate search queries
        queries = await self._generate_search_queries(analysis)

        # Step 3: Search external sources (in parallel)
        results = await asyncio.gather(
            self._search_youtube(queries["video_queries"]),
            self._search_articles(queries["article_queries"]),
            self._search_tutorials(queries["tutorial_queries"])
        )

        # Step 4: Rank and filter
        ranked_resources = await self._rank_resources(results, analysis)

        # Step 5: Suggest Thing structures
        things = await self._suggest_things(ranked_resources, count)

        return {"resources": ranked_resources, "suggested_things": things}
```

### 2. Generation Agent

**Purpose:** Create original explanatory content when external resources are insufficient

**Input:**
```python
{
    "topic": "Understanding beef cuts - primary cuts",
    "target_duration_min": 8,
    "difficulty": "beginner",
    "format": "article"  # or "tutorial", "code_example", etc.
}
```

**Process:**
1. Construct specialized system prompt based on topic and format
2. Call LLM to generate content
3. Validate content length (should fit 5-10 min reading)
4. Format as markdown
5. Extract key concepts for quiz generation

**Output:**
```python
{
    "content": "# Understanding Beef Cuts: Primary Cuts\n\n## Introduction\n...",
    "format": "markdown",
    "estimated_read_time": 8,
    "key_concepts": [
        "Chuck comes from shoulder, good for slow cooking",
        "Rib section includes ribeye, high marbling",
        "Loin is most tender, includes tenderloin and strip",
        "Round is lean, from rear leg"
    ]
}
```

**Implementation:**
```python
class GenerationAgent(BaseAgent):
    async def execute(self, input_data: Dict) -> Dict:
        topic = input_data["topic"]
        duration = input_data["target_duration_min"]
        difficulty = input_data.get("difficulty", "beginner")

        # Build system prompt
        system_prompt = self._build_system_prompt(difficulty, duration)

        # Generate content
        content = await self._call_llm(
            system_prompt=system_prompt,
            user_message=f"Create educational content about: {topic}",
            temperature=0.7
        )

        # Extract key concepts for quiz
        key_concepts = await self._extract_concepts(content)

        return {
            "content": content,
            "format": "markdown",
            "estimated_read_time": duration,
            "key_concepts": key_concepts
        }

    def _build_system_prompt(self, difficulty: str, duration: int) -> str:
        word_count = duration * 150  # ~150 words per minute
        return f"""You are an expert educational content creator.

Create clear, engaging content for a {difficulty}-level learner.
Target length: {word_count} words (~{duration} minutes to read).

Requirements:
- Use simple, clear language
- Break into digestible sections with headers
- Include practical examples
- Use markdown formatting
- Focus on actionable information
- Make it interesting and engaging

Output format: Markdown
"""
```

### 3. Decomposition Agent

**Purpose:** Break down topics/projects into 5-10 minute tasks

**Input:**
```python
{
    "thing": {
        "title": "Building a Personal Memory System Project",
        "description": "Multi-phase project to build AI agent memory",
        "type": "project",
        "resources": [...]
    },
    "target_task_duration_min": 8
}
```

**Process:**
1. Analyze the Thing and its complexity
2. Determine logical learning progression
3. Break into sequential tasks
4. Estimate duration for each task
5. Identify which tasks should have Action Items
6. Generate task descriptions and content pointers

**Output:**
```python
{
    "tasks": [
        {
            "order": 1,
            "title": "Design your memory architecture",
            "description": "Whiteboard session planning memory system components",
            "estimated_time_min": 10,
            "content_type": "generated",  # or "video_link", "article_link"
            "prerequisites": [],
            "has_action_item": true,
            "action_item_suggestion": {
                "title": "Create architecture diagram",
                "estimated_hours": 1,
                "verification_type": "photo"
            }
        },
        {
            "order": 2,
            "title": "Research embedding models",
            "description": "Compare OpenAI, Cohere, sentence-transformers",
            "estimated_time_min": 8,
            "content_type": "generated",
            "prerequisites": [1],
            "has_action_item": true
        }
        # ... more tasks
    ],
    "total_tasks": 12,
    "estimated_total_time_hours": 2.5
}
```

**Implementation:**
```python
class DecompositionAgent(BaseAgent):
    async def execute(self, input_data: Dict) -> Dict:
        thing = input_data["thing"]
        target_duration = input_data.get("target_task_duration_min", 8)

        # Analyze complexity
        complexity_analysis = await self._analyze_complexity(thing)

        # Generate task breakdown
        system_prompt = f"""You are an expert at breaking down learning topics
        into bite-sized tasks. Each task should take {target_duration} ± 2 minutes.

        Create a logical learning progression from beginner to competent.
        Identify tasks that should lead to hands-on action items.

        Return tasks as a JSON array with: order, title, description,
        estimated_time_min, prerequisites, has_action_item.
        """

        user_message = f"""Break down this learning topic into micro-tasks:

Title: {thing['title']}
Description: {thing['description']}
Type: {thing['type']}
Complexity: {complexity_analysis['level']}

Available resources:
{json.dumps(thing.get('resources', []), indent=2)}
"""

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.5  # Lower temp for structured output
        )

        tasks = json.loads(response)

        # Validate and adjust durations
        tasks = self._validate_tasks(tasks, target_duration)

        return {
            "tasks": tasks,
            "total_tasks": len(tasks),
            "estimated_total_time_hours": sum(t["estimated_time_min"] for t in tasks) / 60
        }
```

### 4. Quiz Generation Agent

**Purpose:** Create multiple-choice questions based on task content

**Input:**
```python
{
    "task": {
        "title": "Learn about primary beef cuts",
        "content": "# Understanding Beef Cuts...",
        "key_concepts": [...]
    },
    "num_questions": 4,
    "difficulty": "beginner"
}
```

**Process:**
1. Analyze task content
2. Identify testable concepts
3. Generate questions with 4 options each
4. Ensure one correct answer, three plausible distractors
5. Write explanations for correct answers
6. Validate question clarity

**Output:**
```python
{
    "questions": [
        {
            "question_text": "Which beef cut comes from the shoulder and is best for slow cooking?",
            "options": ["Ribeye", "Chuck", "Tenderloin", "Sirloin"],
            "correct_answer": "B",
            "explanation": "Chuck comes from the shoulder and has connective tissue ideal for braising."
        },
        # ... 3 more questions
    ]
}
```

**Implementation:**
```python
class QuizGenerationAgent(BaseAgent):
    async def execute(self, input_data: Dict) -> Dict:
        task = input_data["task"]
        num_q = input_data.get("num_questions", 4)
        difficulty = input_data.get("difficulty", "beginner")

        system_prompt = f"""You are an expert quiz creator for educational content.

Create {num_q} multiple-choice questions at {difficulty} level.

Requirements:
- Each question tests understanding, not just memorization
- 4 options per question (A, B, C, D)
- One correct answer
- Three plausible but incorrect distractors
- Include explanation for why the answer is correct
- Questions should be clear and unambiguous

Return JSON array of questions.
"""

        user_message = f"""Create a quiz for this educational content:

Title: {task['title']}

Content:
{task['content']}

Key concepts to test:
{json.dumps(task.get('key_concepts', []), indent=2)}
"""

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.6
        )

        questions = json.loads(response)

        # Validate question structure
        questions = self._validate_questions(questions)

        return {"questions": questions}
```

### 5. Recommendation Agent

**Purpose:** Suggest optimal next task based on user context

**Input:**
```python
{
    "user_id": "uuid-123",
    "filter": "high_priority",  # or "any", "topic", etc.
    "interest_id": "uuid-456",  # optional
    "context": {
        "recent_completions": [...],
        "quiz_scores": [...],
        "time_of_day": "morning",
        "available_time_min": 10
    }
}
```

**Process:**
1. Fetch user's incomplete tasks
2. Apply filters (priority, topic, etc.)
3. Consider:
   - Prerequisites (don't suggest Task 2 if Task 1 incomplete)
   - Recent activity (avoid repetition)
   - Quiz performance (if struggling, suggest easier tasks)
   - Time of day patterns (user preference learning)
4. Score and rank candidates
5. Return top recommendation with reasoning

**Output:**
```python
{
    "recommended_task": {
        "task_id": "uuid-789",
        "title": "Learn about short-term vs long-term memory",
        "estimated_time_min": 8,
        "interest_title": "AI agent memory management",
        "interest_priority": 10
    },
    "reasoning": "High-priority interest, prerequisite for other tasks, matches your available time",
    "alternatives": [...]  # 2-3 backup suggestions
}
```

**Implementation:**
```python
class RecommendationAgent(BaseAgent):
    async def execute(self, input_data: Dict) -> Dict:
        user_id = input_data["user_id"]
        filter_type = input_data.get("filter", "any")
        context = input_data.get("context", {})

        # Fetch candidate tasks from database
        candidates = await self._fetch_candidates(
            user_id,
            filter_type,
            input_data.get("interest_id")
        )

        # Score each candidate
        scored = []
        for task in candidates:
            score = await self._score_task(task, context)
            scored.append((task, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Get top recommendation
        top_task, top_score = scored[0]

        # Generate reasoning
        reasoning = await self._generate_reasoning(top_task, context, top_score)

        return {
            "recommended_task": top_task,
            "reasoning": reasoning,
            "alternatives": [t for t, s in scored[1:4]]
        }

    async def _score_task(self, task: Dict, context: Dict) -> float:
        """Score a task based on multiple factors."""
        score = 0.0

        # Priority weight (0-1)
        score += task["interest_priority"] / 10 * 0.3

        # Prerequisite satisfaction (0 or 1)
        if self._prerequisites_met(task):
            score += 0.25
        else:
            return 0  # Can't recommend if prereqs not met

        # Recency (avoid recently completed topics)
        recency_penalty = self._calculate_recency_penalty(task, context)
        score -= recency_penalty * 0.15

        # Time fit (how well task duration fits available time)
        time_fit = self._calculate_time_fit(task, context.get("available_time_min", 10))
        score += time_fit * 0.2

        # Quiz performance factor (if user struggling, recommend easier)
        quiz_factor = self._calculate_quiz_factor(task, context.get("quiz_scores", []))
        score += quiz_factor * 0.1

        return score
```

### Agent Orchestrator

**Purpose:** Coordinate multi-agent workflows

```python
# app/agents/orchestrator.py
class AgentOrchestrator:
    def __init__(self):
        self.discovery = ContentDiscoveryAgent()
        self.generation = GenerationAgent()
        self.decomposition = DecompositionAgent()
        self.quiz = QuizGenerationAgent()
        self.recommendation = RecommendationAgent()

    async def generate_complete_things(
        self,
        interest: Interest,
        count: int
    ) -> List[Thing]:
        """Full workflow: discovery → generation → decomposition → quiz."""

        # Step 1: Discover resources
        discovery_result = await self.discovery.execute({
            "interest_description": interest.description,
            "priority": interest.priority,
            "count": count
        })

        things = []
        for suggested_thing in discovery_result["suggested_things"]:
            # Step 2: Generate content for tasks that need it
            tasks_with_content = []
            for task_outline in suggested_thing["task_outlines"]:
                if task_outline["needs_generation"]:
                    content = await self.generation.execute({
                        "topic": task_outline["topic"],
                        "target_duration_min": task_outline["duration"],
                        "difficulty": interest.difficulty_level
                    })
                    task_outline["content"] = content

                tasks_with_content.append(task_outline)

            # Step 3: Create Thing object
            thing = Thing(
                interest_id=interest.id,
                title=suggested_thing["title"],
                type=suggested_thing["type"]
            )

            # Step 4: Create Tasks
            for task_data in tasks_with_content:
                task = Task(
                    thing_id=thing.id,
                    title=task_data["title"],
                    content=task_data.get("content", {}).get("content"),
                    estimated_time_min=task_data["duration"]
                )

                # Step 5: Generate quiz for each task
                if task.content:
                    quiz_result = await self.quiz.execute({
                        "task": {
                            "title": task.title,
                            "content": task.content,
                            "key_concepts": task_data.get("content", {}).get("key_concepts", [])
                        },
                        "num_questions": 4
                    })

                    quiz = Quiz(
                        task_id=task.id,
                        questions=quiz_result["questions"]
                    )
                    task.quiz = quiz

                thing.tasks.append(task)

            things.append(thing)

        return things
```

---

## Database Architecture

### Technology Stack

- **Primary Database:** PostgreSQL 15+
  - ACID compliance
  - JSONB support for flexible schemas
  - Full-text search capabilities
  - Mature, reliable, well-documented

- **Vector Database:** Pinecone or pgvector extension
  - For semantic search of generated content
  - Future: find similar tasks across users

- **Cache Layer:** Redis
  - Session storage
  - LLM output caching
  - Rate limiting counters
  - Real-time analytics

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Interests table
CREATE TABLE interests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    priority INTEGER CHECK (priority >= 1 AND priority <= 10),
    status VARCHAR(20) DEFAULT 'active', -- active, archived
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_priority (user_id, priority DESC),
    INDEX idx_user_status (user_id, status)
);

-- Things table
CREATE TABLE things (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interest_id UUID NOT NULL REFERENCES interests(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    type VARCHAR(50) NOT NULL, -- learning_material, recipe, project, tutorial
    estimated_time_min INTEGER,
    task_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'not_started', -- not_started, in_progress, completed
    metadata JSONB, -- sources, tags, etc.
    generated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_interest (interest_id),
    INDEX idx_status (status)
);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thing_id UUID NOT NULL REFERENCES things(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    estimated_time_min INTEGER,
    content TEXT, -- Markdown content
    content_type VARCHAR(50), -- text, video_link, article_link, code
    external_links JSONB, -- Array of links
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    notes TEXT,
    actual_time_min INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_thing_order (thing_id, order_index),
    INDEX idx_completed (completed, completed_at)
);

-- Action Items table
CREATE TABLE action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL, -- nullable
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    estimated_time_hours DECIMAL(5,2),
    verification_type VARCHAR(50), -- photo, screenshot, link, text
    verification_data TEXT, -- URL or text content
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    tags JSONB,
    INDEX idx_user_completed (user_id, completed),
    INDEX idx_task (task_id)
);

-- Quizzes table
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    questions JSONB NOT NULL, -- Array of question objects
    generated_at TIMESTAMP DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    UNIQUE (task_id, version)
);

-- Quiz Attempts table
CREATE TABLE quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    answers JSONB NOT NULL, -- User's selected answers
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT NOW(),
    time_taken_seconds INTEGER,
    INDEX idx_user_task (user_id, task_id),
    INDEX idx_quiz (quiz_id)
);

-- Task Completions tracking table
CREATE TABLE task_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed_at TIMESTAMP DEFAULT NOW(),
    actual_time_min INTEGER,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT,
    INDEX idx_user_date (user_id, completed_at DESC),
    INDEX idx_task (task_id)
);
```

### Database Indexes Strategy

**Performance-critical queries:**
1. Get user's interests ordered by priority
2. Get incomplete tasks for a user
3. Get quiz attempts for analytics
4. Track completion history

**Indexes created:**
- Composite indexes on foreign keys + frequently filtered columns
- Descending indexes on timestamps for recent-first queries
- Partial indexes for common WHERE conditions

### Database Migrations

Using **Alembic** for schema versioning:

```bash
# Initialize
alembic init app/db/migrations

# Create migration
alembic revision --autogenerate -m "Add quizzes table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## API Layer Design

### API Versioning Strategy

- **URL-based versioning:** `/api/v1/interests`
- Start with v1, increment for breaking changes
- Maintain backward compatibility within version

### Request/Response Patterns

**Standard Response Format:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2025-10-29T10:00:00Z",
    "request_id": "uuid-123"
  }
}
```

**Error Response Format:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Priority must be between 1 and 10",
    "details": {
      "field": "priority",
      "value": 15
    }
  },
  "meta": {
    "timestamp": "2025-10-29T10:00:00Z",
    "request_id": "uuid-123"
  }
}
```

### Authentication Flow

**JWT-based authentication:**

```
1. POST /api/v1/auth/register
   → Returns access_token + refresh_token

2. POST /api/v1/auth/login
   → Returns access_token + refresh_token

3. All subsequent requests:
   Headers: { Authorization: "Bearer <access_token>" }

4. POST /api/v1/auth/refresh
   Body: { refresh_token: "..." }
   → Returns new access_token

5. POST /api/v1/auth/logout
   → Invalidates refresh_token
```

**Token Details:**
- Access token: 15-minute expiry
- Refresh token: 30-day expiry
- Stored in httpOnly cookies (web) or secure storage (iOS)

### Rate Limiting

**Per-tier limits:**
```python
RATE_LIMITS = {
    "free": {
        "requests_per_minute": 30,
        "thing_generations_per_day": 20,
        "quiz_attempts_per_day": 100
    },
    "premium": {
        "requests_per_minute": 120,
        "thing_generations_per_day": -1,  # unlimited
        "quiz_attempts_per_day": -1
    }
}
```

**Implementation:** Redis-based sliding window

### Pagination

**Cursor-based pagination for large lists:**
```
GET /api/v1/tasks/history?cursor=uuid-123&limit=20

Response:
{
  "data": [...],
  "pagination": {
    "next_cursor": "uuid-456",
    "has_more": true
  }
}
```

---

## External Integrations

### 1. LLM Provider (Anthropic/OpenAI)

**Primary:** Anthropic Claude
**Fallback:** OpenAI GPT-4

**Configuration:**
```python
LLM_CONFIG = {
    "primary_provider": "anthropic",
    "fallback_provider": "openai",
    "models": {
        "anthropic": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4-turbo-preview"
    },
    "timeout_seconds": 30,
    "max_retries": 3
}
```

**Error Handling:**
- Retry with exponential backoff
- Automatic failover to backup provider
- Log all LLM errors for debugging

### 2. YouTube API

**Purpose:** Search for educational videos

**Endpoints used:**
- `search.list` - Search videos
- `videos.list` - Get video details (duration, description)

**Rate Limits:**
- 10,000 quota units per day (free tier)
- 1 search = 100 units → 100 searches/day
- Cache results aggressively

### 3. Cloud Storage (AWS S3 / Cloudflare R2)

**Purpose:** Store verification photos/screenshots

**Strategy:**
- Pre-signed URLs for direct uploads from iOS
- Image compression before storage
- CDN for fast retrieval
- Auto-delete after action item completion (optional)

### 4. Analytics (Mixpanel / PostHog)

**Events tracked:**
- User registration
- Interest created
- Thing generated
- Task completed
- Quiz taken (with score)
- Action item created/completed

---

## Security & Authentication

### Authentication Strategy

- **JWT tokens** for stateless auth
- **Refresh token rotation** for security
- **Password hashing:** bcrypt with salt rounds = 12

### Authorization

**Role-based access control (future):**
- User (default)
- Premium User
- Admin

**Resource ownership validation:**
```python
async def verify_ownership(
    user_id: UUID,
    resource_id: UUID,
    resource_type: str,
    db: Session
):
    """Ensure user owns the resource."""
    # Example: user trying to complete someone else's task
    if resource_type == "task":
        task = await db.get(Task, resource_id)
        if task.thing.interest.user_id != user_id:
            raise PermissionDeniedError()
```

### Data Protection

- **Encryption at rest:** Database-level encryption
- **Encryption in transit:** TLS 1.3 for all API calls
- **PII handling:** Email hashed in logs, no sensitive data in analytics

### API Security

- **CORS:** Strict origin validation
- **CSRF:** Token-based protection for web
- **SQL Injection:** Parameterized queries (SQLAlchemy ORM)
- **XSS:** Input sanitization, output encoding

---

## Deployment Architecture

### Infrastructure

**Cloud Provider:** AWS (can migrate to others)

```
┌─────────────────────────────────────────────────┐
│              Route 53 (DNS)                      │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│        CloudFront CDN (Static Assets)            │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│     Application Load Balancer (ALB)              │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
┌────────▼────────┐  ┌───────▼────────┐
│  ECS Fargate    │  │  ECS Fargate   │
│  (FastAPI App)  │  │  (FastAPI App) │
│  Container 1    │  │  Container 2   │
└────────┬────────┘  └───────┬────────┘
         │                   │
         └─────────┬─────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐  ┌──────▼─────┐  ┌────▼────┐
│  RDS   │  │   Redis    │  │   S3    │
│ Postgres│  │ ElastiCache│  │ Storage │
└────────┘  └────────────┘  └─────────┘
```

### Container Strategy

**Docker multi-stage build:**
```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY ./app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

**Environment-specific configs:**
- `dev` - Local development
- `staging` - Pre-production testing
- `production` - Live environment

**Managed via:**
- AWS Secrets Manager for sensitive values
- Environment variables for non-sensitive config

### CI/CD Pipeline

**GitHub Actions workflow:**
```yaml
1. On push to main:
   - Run tests (pytest)
   - Run linting (ruff, mypy)
   - Build Docker image
   - Push to ECR (Elastic Container Registry)

2. On tag (e.g., v1.0.0):
   - Deploy to staging
   - Run integration tests
   - Manual approval gate
   - Deploy to production
```

---

## Monitoring & Observability

### Logging Strategy

**Structured logging with Python's `structlog`:**
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "task_completed",
    user_id=user.id,
    task_id=task.id,
    duration_min=8,
    quiz_score=0.75
)
```

**Log levels:**
- DEBUG: Development debugging
- INFO: Normal operations, key events
- WARNING: Recoverable issues
- ERROR: Failures requiring attention
- CRITICAL: System-level failures

**Log aggregation:** CloudWatch Logs or Datadog

### Metrics

**Application metrics (via Prometheus):**
- Request latency (p50, p95, p99)
- Request rate
- Error rate
- LLM call duration
- LLM cost per request
- Database query time
- Cache hit rate

**Business metrics:**
- Tasks completed per day
- Quiz average score
- Action items created/completed
- User retention (DAU, WAU, MAU)
- Premium conversion rate

### Alerting

**Critical alerts:**
- Error rate > 5% for 5 minutes
- API latency p95 > 2 seconds
- Database connection pool exhausted
- LLM API failures > 10% for 5 minutes

**Delivery:** PagerDuty or AWS SNS → Email/Slack

### Tracing

**Distributed tracing with OpenTelemetry:**
- Trace requests across API → Service → Agent → LLM
- Identify bottlenecks
- Debug production issues

---

## Scalability Considerations

### Horizontal Scaling

- **Stateless FastAPI instances** - Scale ECS tasks based on CPU/memory
- **Database read replicas** - For analytics queries
- **Redis cluster** - For high-throughput caching

### Performance Optimizations

1. **Caching Strategy:**
   - LLM outputs cached for 1 hour
   - Database queries cached in Redis
   - CDN for static assets

2. **Database Optimizations:**
   - Connection pooling (SQLAlchemy)
   - Query optimization (EXPLAIN ANALYZE)
   - Materialized views for analytics

3. **Async/Await:**
   - All I/O operations are async
   - Non-blocking LLM calls
   - Parallel agent execution where possible

### Cost Optimization

**LLM Cost Control:**
- Use cheaper models for simple tasks (Haiku vs Sonnet)
- Aggressive caching
- Batch API calls where possible
- Monitor cost per user

**Estimated Costs (at 10K MAU):**
- LLM API: $500-1000/month
- Infrastructure (AWS): $300-500/month
- Database: $100-200/month
- Total: ~$1000-1700/month

---

## Technology Stack Summary

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Backend | Python 3.11 + FastAPI | Fast, async, type-safe, great for LLM integration |
| Database | PostgreSQL 15 | Reliable, JSONB support, full-text search |
| Cache | Redis | Fast, simple, mature |
| Vector DB | pgvector or Pinecone | Semantic search capabilities |
| LLM | Anthropic Claude | Best reasoning, good for content generation |
| Auth | JWT | Stateless, scalable |
| Deployment | AWS ECS Fargate | Serverless containers, auto-scaling |
| CI/CD | GitHub Actions | Native integration, free for open source |
| Monitoring | CloudWatch + Prometheus | AWS native + industry standard |
| iOS | SwiftUI | Modern, declarative, native performance |

---

## Next Steps

1. ✅ Complete architecture design (this document)
2. ⬜ Set up development environment
3. ⬜ Initialize FastAPI project structure
4. ⬜ Implement database models and migrations
5. ⬜ Build base agent classes
6. ⬜ Implement first agent (Generation Agent)
7. ⬜ Create core API endpoints (Interests, Things, Tasks)
8. ⬜ Build agent orchestrator
9. ⬜ Add authentication & authorization
10. ⬜ Write tests (unit + integration)

---

## Document Revision History

- **v1.0** - October 29, 2025 - Initial architecture design
- Last updated: October 29, 2025
