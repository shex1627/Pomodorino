"""Test script for Recommendation Agent."""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.recommendation_agent import RecommendationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock user data representing a realistic learning state
MOCK_USER_STATE = {
    "interests": [
        {
            "interest_id": "int-1",
            "description": "Learn to cook different parts of beef",
            "priority": 7,
            "things": [
                {
                    "thing_id": "thing-1",
                    "title": "Understanding Beef Cuts",
                    "type": "learning_material",
                    "tasks": [
                        {
                            "task_id": "task-1-1",
                            "order": 1,
                            "title": "Learn about primary beef cuts",
                            "estimated_time_min": 8,
                            "completed": True,  # Already done
                            "prerequisites": []
                        },
                        {
                            "task_id": "task-1-2",
                            "order": 2,
                            "title": "Learn about secondary cuts",
                            "estimated_time_min": 7,
                            "completed": False,
                            "prerequisites": [1]
                        }
                    ]
                },
                {
                    "thing_id": "thing-2",
                    "title": "Pan-Seared Steak Techniques",
                    "type": "tutorial",
                    "tasks": [
                        {
                            "task_id": "task-2-1",
                            "order": 1,
                            "title": "Touch test and timing practice",
                            "estimated_time_min": 10,
                            "completed": False,
                            "prerequisites": []
                        }
                    ]
                }
            ]
        },
        {
            "interest_id": "int-2",
            "description": "AI agent memory management",
            "priority": 10,
            "things": [
                {
                    "thing_id": "thing-3",
                    "title": "Memory Types in AI Agents",
                    "type": "learning_material",
                    "tasks": [
                        {
                            "task_id": "task-3-1",
                            "order": 1,
                            "title": "Understand short-term vs long-term memory",
                            "estimated_time_min": 8,
                            "completed": False,
                            "prerequisites": []
                        },
                        {
                            "task_id": "task-3-2",
                            "order": 2,
                            "title": "Learn about vector embeddings",
                            "estimated_time_min": 9,
                            "completed": False,
                            "prerequisites": [1]
                        }
                    ]
                },
                {
                    "thing_id": "thing-4",
                    "title": "LangChain Memory Modules",
                    "type": "tutorial",
                    "tasks": [
                        {
                            "task_id": "task-4-1",
                            "order": 1,
                            "title": "Explore ConversationBufferMemory",
                            "estimated_time_min": 8,
                            "completed": False,
                            "prerequisites": []
                        }
                    ]
                }
            ]
        },
        {
            "interest_id": "int-3",
            "description": "Basic plumbing for home maintenance",
            "priority": 3,
            "things": [
                {
                    "thing_id": "thing-5",
                    "title": "Plumbing Basics",
                    "type": "learning_material",
                    "tasks": [
                        {
                            "task_id": "task-5-1",
                            "order": 1,
                            "title": "Learn about common pipe types",
                            "estimated_time_min": 7,
                            "completed": False,
                            "prerequisites": []
                        }
                    ]
                }
            ]
        }
    ],
    "recent_completions": [
        {
            "task_id": "task-1-1",
            "interest_id": "int-1",
            "thing_id": "thing-1",
            "order": 1,
            "completed_at": "2025-10-31T10:00:00",
            "actual_time_min": 9
        }
    ],
    "quiz_scores": [
        {
            "task_id": "task-1-1",
            "interest_id": "int-1",
            "score": 3,
            "total_questions": 4,  # 75% - good performance
            "completed_at": "2025-10-31T10:10:00"
        }
    ]
}


async def test_basic_recommendation():
    """Test basic recommendation with default settings."""

    print("\n" + "="*80)
    print("TEST 1: Basic Recommendation (Any Task)")
    print("="*80 + "\n")

    agent = RecommendationAgent()

    result = await agent.execute({
        "interests": MOCK_USER_STATE["interests"],
        "recent_completions": MOCK_USER_STATE["recent_completions"],
        "quiz_scores": MOCK_USER_STATE["quiz_scores"],
        "filter": "any",
        "available_time_min": 10
    })

    print(f"📌 RECOMMENDED TASK:")
    print(f"   {result['recommended_task']['title']}")
    print(f"   From: {result['recommended_task']['interest_title']}")
    print(f"   Duration: {result['recommended_task']['estimated_time_min']} min")
    print(f"   Priority: {result['recommended_task']['interest_priority']}/10")
    print(f"   Score: {result['score']:.2f}")
    print(f"\n💡 REASONING:")
    print(f"   {result['reasoning']}")

    if result['alternatives']:
        print(f"\n📋 ALTERNATIVES:")
        for i, alt in enumerate(result['alternatives'], 1):
            print(f"   {i}. {alt['title']} ({alt['estimated_time_min']} min)")


