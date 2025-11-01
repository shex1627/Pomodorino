"""Test script for Discovery Agent."""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.discovery_agent import ContentDiscoveryAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_discovery_agent():
    """Test the discovery agent with sample interests."""

    # Test cases
    test_interests = [
        {
            "interest_description": "Learn to cook different parts of beef (prefer dishes under 15 min)",
            "priority": 7,
            "count": 5
        },
        {
            "interest_description": "I want to learn about AI agent memory management",
            "priority": 10,
            "count": 5
        },
        {
            "interest_description": "Learn plumbing basics for home maintenance",
            "priority": 3,
            "count": 3
        }
    ]

    # Initialize agent
    agent = ContentDiscoveryAgent()

    # Test each interest
    for i, interest_data in enumerate(test_interests, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST {i}: {interest_data['interest_description']}")
        logger.info(f"{'='*80}\n")

        try:
            # Execute agent
            result = await agent.execute(interest_data)

            # Print results
            print(f"\n🎯 INTEREST: {interest_data['interest_description']}")
            print(f"   Priority: {interest_data['priority']}/10")
            print(f"\n📊 ANALYSIS:")
            print(f"   Difficulty: {result['analysis'].get('difficulty_level')}")
            print(f"   Key Topics: {', '.join(result['analysis'].get('key_topics', []))}")
            print(f"   Learning Goals:")
            for goal in result['analysis'].get('learning_goals', []):
                print(f"     - {goal}")

            print(f"\n📹 RESOURCES FOUND: {len(result['resources'])}")
            for resource in result['resources'][:3]:  # Show first 3
                print(f"   - [{resource['type']}] {resource['title']}")
                print(f"     URL: {resource['url']}")
                print(f"     Duration: {resource.get('duration_minutes', 'N/A')} min")

            print(f"\n📚 SUGGESTED THINGS: {len(result['suggested_things'])}")
            for thing in result['suggested_things']:
                print(f"\n   📖 {thing['title']}")
                print(f"      Type: {thing['type']}")
                print(f"      Total Time: {thing.get('estimated_total_time_min', 'N/A')} min")
                print(f"      Tasks: {thing.get('task_count', 0)}")
                print(f"      Tasks outline:")
                for task in thing.get('task_outlines', []):
                    print(f"         {task['order']}. {task['title']} ({task['duration_min']} min)")
                    if task.get('resource_url'):
                        print(f"            Resource: {task['resource_url']}")

            # Save full result to file
            output_file = Path(__file__).parent / f"discovery_result_{i}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Full result saved to: {output_file}")

        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)

        # Wait between tests to avoid rate limits
        if i < len(test_interests):
            logger.info("\nWaiting 5 seconds before next test...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║                  Discovery Agent Test Suite                    ║
╚════════════════════════════════════════════════════════════════╝

This will test the Content Discovery Agent with 3 sample interests:
1. Cooking beef cuts
2. AI agent memory management
3. Plumbing basics

Make sure you have set up your .env file with:
- ANTHROPIC_API_KEY (required)
- YOUTUBE_API_KEY (optional, for video search)

""")

    try:
        asyncio.run(test_discovery_agent())
        print("\n✅ All tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
