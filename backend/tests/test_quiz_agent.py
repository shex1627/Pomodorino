"""Test script for Quiz Generation Agent."""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.quiz_agent import QuizGenerationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_quiz_from_generated_content():
    """Test quiz generation using content from Generation Agent."""

    # Find generated content files
    content_files = sorted(Path(__file__).parent.glob("generated_content_*.md"))

    if not content_files:
        print("❌ No generated content files found. Run test_generation_agent.py first!")
        return

    print(f"Found {len(content_files)} content files to generate quizzes from\n")

    # Initialize Quiz Agent
    agent = QuizGenerationAgent()

    # Test with first 3 content files (to save API costs)
    for i, content_file in enumerate(content_files[:3], 1):
        print(f"\n{'='*80}")
        print(f"QUIZ {i}: {content_file.name}")
        print(f"{'='*80}\n")

        # Parse the generated content file
        with open(content_file, 'r') as f:
            file_content = f.read()

        # Extract metadata and content
        lines = file_content.split('\n')
        task_title = lines[0].replace('# ', '').strip()

        # Find the actual content (after the second ---)
        content_start = 0
        dash_count = 0
        for idx, line in enumerate(lines):
            if line.strip() == '---':
                dash_count += 1
                if dash_count == 2:
                    content_start = idx + 1
                    break

        # Extract content and key concepts
        content_parts = file_content.split('## Key Concepts')
        actual_content = content_parts[0][content_start:] if len(content_parts) > 0 else file_content

        # Extract key concepts if they exist
        key_concepts = []
        if len(content_parts) > 1:
            concepts_text = content_parts[1]
            for line in concepts_text.split('\n'):
                if line.strip().startswith('- '):
                    key_concepts.append(line.strip()[2:])

        print(f"📖 Task: {task_title}")
        print(f"   Content length: {len(actual_content)} chars")
        print(f"   Key concepts: {len(key_concepts)}")
        print(f"\n🎯 Generating 4-question quiz...")

        try:
            # Generate quiz
            result = await agent.generate_for_task(
                task_content=actual_content,
                task_title=task_title,
                key_concepts=key_concepts,
                num_questions=4,
                difficulty="beginner"
            )

            # Display results
            print(f"\n✅ Quiz Generated!")
            print(f"   Total questions: {result['total_questions']}")
            print(f"   Difficulty: {result['difficulty']}")

            # Display each question
            for q_num, question in enumerate(result['questions'], 1):
                print(f"\n{'─'*76}")
                print(f"Question {q_num}: {question['question_text']}")
                print()
                for idx, option in enumerate(question['options']):
                    letter = chr(65 + idx)  # A, B, C, D
                    marker = "✓" if letter == question['correct_answer'] else " "
                    print(f"   {marker} {letter}) {option}")
                print()
                print(f"   💡 Explanation: {question['explanation']}")

            # Save quiz to file
            quiz_output = {
                "task_title": task_title,
                "content_source": content_file.name,
                "quiz": result
            }

            output_file = Path(__file__).parent / f"quiz_{i}.json"
            with open(output_file, 'w') as f:
                json.dump(quiz_output, f, indent=2)

            print(f"\n💾 Quiz saved to: {output_file.name}")

        except Exception as e:
            logger.error(f"Quiz generation failed: {e}", exc_info=True)
            print(f"❌ Failed: {e}")

        # Wait between tests to avoid rate limits
        if i < min(3, len(content_files)):
            print("\nWaiting 5 seconds before next quiz...")
            await asyncio.sleep(5)


