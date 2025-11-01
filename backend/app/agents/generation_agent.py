"""Generation Agent - creates original educational content."""
import logging
from typing import Any, Dict, List, Optional
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GenerationAgent(BaseAgent):
    """Agent that generates original educational content for tasks."""

    SYSTEM_PROMPT = """You are an expert educational content creator specializing in micro-learning.

Your job is to create clear, engaging content that can be consumed in 5-10 minutes.

## FORMAT INFERENCE RULES

Infer the appropriate format from the task title:

1. **Tutorial** - For titles containing: "exercise", "practice", "walkthrough", "step-by-step", "how to"
   - Structure: Introduction → Steps (numbered) → Practice tips → Summary
   - Interactive and hands-on
   - Include specific actions to take

2. **Article** - For titles containing: "understanding", "learn about", "introduction to", "overview"
   - Structure: Introduction → Key concepts (sections with headers) → Examples → Conclusion
   - Educational and explanatory
   - Focus on comprehension

3. **Guide** - For titles containing: "guide", "reference", "quick reference", "identification"
   - Structure: Brief intro → Organized information (tables, lists, categories)
   - Quick lookup format
   - Concise and scannable

4. **Checklist** - For titles containing: "checklist", "preparation", "setup", "pre-", "requirements"
   - Structure: Context → Checklist items (☐) → Additional notes
   - Actionable items
   - Easy to follow along

5. **Code/Technical** - For titles containing: "code", "implementation", "programming", "script"
   - Structure: Explanation → Code examples → Line-by-line breakdown → Usage
   - Include working code snippets
   - Technical but accessible

## CONTENT QUALITY REQUIREMENTS

- **Target reading time**: Match the specified duration (±2 minutes)
- **Clarity**: Use simple, direct language - assume beginner unless specified otherwise
- **Actionable**: Focus on what the learner can DO, not just know
- **Examples**: Include 2-3 concrete examples
- **Structure**: Use markdown headers, lists, bold/italic for emphasis
- **Engagement**: Make it interesting - use analogies, real-world connections

## WORD COUNT FORMULA
- 5 minutes = ~750 words
- 8 minutes = ~1200 words
- 10 minutes = ~1500 words
- Adjust based on target_duration_min

Generate content that feels like it was written by an expert teacher who cares about the student's success.
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate educational content for a task.

        Args:
            input_data: Dict with keys:
                - title: str (task title)
                - duration_min: int (target reading time)
                - topic: str (optional, defaults to title)
                - difficulty: str (optional, defaults to "beginner")
                - context: str (optional, additional context about the interest)

        Returns:
            Dict with:
                - content: str (markdown content)
                - format: str (inferred format)
                - estimated_read_time: int (minutes)
                - word_count: int
                - key_concepts: List[str] (for quiz generation)
        """
        title = input_data["title"]
        duration_min = input_data.get("duration_min", 8)
        topic = input_data.get("topic", title)
        difficulty = input_data.get("difficulty", "beginner")
        context = input_data.get("context", "")

        logger.info(f"Generating content for: '{title}' ({duration_min} min, {difficulty})")

        # Infer format from title (will be done by LLM)
        inferred_format = self._infer_format_hint(title)
        logger.debug(f"Format hint: {inferred_format}")

        # Generate the content
        content = await self._generate_content(
            title=title,
            topic=topic,
            duration_min=duration_min,
            difficulty=difficulty,
            context=context,
            format_hint=inferred_format
        )

        # Extract key concepts for quiz generation
        key_concepts = await self._extract_key_concepts(content)

        # Estimate actual word count and read time
        word_count = len(content.split())
        estimated_read_time = max(1, round(word_count / 150))  # ~150 words per minute

        return {
            "content": content,
            "format": inferred_format,
            "estimated_read_time": estimated_read_time,
            "word_count": word_count,
            "key_concepts": key_concepts
        }

    def _infer_format_hint(self, title: str) -> str:
        """Provide a format hint based on title keywords.

        This is a simple heuristic - the LLM will do the actual inference.

        Args:
            title: Task title

        Returns:
            Format hint string
        """
        title_lower = title.lower()

        if any(word in title_lower for word in ["exercise", "practice", "walkthrough", "step-by-step", "how to"]):
            return "tutorial"
        elif any(word in title_lower for word in ["checklist", "preparation", "setup", "pre-", "requirements"]):
            return "checklist"
        elif any(word in title_lower for word in ["guide", "reference", "identification"]):
            return "guide"
        elif any(word in title_lower for word in ["code", "implementation", "programming", "script"]):
            return "code"
        else:
            return "article"

    async def _generate_content(
        self,
        title: str,
        topic: str,
        duration_min: int,
        difficulty: str,
        context: str,
        format_hint: str
    ) -> str:
        """Generate the actual content using LLM.

        Args:
            title: Task title
            topic: Topic to cover
            duration_min: Target reading time
            difficulty: Difficulty level
            context: Additional context
            format_hint: Suggested format

        Returns:
            Generated markdown content
        """
        word_count = duration_min * 150  # ~150 words per minute

        user_message = f"""Create educational content for this learning task:

**Task Title:** {title}
**Topic:** {topic}
**Target Reading Time:** {duration_min} minutes (~{word_count} words)
**Difficulty Level:** {difficulty}
**Format Hint:** {format_hint}

{f"**Context:** {context}" if context else ""}

Based on the title, infer the best format and structure. Follow the format inference rules in your system prompt.

Create engaging, practical content that helps the learner understand and apply this knowledge.

Use markdown formatting with:
- Clear headers (##, ###)
- Lists where appropriate
- **Bold** for key terms
- Code blocks if technical
- Tables if comparing information

Output only the markdown content, no preamble.
"""

        content = await self._call_llm(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.7,
            max_tokens=4096
        )

        return content.strip()

    async def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from generated content for quiz generation.

        Args:
            content: Generated markdown content

        Returns:
            List of key concepts/facts
        """
        user_message = f"""Extract 3-5 key concepts or facts from this educational content that would make good quiz questions.

Content:
{content[:2000]}  # Limit to avoid token overflow

Return as a JSON array of strings:
["concept 1", "concept 2", "concept 3", ...]

Each concept should be:
- A specific fact or principle
- Testable (can make a question from it)
- Important to understanding the topic

Output only the JSON array, nothing else.
"""

        try:
            response = await self._call_llm(
                system_prompt="You are an expert at identifying key learning concepts.",
                user_message=user_message,
                temperature=0.3,
                max_tokens=500
            )

            # Parse JSON
            import json
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            concepts = json.loads(json_str)
            logger.debug(f"Extracted {len(concepts)} key concepts")
            return concepts

        except Exception as e:
            logger.error(f"Failed to extract key concepts: {e}")
            # Return empty list, not critical
            return []

    async def generate_for_task_outline(self, task_outline: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """Convenience method to generate content from Discovery Agent task outline.

        Args:
            task_outline: Task outline from Discovery Agent with keys:
                - title
                - duration_min
                - content_type (should be "generated")
            context: Optional context about the overall interest/thing

        Returns:
            Same as execute() method
        """
        if task_outline.get("content_type") != "generated":
            logger.warning(f"Task '{task_outline.get('title')}' is not marked for generation")
            return None

        return await self.execute({
            "title": task_outline["title"],
            "duration_min": task_outline["duration_min"],
            "topic": task_outline["title"],
            "difficulty": "beginner",  # Could be inferred from interest analysis
            "context": context
        })
