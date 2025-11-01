"""Quiz Generation Agent - creates multiple-choice questions from content."""
import json
import logging
from typing import Any, Dict, List, Optional
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class QuizGenerationAgent(BaseAgent):
    """Agent that generates multiple-choice quizzes from educational content."""

    SYSTEM_PROMPT = """You are an expert quiz creator specializing in educational assessment.

Your job is to create high-quality multiple-choice questions that test genuine understanding, not just memorization.

## QUESTION QUALITY REQUIREMENTS

**Good Questions:**
- Test understanding and application, not just recall
- Have one clearly correct answer
- Include plausible distractors (wrong answers that seem reasonable)
- Are unambiguous and clearly worded
- Cover key concepts from the content
- Avoid trick questions or overly nitpicky details

**Question Types to Use:**
1. **Conceptual**: Test understanding of core ideas
2. **Application**: "Which would you use when..."
3. **Comparison**: "What's the difference between X and Y?"
4. **Process**: "What's the correct order/sequence?"
5. **Problem-solving**: Present a scenario, ask for solution

**Avoid:**
- Questions that are too easy (obvious answers)
- Questions that are too hard (obscure details)
- Negative questions ("Which is NOT true?")
- "All of the above" or "None of the above" options
- Questions with multiple correct answers

## DISTRACTOR GUIDELINES

Distractors (wrong answers) should be:
- **Plausible**: Sound like they could be right to someone who didn't fully understand
- **Related**: Use concepts/terms from the same domain
- **Common misconceptions**: Reflect typical mistakes learners make
- **Consistent**: Match the format and length of the correct answer

**Bad distractor**: "Purple elephant" (obviously wrong, unrelated)
**Good distractor**: A common misconception or partial truth

## OUTPUT FORMAT

Return questions as a JSON array:
[
  {
    "question_text": "Clear, specific question?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "B",
    "explanation": "Why B is correct and why others are wrong"
  }
]

**Explanation Requirements:**
- Start with why the correct answer is right
- Optionally mention why common distractors are wrong
- Keep it concise (1-3 sentences)
- Help reinforce learning

Generate questions that help learners solidify their understanding and identify knowledge gaps.
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a quiz from educational content.

        Args:
            input_data: Dict with keys:
                - content: str (markdown content to create quiz from)
                - key_concepts: List[str] (optional, key concepts to focus on)
                - num_questions: int (optional, default 4)
                - difficulty: str (optional, default "beginner")
                - task_title: str (optional, for context)

        Returns:
            Dict with:
                - questions: List[Dict] (quiz questions)
                - total_questions: int
                - difficulty: str
        """
        content = input_data["content"]
        key_concepts = input_data.get("key_concepts", [])
        num_questions = input_data.get("num_questions", 4)
        difficulty = input_data.get("difficulty", "beginner")
        task_title = input_data.get("task_title", "Unknown Task")

        # Validate num_questions range
        if num_questions < 3:
            num_questions = 3
        elif num_questions > 10:
            num_questions = 10

        logger.info(f"Generating {num_questions} quiz questions for: '{task_title}' ({difficulty})")

        # Generate questions
        questions = await self._generate_questions(
            content=content,
            key_concepts=key_concepts,
            num_questions=num_questions,
            difficulty=difficulty,
            task_title=task_title
        )

        # Validate and clean questions
        questions = self._validate_questions(questions)

        logger.info(f"Successfully generated {len(questions)} valid questions")

        return {
            "questions": questions,
            "total_questions": len(questions),
            "difficulty": difficulty
        }

    async def _generate_questions(
        self,
        content: str,
        key_concepts: List[str],
        num_questions: int,
        difficulty: str,
        task_title: str
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions using LLM.

        Args:
            content: Educational content
            key_concepts: Key concepts to test
            num_questions: Number of questions to generate
            difficulty: Difficulty level
            task_title: Title of the task

        Returns:
            List of question dictionaries
        """
        # Truncate content if too long (to avoid token limits)
        max_content_length = 3000
        if len(content) > max_content_length:
            content_preview = content[:max_content_length] + "\n\n[Content truncated for quiz generation]"
        else:
            content_preview = content

        user_message = f"""Create {num_questions} multiple-choice questions for this educational content:

**Task:** {task_title}
**Difficulty Level:** {difficulty}

**Content:**
{content_preview}

{f'''**Key Concepts to Test:**
{chr(10).join(f"- {concept}" for concept in key_concepts)}''' if key_concepts else ''}

**Instructions:**
1. Generate exactly {num_questions} questions
2. Each question must have 4 options (A, B, C, D)
3. Questions should test understanding at {difficulty} level
4. Include clear explanations for correct answers
5. Make distractors plausible but clearly incorrect
6. Cover different aspects of the content (don't repeat similar questions)

Return ONLY the JSON array of questions, no other text.
"""

        response = await self._call_llm(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.7,  # Some creativity but not too random
            max_tokens=3000
        )

        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            questions = json.loads(json_str)
            logger.debug(f"Parsed {len(questions)} questions from LLM response")
            return questions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            # Return empty list rather than crashing
            return []

    def _validate_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean quiz questions.

        Args:
            questions: Raw questions from LLM

        Returns:
            Validated and cleaned questions
        """
        validated = []

        for i, q in enumerate(questions, 1):
            try:
                # Check required fields
                if not all(key in q for key in ["question_text", "options", "correct_answer", "explanation"]):
                    logger.warning(f"Question {i} missing required fields, skipping")
                    continue

                # Check options count
                if len(q["options"]) != 4:
                    logger.warning(f"Question {i} doesn't have exactly 4 options, skipping")
                    continue

                # Check correct_answer format
                if q["correct_answer"] not in ["A", "B", "C", "D"]:
                    logger.warning(f"Question {i} has invalid correct_answer: {q['correct_answer']}, skipping")
                    continue

                # Clean and normalize
                cleaned = {
                    "question_text": str(q["question_text"]).strip(),
                    "options": [str(opt).strip() for opt in q["options"]],
                    "correct_answer": str(q["correct_answer"]).upper().strip(),
                    "explanation": str(q["explanation"]).strip()
                }

                # Additional validation
                if not cleaned["question_text"] or len(cleaned["question_text"]) < 10:
                    logger.warning(f"Question {i} has invalid question_text, skipping")
                    continue

                if any(not opt or len(opt) < 2 for opt in cleaned["options"]):
                    logger.warning(f"Question {i} has invalid options, skipping")
                    continue

                validated.append(cleaned)

            except Exception as e:
                logger.error(f"Error validating question {i}: {e}")
                continue

        return validated

    async def generate_for_task(
        self,
        task_content: str,
        task_title: str,
        key_concepts: Optional[List[str]] = None,
        num_questions: int = 4,
        difficulty: str = "beginner"
    ) -> Dict[str, Any]:
        """Convenience method to generate quiz for a task.

        Args:
            task_content: Markdown content of the task
            task_title: Title of the task
            key_concepts: Optional list of key concepts
            num_questions: Number of questions (3-10)
            difficulty: Difficulty level

        Returns:
            Same as execute() method
        """
        return await self.execute({
            "content": task_content,
            "key_concepts": key_concepts or [],
            "num_questions": num_questions,
            "difficulty": difficulty,
            "task_title": task_title
        })

    async def generate_from_generation_result(
        self,
        generation_result: Dict[str, Any],
        num_questions: int = 4
    ) -> Dict[str, Any]:
        """Generate quiz from Generation Agent output.

        Args:
            generation_result: Output from GenerationAgent.execute()
            num_questions: Number of questions

        Returns:
            Quiz data
        """
        return await self.execute({
            "content": generation_result["content"],
            "key_concepts": generation_result.get("key_concepts", []),
            "num_questions": num_questions,
            "difficulty": "beginner",  # Could be extracted from generation metadata
            "task_title": "Generated Content"
        })
