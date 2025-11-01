"""Test script for Generation Agent."""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.generation_agent import GenerationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_generation_agent():
    """Test the generation agent with tasks from Discovery Agent results."""

    # Load Discovery Agent results
    discovery_results = []
    for i in [1, 2, 3]:
        result_file = Path(__file__).parent / f"discovery_result_{i}.json"
        if result_file.exists():
            with open(result_file, 'r') as f:
                discovery_results.append(json.load(f))

    if not discovery_results:
        print("❌ No discovery results found. Run test_discovery_agent.py first!")
        return

    # Initialize Generation Agent
    agent = GenerationAgent()

    # Test with tasks from each discovery result
    for idx, discovery in enumerate(discovery_results, 1):
        interest_desc = discovery['analysis'].get('key_topics', ['Unknown'])[0]
        print(f"\n{'='*80}")
        print(f"DISCOVERY RESULT {idx}: {interest_desc}")
        print(f"{'='*80}\n")

        # Find tasks that need generation
        tasks_to_generate = []
        for thing in discovery.get('suggested_things', []):
            thing_title = thing['title']
            for task_outline in thing.get('task_outlines', []):
                if task_outline.get('content_type') == 'generated':
                    tasks_to_generate.append({
                        'thing_title': thing_title,
                        'task': task_outline
                    })

        print(f"Found {len(tasks_to_generate)} tasks needing content generation\n")

        # Generate content for first 2 tasks (to save API costs)
        for i, item in enumerate(tasks_to_generate[:2], 1):
            thing_title = item['thing_title']
            task = item['task']

            print(f"📝 TASK {i}: {task['title']}")
            print(f"   From Thing: {thing_title}")
            print(f"   Duration: {task['duration_min']} min")
            print(f"   Generating content...")

            try:
                # Generate content
                result = await agent.generate_for_task_outline(
                    task_outline=task,
                    context=f"Part of learning module: {thing_title}"
                )

                # Print results
                print(f"\n✅ Content Generated!")
                print(f"   Format: {result['format']}")
                print(f"   Word Count: {result['word_count']}")
                print(f"   Estimated Read Time: {result['estimated_read_time']} min")
                print(f"   Key Concepts: {len(result['key_concepts'])}")

                print(f"\n📄 CONTENT PREVIEW (first 500 chars):")
                print("   " + "-" * 76)
                preview = result['content'][:500].replace('\n', '\n   ')
                print(f"   {preview}...")
                print("   " + "-" * 76)

                print(f"\n🔑 KEY CONCEPTS:")
                for concept in result['key_concepts']:
                    print(f"   - {concept}")

                # Save full content to file
                output_file = Path(__file__).parent / f"generated_content_{idx}_{i}.md"
                with open(output_file, 'w') as f:
                    f.write(f"# {task['title']}\n\n")
                    f.write(f"**Thing:** {thing_title}\n")
                    f.write(f"**Duration:** {task['duration_min']} minutes\n")
                    f.write(f"**Format:** {result['format']}\n")
                    f.write(f"**Word Count:** {result['word_count']}\n\n")
                    f.write("---\n\n")
                    f.write(result['content'])
                    f.write("\n\n---\n\n")
                    f.write("## Key Concepts\n\n")
                    for concept in result['key_concepts']:
                        f.write(f"- {concept}\n")

                print(f"\n💾 Full content saved to: {output_file.name}\n")

            except Exception as e:
                logger.error(f"Generation failed: {e}", exc_info=True)
                print(f"❌ Generation failed: {e}\n")

            # Wait between generations to avoid rate limits
            if i < len(tasks_to_generate[:2]):
                await asyncio.sleep(3)

        # Wait between discovery results
        if idx < len(discovery_results):
            print("\nWaiting 5 seconds before next discovery result...")
            await asyncio.sleep(5)


async def test_manual_generation():
    """Test generation with manual examples to verify format inference."""

    print("\n" + "="*80)
    print("MANUAL FORMAT INFERENCE TEST")
    print("="*80 + "\n")

    agent = GenerationAgent()

    test_cases = [
        {
            "title": "Touch Test & Timing Practice Exercise",
            "duration_min": 10,
            "expected_format": "tutorial"
        },
        {
            "title": "Quick-Cooking Beef Cuts Identification Guide",
            "duration_min": 8,
            "expected_format": "guide"
        },
        {
            "title": "Pre-Cook Preparation Checklist & Setup",
            "duration_min": 8,
            "expected_format": "checklist"
        },
        {
            "title": "Understanding Short-term vs Long-term Memory",
            "duration_min": 8,
            "expected_format": "article"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{test['title']}'")
        print(f"   Expected format: {test['expected_format']}")

        try:
            result = await agent.execute({
                "title": test['title'],
                "duration_min": test['duration_min']
            })

            print(f"   ✅ Generated format: {result['format']}")
            print(f"   Word count: {result['word_count']}")
            print(f"   Read time: {result['estimated_read_time']} min")

            if result['format'] == test['expected_format']:
                print(f"   🎯 Format inference CORRECT!")
            else:
                print(f"   ⚠️  Format inference mismatch (got {result['format']})")

        except Exception as e:
            print(f"   ❌ Failed: {e}")

        if i < len(test_cases):
            await asyncio.sleep(2)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║                  Generation Agent Test Suite                   ║
╚════════════════════════════════════════════════════════════════╝

This will test the Content Generation Agent with tasks from the
Discovery Agent results.

Test Plan:
1. Load Discovery Agent results (discovery_result_*.json)
2. Find tasks marked content_type="generated"
3. Generate actual content for those tasks
4. Verify format inference works correctly
5. Save generated content to .md files

Make sure you have:
- Run test_discovery_agent.py first
- ANTHROPIC_API_KEY in .env file

""")

    try:
        # Run main test with discovery results
        asyncio.run(test_generation_agent())

        # Run manual format inference test
        print("\n\n" + "="*80)
        print("Running manual format inference tests...")
        print("="*80)
        asyncio.run(test_manual_generation())

        print("\n✅ All tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