async def test_manual_quiz_examples():
    """Test quiz generation with manual examples."""

    print("\n" + "="*80)
    print("MANUAL QUIZ GENERATION TEST")
    print("="*80 + "\n")

    agent = QuizGenerationAgent()

    # Test case 1: Simple concept
    test_content_1 = """
# Understanding Rare, Medium, and Well-Done Steak

When cooking steak, doneness refers to how much the internal temperature has risen.

**Rare (120-125°F):**
- Cool red center
- Very soft and squishy to touch
- Cooks for about 2-3 minutes per side

**Medium-Rare (130-135°F):**
- Warm red center
- Slightly firmer, like touching thumb to index finger
- Cooks for about 3-4 minutes per side
- **Most popular and recommended for quality cuts**

**Medium (135-145°F):**
- Warm pink center
- Firmer, like touching thumb to middle finger
- Cooks for about 4-5 minutes per side

**Well-Done (155°F+):**
- No pink, fully brown throughout
- Very firm, like touching thumb to pinky
- Cooks for 6+ minutes per side
"""

    print("Test 1: Simple Steak Doneness Concept")
    print("─" * 40)

    try:
        result = await agent.generate_for_task(
            task_content=test_content_1,
            task_title="Understanding Steak Doneness Levels",
            key_concepts=[
                "Rare is 120-125°F with cool red center",
                "Medium-rare is most popular at 130-135°F",
                "Well-done has no pink and is very firm"
            ],
            num_questions=3,
            difficulty="beginner"
        )

        print(f"Generated {result['total_questions']} questions:\n")
        for i, q in enumerate(result['questions'], 1):
            print(f"{i}. {q['question_text']}")
            print(f"   Correct: {q['correct_answer']}")

    except Exception as e:
        print(f"Failed: {e}")

    await asyncio.sleep(3)

    # Test case 2: More complex technical content
    test_content_2 = """
# Vector Embeddings in AI Memory Systems

Vector embeddings are numerical representations of text that capture semantic meaning.

**How They Work:**
1. Text is converted into a high-dimensional vector (e.g., 1536 dimensions)
2. Similar concepts have vectors that are close together in space
3. Distance metrics (cosine similarity) measure how related two pieces of text are

**Use in AI Agents:**
- Store conversation history as vectors in a vector database
- When user asks a question, convert it to a vector
- Search for similar past conversations using vector similarity
- Retrieve relevant context without exact keyword matching

**Popular Vector Databases:**
- Pinecone (managed cloud service)
- Chroma (open-source, Python)
- Weaviate (graph-based)
"""

    print("\n\nTest 2: Technical AI Concept")
    print("─" * 40)

    try:
        result = await agent.generate_for_task(
            task_content=test_content_2,
            task_title="Vector Embeddings for Memory",
            key_concepts=[
                "Vector embeddings convert text to numerical representations",
                "Similar concepts have vectors close together in space",
                "Cosine similarity measures vector distance"
            ],
            num_questions=4,
            difficulty="intermediate"
        )

        print(f"Generated {result['total_questions']} questions:\n")
        for i, q in enumerate(result['questions'], 1):
            print(f"{i}. {q['question_text']}")
            for idx, opt in enumerate(q['options']):
                letter = chr(65 + idx)
                marker = "→" if letter == q['correct_answer'] else " "
                print(f"   {marker} {letter}) {opt}")
            print()

    except Exception as e:
        print(f"Failed: {e}")


async def test_quiz_quality():
    """Test that quiz questions meet quality standards."""

    print("\n" + "="*80)
    print("QUIZ QUALITY VALIDATION TEST")
    print("="*80 + "\n")

    agent = QuizGenerationAgent()

    # Simple test content
    content = """
Python is a high-level programming language. It was created by Guido van Rossum
and first released in 1991. Python emphasizes code readability and uses significant
indentation. It supports multiple programming paradigms including procedural,
object-oriented, and functional programming.
"""

    result = await agent.generate_for_task(
        task_content=content,
        task_title="Python Programming Basics",
        num_questions=3
    )

    print("Quality Checks:")
    print("─" * 40)

    all_passed = True

    for i, q in enumerate(result['questions'], 1):
        print(f"\nQuestion {i}:")

        # Check 1: Has question mark
        has_question_mark = '?' in q['question_text']
        print(f"   {'✓' if has_question_mark else '✗'} Has question mark")
        if not has_question_mark:
            all_passed = False

        # Check 2: Exactly 4 options
        has_4_options = len(q['options']) == 4
        print(f"   {'✓' if has_4_options else '✗'} Has exactly 4 options ({len(q['options'])})")
        if not has_4_options:
            all_passed = False

        # Check 3: Valid correct answer
        valid_answer = q['correct_answer'] in ['A', 'B', 'C', 'D']
        print(f"   {'✓' if valid_answer else '✗'} Valid correct answer ({q['correct_answer']})")
        if not valid_answer:
            all_passed = False

        # Check 4: Has explanation
        has_explanation = len(q['explanation']) > 10
        print(f"   {'✓' if has_explanation else '✗'} Has explanation ({len(q['explanation'])} chars)")
        if not has_explanation:
            all_passed = False

        # Check 5: Options are unique
        unique_options = len(q['options']) == len(set(q['options']))
        print(f"   {'✓' if unique_options else '✗'} All options are unique")
        if not unique_options:
            all_passed = False

    print(f"\n{'='*40}")
    if all_passed:
        print("✅ All quality checks passed!")
    else:
        print("⚠️  Some quality checks failed")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║                  Quiz Generation Agent Test Suite               ║
╚════════════════════════════════════════════════════════════════╝

This will test the Quiz Generation Agent with:
1. Content from Generation Agent (if available)
2. Manual test examples
3. Quality validation checks

Make sure you have ANTHROPIC_API_KEY in .env file.

""")

    try:
        # Test 1: Generate quizzes from existing content
        asyncio.run(test_quiz_from_generated_content())

        # Test 2: Manual examples
        print("\n\n")
        asyncio.run(test_manual_quiz_examples())

        # Test 3: Quality validation
        print("\n\n")
        asyncio.run(test_quiz_quality())

        print("\n✅ All quiz tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