async def test_high_priority_filter():
    """Test recommendation with high-priority filter."""

    print("\n" + "="*80)
    print("TEST 2: High-Priority Filter (Priority >= 7)")
    print("="*80 + "\n")

    agent = RecommendationAgent()

    result = await agent.execute({
        "interests": MOCK_USER_STATE["interests"],
        "recent_completions": MOCK_USER_STATE["recent_completions"],
        "quiz_scores": MOCK_USER_STATE["quiz_scores"],
        "filter": "high_priority",
        "available_time_min": 8
    })

    print(f"📌 RECOMMENDED TASK:")
    print(f"   {result['recommended_task']['title']}")
    print(f"   From: {result['recommended_task']['interest_title']} (Priority: {result['recommended_task']['interest_priority']}/10)")
    print(f"   Duration: {result['recommended_task']['estimated_time_min']} min")
    print(f"   Score: {result['score']:.2f}")
    print(f"\n💡 REASONING:")
    print(f"   {result['reasoning']}")

    # Verify all alternatives are also high priority
    print(f"\n✓ Verification: All recommended tasks have priority >= 7")
    for alt in [result['recommended_task']] + result['alternatives']:
        assert alt['interest_priority'] >= 7, f"Task has priority {alt['interest_priority']}"
        print(f"   ✓ {alt['title']}: Priority {alt['interest_priority']}")


async def test_interest_specific():
    """Test recommendation for specific interest."""

    print("\n" + "="*80)
    print("TEST 3: Interest-Specific Recommendation (AI Memory)")
    print("="*80 + "\n")

    agent = RecommendationAgent()

    result = await agent.execute({
        "interests": MOCK_USER_STATE["interests"],
        "recent_completions": MOCK_USER_STATE["recent_completions"],
        "quiz_scores": MOCK_USER_STATE["quiz_scores"],
        "filter": "topic",
        "interest_id": "int-2",  # AI memory interest
        "available_time_min": 8
    })

    print(f"📌 RECOMMENDED TASK:")
    print(f"   {result['recommended_task']['title']}")
    print(f"   From: {result['recommended_task']['interest_title']}")
    print(f"   Duration: {result['recommended_task']['estimated_time_min']} min")
    print(f"   Score: {result['score']:.2f}")
    print(f"\n💡 REASONING:")
    print(f"   {result['reasoning']}")

    # Verify all tasks are from the specified interest
    print(f"\n✓ Verification: All tasks are from 'AI agent memory management'")
    for task in [result['recommended_task']] + result['alternatives']:
        assert task['interest_id'] == "int-2"
        print(f"   ✓ {task['title']}")


async def test_time_constraint():
    """Test recommendation with limited time."""

    print("\n" + "="*80)
    print("TEST 4: Limited Time (5 minutes available)")
    print("="*80 + "\n")

    agent = RecommendationAgent()

    result = await agent.execute({
        "interests": MOCK_USER_STATE["interests"],
        "recent_completions": MOCK_USER_STATE["recent_completions"],
        "quiz_scores": MOCK_USER_STATE["quiz_scores"],
        "filter": "any",
        "available_time_min": 5  # Very limited time
    })

    print(f"📌 RECOMMENDED TASK:")
    print(f"   {result['recommended_task']['title']}")
    print(f"   Duration: {result['recommended_task']['estimated_time_min']} min (Available: 5 min)")
    print(f"   Time fit: {'✓ Good' if result['recommended_task']['estimated_time_min'] <= 6 else '⚠ Might be tight'}")
    print(f"   Score: {result['score']:.2f}")
    print(f"\n💡 REASONING:")
    print(f"   {result['reasoning']}")


