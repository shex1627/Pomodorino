"""Recommendation Agent - suggests optimal next task for user."""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RecommendationAgent(BaseAgent):
    """Agent that recommends the optimal next task based on user context."""

    SYSTEM_PROMPT = """You are an expert learning coach helping users make optimal decisions about what to learn next.

Your job is to analyze a user's learning state and recommend the best task for their current situation.

Consider:
- **Priority**: Higher priority interests should be favored
- **Progress**: Recommend tasks in logical order (don't skip prerequisites)
- **Variety**: Avoid recommending the same topic repeatedly
- **Time fit**: Match task duration to available time
- **Performance**: If user is struggling (low quiz scores), recommend easier content
- **Engagement**: Consider what will keep the user motivated

Generate recommendations that balance learning effectiveness with user engagement.
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend optimal task for user.

        Args:
            input_data: Dict with keys:
                - interests: List[Dict] - User's interests with tasks
                - recent_completions: List[Dict] - Recently completed tasks
                - quiz_scores: List[Dict] - Recent quiz attempt scores
                - filter: str - "any", "high_priority", "topic"
                - interest_id: str (optional) - Filter to specific interest
                - available_time_min: int (optional) - User's available time
                - time_of_day: str (optional) - "morning", "afternoon", "evening"

        Returns:
            Dict with:
                - recommended_task: Dict (best task to do)
                - reasoning: str (why this task)
                - score: float (confidence score)
                - alternatives: List[Dict] (2-3 backup options)
        """
        interests = input_data.get("interests", [])
        recent_completions = input_data.get("recent_completions", [])
        quiz_scores = input_data.get("quiz_scores", [])
        filter_type = input_data.get("filter", "any")
        interest_id = input_data.get("interest_id")
        available_time = input_data.get("available_time_min", 10)
        time_of_day = input_data.get("time_of_day", "afternoon")

        logger.info(f"Finding recommendation (filter: {filter_type}, time: {available_time} min)")

        # Get candidate tasks
        candidates = self._get_candidate_tasks(
            interests=interests,
            filter_type=filter_type,
            interest_id=interest_id
        )

        if not candidates:
            logger.warning("No candidate tasks found")
            return {
                "recommended_task": None,
                "reasoning": "No tasks available matching your criteria",
                "score": 0.0,
                "alternatives": []
            }

        logger.info(f"Found {len(candidates)} candidate tasks")

        # Score each candidate
        scored_candidates = []
        for task in candidates:
            score = self._score_task(
                task=task,
                recent_completions=recent_completions,
                quiz_scores=quiz_scores,
                available_time=available_time
            )
            scored_candidates.append((task, score))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Get top recommendation and alternatives
        top_task, top_score = scored_candidates[0]
        alternatives = [task for task, score in scored_candidates[1:4]]  # Next 3

        # Generate reasoning with LLM
        reasoning = await self._generate_reasoning(
            task=top_task,
            score=top_score,
            available_time=available_time,
            filter_type=filter_type,
            recent_completions=recent_completions,
            quiz_scores=quiz_scores
        )

        logger.info(f"Recommended: '{top_task['title']}' (score: {top_score:.2f})")

        return {
            "recommended_task": top_task,
            "reasoning": reasoning,
            "score": top_score,
            "alternatives": alternatives
        }

    def _get_candidate_tasks(
        self,
        interests: List[Dict],
        filter_type: str,
        interest_id: Optional[str] = None
    ) -> List[Dict]:
        """Get candidate tasks based on filters.

        Args:
            interests: User's interests with their tasks
            filter_type: Type of filter to apply
            interest_id: Specific interest to filter to

        Returns:
            List of candidate task dictionaries
        """
        candidates = []

        for interest in interests:
            # Apply interest filter if specified
            if interest_id and interest.get("interest_id") != interest_id:
                continue

            # Apply priority filter
            if filter_type == "high_priority" and interest.get("priority", 0) < 7:
                continue

            # Get incomplete tasks from this interest
            for thing in interest.get("things", []):
                for task in thing.get("tasks", []):
                    # Only include incomplete tasks
                    if task.get("completed", False):
                        continue

                    # Enrich task with interest context
                    enriched_task = {
                        **task,
                        "interest_id": interest.get("interest_id"),
                        "interest_title": interest.get("description"),
                        "interest_priority": interest.get("priority", 5),
                        "thing_id": thing.get("thing_id"),
                        "thing_title": thing.get("title"),
                        "thing_type": thing.get("type")
                    }
                    candidates.append(enriched_task)

        return candidates

    def _score_task(
        self,
        task: Dict,
        recent_completions: List[Dict],
        quiz_scores: List[Dict],
        available_time: int
    ) -> float:
        """Score a task based on multiple factors.

        Args:
            task: Task to score
            recent_completions: Recently completed tasks
            quiz_scores: Recent quiz scores
            available_time: Available time in minutes

        Returns:
            Score between 0 and 1 (higher is better)
        """
        score = 0.0

        # Factor 1: Priority (0-0.3)
        priority = task.get("interest_priority", 5)
        priority_score = (priority / 10) * 0.3
        score += priority_score

        # Factor 2: Prerequisites (0 or 0.25)
        prereqs = task.get("prerequisites", [])
        prereqs_met = self._check_prerequisites(task, recent_completions)
        if prereqs_met:
            score += 0.25
        else:
            # Can't recommend tasks with unmet prerequisites
            return 0.0

        # Factor 3: Recency penalty (-0.15 to 0)
        recency_penalty = self._calculate_recency_penalty(task, recent_completions)
        score -= recency_penalty * 0.15

        # Factor 4: Time fit (0-0.2)
        time_fit = self._calculate_time_fit(task, available_time)
        score += time_fit * 0.2

        # Factor 5: Quiz performance (0-0.1)
        quiz_factor = self._calculate_quiz_factor(task, quiz_scores)
        score += quiz_factor * 0.1

        # Factor 6: Freshness bonus (0-0.05)
        # Tasks never attempted get a small bonus
        if not any(c.get("task_id") == task.get("task_id") for c in recent_completions):
            score += 0.05

        return max(0.0, min(1.0, score))  # Clamp to [0, 1]

    def _check_prerequisites(
        self,
        task: Dict,
        recent_completions: List[Dict]
    ) -> bool:
        """Check if task prerequisites are met.

        Args:
            task: Task to check
            recent_completions: List of completed tasks

        Returns:
            True if all prerequisites are met
        """
        prereqs = task.get("prerequisites", [])
        if not prereqs:
            return True

        completed_task_ids = {c.get("task_id") for c in recent_completions}
        completed_orders = {c.get("order") for c in recent_completions if c.get("thing_id") == task.get("thing_id")}

        # Check if all prerequisite task orders are completed
        for prereq_order in prereqs:
            if prereq_order not in completed_orders:
                return False

        return True

    def _calculate_recency_penalty(
        self,
        task: Dict,
        recent_completions: List[Dict]
    ) -> float:
        """Calculate penalty for recently completed similar tasks.

        Args:
            task: Task being scored
            recent_completions: Recent completions

        Returns:
            Penalty between 0 and 1 (higher means more recent)
        """
        if not recent_completions:
            return 0.0

        # Check if same interest/thing was recently completed
        same_interest_recent = [
            c for c in recent_completions[-5:]  # Last 5 completions
            if c.get("interest_id") == task.get("interest_id")
        ]

        if not same_interest_recent:
            return 0.0

        # Most recent gets highest penalty
        return len(same_interest_recent) / 5.0

    def _calculate_time_fit(
        self,
        task: Dict,
        available_time: int
    ) -> float:
        """Calculate how well task duration fits available time.

        Args:
            task: Task being scored
            available_time: Minutes available

        Returns:
            Fit score between 0 and 1
        """
        task_duration = task.get("estimated_time_min", 8)

        # Perfect fit: task takes 80-100% of available time
        if 0.8 * available_time <= task_duration <= available_time:
            return 1.0

        # Good fit: task takes 60-120% of available time
        if 0.6 * available_time <= task_duration <= 1.2 * available_time:
            return 0.8

        # Acceptable: task takes 40-140% of available time
        if 0.4 * available_time <= task_duration <= 1.4 * available_time:
            return 0.5

        # Poor fit: significantly too short or too long
        return 0.2

    def _calculate_quiz_factor(
        self,
        task: Dict,
        quiz_scores: List[Dict]
    ) -> float:
        """Calculate factor based on quiz performance.

        Args:
            task: Task being scored
            quiz_scores: Recent quiz scores

        Returns:
            Factor between 0 and 1
        """
        if not quiz_scores:
            return 0.5  # Neutral

        # Get recent scores for same interest
        interest_scores = [
            s.get("score", 0) / s.get("total_questions", 1)
            for s in quiz_scores[-5:]
            if s.get("interest_id") == task.get("interest_id")
        ]

        if not interest_scores:
            return 0.5

        avg_score = sum(interest_scores) / len(interest_scores)

        # If user is struggling (< 60%), favor easier content
        # If user is doing well (> 80%), can handle harder content
        # This is a simplified version - in practice, we'd check task difficulty
        return avg_score  # 0-1 range

    async def _generate_reasoning(
        self,
        task: Dict,
        score: float,
        available_time: int,
        filter_type: str,
        recent_completions: List[Dict],
        quiz_scores: List[Dict]
    ) -> str:
        """Generate human-readable reasoning for recommendation.

        Args:
            task: Recommended task
            score: Task score
            available_time: Available time
            filter_type: Filter applied
            recent_completions: Recent completions
            quiz_scores: Quiz scores

        Returns:
            Reasoning string
        """
        # Build context
        priority = task.get("interest_priority", 5)
        duration = task.get("estimated_time_min", 8)
        interest_title = task.get("interest_title", "Unknown")

        # Count recent completions in same interest
        same_interest_count = sum(
            1 for c in recent_completions[-10:]
            if c.get("interest_id") == task.get("interest_id")
        )

        # Average quiz score for interest
        interest_quiz_scores = [
            s.get("score", 0) / s.get("total_questions", 1)
            for s in quiz_scores[-5:]
            if s.get("interest_id") == task.get("interest_id")
        ]
        avg_quiz = sum(interest_quiz_scores) / len(interest_quiz_scores) if interest_quiz_scores else None

        user_message = f"""Generate a brief (1-2 sentences) recommendation reasoning for this task:

**Task:** {task['title']}
**From Interest:** {interest_title} (Priority: {priority}/10)
**Duration:** {duration} minutes
**Available Time:** {available_time} minutes
**Filter:** {filter_type}
**Recent completions in this interest:** {same_interest_count} in last 10 tasks
{f"**Average quiz score:** {avg_quiz:.0%}" if avg_quiz else ""}

Explain why this is a good task to do right now. Be concise and encouraging.
Focus on the most relevant factors (priority, time fit, progress in interest).
"""

        try:
            reasoning = await self._call_llm(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=200
            )
            return reasoning.strip()
        except Exception as e:
            logger.error(f"Failed to generate reasoning: {e}")
            # Fallback to simple reasoning
            return f"High-priority interest ({priority}/10), matches your available time ({duration} min), and builds on your progress."