async def test_recency_effect():
    """Test that recently completed topics get lower priority."""

    print("\n" + "="*80)
    print("TEST 5: Recency Effect (Avoid Recently Completed)")
    print("="*80 + "\n")

    agent = RecommendationAgent()

    # Add more recent completions from beef cooking
    extended_completions = MOCK_USER_STATE["recent_completions"] + [
        {
            "task_id": "task-1-2",
            "interest_id": "int-1",
            "thing_id": "thing-1",
            "order": 2,
            "completed_at": "2025-10-31T11:00:00"
        },
        {
            "task_id": "task-2-1",
            "interest_id": "int-1",
            "thing_id": "thing-2",
            "order": 1,
            "completed_at": "2025-10-31T12:00:00"
        }
    ]

    result = await agent.execute({
        "interests": MOCK_USER_STATE["interests"],
        "recent_completions": extended_completions,
        "quiz_scores": MOCK_USER_STATE["quiz_scores"],
        "filter": "any",
        "available_time_min": 8
    })

    print(f"📌 RECOMMENDED TASK:")
    print(f"   {result['recommended_task']['title']}")
    print(f"   From: {result['recommended_task']['interest_title']}")

    # Should likely recommend AI or plumbing, not beef cooking
    if result['recommended_task']['interest_id'] != "int-1":
        print(f"   ✓ Correctly avoided beef cooking (recently completed 3 tasks)")
    else:
        print(f"   ⚠ Recommended beef cooking despite recent completions")

    print(f"\n💡 REASONING:")
    print(f"   {result['reasoning']}")


async def test_prerequisite_ordering():
    """Test that prerequisites are respected."""

    print("\n" + "="*80)
    print("TEST 6: Prerequisite Ordering")
    print("="*80 + "\n")

    agent = RecommendationAgent()

    # User has NO completions yet
    result = await agent.execute({
        "interests": MOCK_USER_STATE["interests"],
        "recent_completions": [],  # No history
        "quiz_scores": [],
        "filter": "topic",
        "interest_id": "int-1",  # Beef cooking
        "available_time_min": 8
    })

    print(f"📌 RECOMMENDED TASK:")
    print(f"   Order: {result['recommended_task']['order']}")
    print(f"   Title: {result['recommended_task']['title']}")

    # Should recommend task with order=1 or no prerequisites
    if result['recommended_task']['order'] == 1 or not result['recommended_task'].get('prerequisites'):
        print(f"   ✓ Correctly recommended task with no prerequisites")
    else:
        print(f"   ⚠ Recommended task {result['recommended_task']['order']} (might have prerequisites)")

    print(f"\n💡 REASONING:")
    print(f"   {result['reasoning']}")


async def test_score_breakdown():
    """Test to show score breakdown for multiple tasks."""

    print("\n" + "="*80)
    print("TEST 7: Score Breakdown Analysis")
    print("="*80 + "\n")

    agent = RecommendationAgent()

    result = await agent.execute({
        "interests": MOCK_USER_STATE["interests"],
        "recent_completions": MOCK_USER_STATE["recent_completions"],
        "quiz_scores": MOCK_USER_STATE["quiz_scores"],
        "filter": "any",
        "available_time_min": 8
    })

    print("Task Scores:")
    print(f"{'Task':<50} {'Priority':<10} {'Score':<10}")
    print("-" * 70)

    # Show top recommendation
    task = result['recommended_task']
    print(f"{task['title']:<50} {task['interest_priority']}/10{'':<6} {result['score']:.3f} ⭐")

    # Show alternatives (we'd need to modify agent to return scores, but for now just show they exist)
    print(f"\n{len(result['alternatives'])} alternatives found")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║               Recommendation Agent Test Suite                   ║
╚════════════════════════════════════════════════════════════════╝

This will test the Recommendation Agent with various scenarios:
1. Basic recommendation (any task)
2. High-priority filter
3. Interest-specific recommendation
4. Time constraint handling
5. Recency effect (avoid recently completed)
6. Prerequisite ordering
7. Score breakdown

Using mock user data with 3 interests and various completion states.

""")

    try:
        asyncio.run(test_basic_recommendation())
        print("\n\n⏳ Waiting 2 seconds...\n")

        asyncio.run(test_high_priority_filter())
        print("\n\n⏳ Waiting 2 seconds...\n")

        asyncio.run(test_interest_specific())
        print("\n\n⏳ Waiting 2 seconds...\n")

        asyncio.run(test_time_constraint())
        print("\n\n⏳ Waiting 2 seconds...\n")

        asyncio.run(test_recency_effect())
        print("\n\n⏳ Waiting 2 seconds...\n")

        asyncio.run(test_prerequisite_ordering())
        print("\n\n⏳ Waiting 2 seconds...\n")

        asyncio.run(test_score_breakdown())

        print("\n✅ All recommendation tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
