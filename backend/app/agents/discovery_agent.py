"""Content Discovery Agent - searches for relevant online resources."""
import json
import logging
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.agents.base_agent import BaseAgent
from app.core.config import settings

logger = logging.getLogger(__name__)


class ContentDiscoveryAgent(BaseAgent):
    """Agent that discovers relevant content from online sources."""

    SYSTEM_PROMPT = """You are a content discovery expert helping to find educational resources.

Your task is to analyze a user's learning interest and:
1. Extract key topics and concepts
2. Generate effective search queries for different resource types
3. Suggest how to structure learning "Things" (learning modules)

Be specific, practical, and focused on actionable learning goals.
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Discover content for a given interest.

        Args:
            input_data: Dict with keys:
                - interest_description: str
                - priority: int (1-10)
                - count: int (how many Things to generate)

        Returns:
            Dict with:
                - resources: List of found resources
                - suggested_things: List of suggested learning modules
        """
        interest = input_data["interest_description"]
        count = input_data.get("count", 10)
        priority = input_data.get("priority", 5)

        logger.info(f"Discovering content for interest: '{interest}' (priority: {priority})")

        # Step 1: Analyze the interest
        analysis = await self._analyze_interest(interest, priority)
        logger.info(f"Interest analysis complete. Topics: {analysis.get('key_topics', [])}")

        # Step 2: Generate search queries
        search_queries = await self._generate_search_queries(analysis)
        logger.info(f"Generated {len(search_queries.get('video_queries', []))} video queries")

        # Step 3: Search for resources
        resources = await self._search_resources(search_queries)
        logger.info(f"Found {len(resources)} total resources")

        # Step 4: Suggest Thing structures
        things = await self._suggest_things(analysis, resources, count)
        logger.info(f"Suggested {len(things)} learning Things")

        return {
            "analysis": analysis,
            "resources": resources,
            "suggested_things": things
        }

    async def _analyze_interest(self, interest: str, priority: int) -> Dict[str, Any]:
        """Analyze the interest to extract key information.

        Args:
            interest: User's interest description
            priority: Interest priority (1-10)

        Returns:
            Dict with analysis results
        """
        user_message = f"""Analyze this learning interest and extract key information:

Interest: "{interest}"
Priority Level: {priority}/10

Provide your analysis in JSON format with these fields:
{{
    "key_topics": [list of 3-5 main topics to learn],
    "difficulty_level": "beginner|intermediate|advanced",
    "learning_goals": [list of 3-5 specific learning goals],
    "suggested_duration_per_task": number (in minutes, should be 5-10),
    "resource_types_needed": ["video", "article", "tutorial", "project", etc.],
    "prerequisites": [any prerequisite knowledge needed]
}}

Be specific and actionable. Focus on what can be learned in 5-10 minute micro-sessions.
"""

        response = await self._call_llm(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.5
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

            analysis = json.loads(json_str)
            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            # Return a basic structure
            return {
                "key_topics": ["general learning"],
                "difficulty_level": "beginner",
                "learning_goals": ["Learn the basics"],
                "suggested_duration_per_task": 8,
                "resource_types_needed": ["article", "video"],
                "prerequisites": []
            }

    async def _generate_search_queries(self, analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate search queries based on analysis.

        Args:
            analysis: Interest analysis results

        Returns:
            Dict with query lists for different resource types
        """
        user_message = f"""Based on this learning interest analysis, generate effective search queries:

Analysis:
{json.dumps(analysis, indent=2)}

Generate search queries in JSON format:
{{
    "video_queries": [5-7 YouTube search queries],
    "article_queries": [5-7 article/blog search queries],
    "tutorial_queries": [3-5 tutorial/how-to search queries]
}}

Make queries:
- Specific and targeted
- Beginner-friendly if difficulty is beginner
- Focused on practical, actionable content
- Optimized for finding 5-10 minute content pieces
"""

        response = await self._call_llm(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.6
        )

        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            queries = json.loads(json_str)
            return queries
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse search queries: {e}")
            return {
                "video_queries": [],
                "article_queries": [],
                "tutorial_queries": []
            }

    async def _search_resources(self, queries: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Search for resources using the generated queries.

        Args:
            queries: Dict with query lists

        Returns:
            List of resource dicts
        """
        resources = []

        # Search YouTube if API key available
        if settings.youtube_api_key and queries.get("video_queries"):
            logger.info("Searching YouTube...")
            youtube_results = await self._search_youtube(queries["video_queries"][:3])  # Limit to 3 queries
            resources.extend(youtube_results)
        else:
            logger.warning("YouTube API key not configured, skipping video search")

        # For now, we'll simulate article search since we don't have a web search API
        # In production, you'd integrate with SerpAPI, Bing API, or similar
        logger.info("Article search would happen here (not implemented in test)")

        return resources

    async def _search_youtube(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Search YouTube for videos.

        Args:
            queries: List of search queries

        Returns:
            List of video resource dicts
        """
        if not settings.youtube_api_key:
            return []

        try:
            youtube = build('youtube', 'v3', developerKey=settings.youtube_api_key)
            results = []

            for query in queries[:3]:  # Limit queries to save quota
                logger.debug(f"YouTube search: '{query}'")

                search_response = youtube.search().list(
                    q=query,
                    part='id,snippet',
                    maxResults=3,  # Get top 3 results per query
                    type='video',
                    videoDuration='short',  # Prefer shorter videos (< 4 min) or medium (4-20 min)
                    order='relevance'
                ).execute()

                for item in search_response.get('items', []):
                    video_id = item['id']['videoId']
                    snippet = item['snippet']

                    # Get video details including duration
                    video_response = youtube.videos().list(
                        part='contentDetails,statistics',
                        id=video_id
                    ).execute()

                    if video_response['items']:
                        duration_iso = video_response['items'][0]['contentDetails']['duration']
                        duration_min = self._parse_youtube_duration(duration_iso)

                        results.append({
                            "type": "video",
                            "title": snippet['title'],
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "duration_minutes": duration_min,
                            "description": snippet['description'][:200],
                            "thumbnail": snippet['thumbnails']['high']['url'],
                            "source": "youtube"
                        })

            logger.info(f"Found {len(results)} YouTube videos")
            return results

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            return []
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return []

    def _parse_youtube_duration(self, duration_iso: str) -> int:
        """Parse ISO 8601 duration to minutes.

        Args:
            duration_iso: Duration string like 'PT15M33S'

        Returns:
            Duration in minutes
        """
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 60 + minutes + (1 if seconds > 30 else 0)

    async def _suggest_things(
        self,
        analysis: Dict[str, Any],
        resources: List[Dict[str, Any]],
        count: int
    ) -> List[Dict[str, Any]]:
        """Suggest learning Things based on analysis and resources.

        Args:
            analysis: Interest analysis
            resources: Found resources
            count: Number of Things to suggest

        Returns:
            List of suggested Thing structures
        """
        user_message = f"""Based on this learning interest analysis and available resources,
suggest {count} distinct learning "Things" (learning modules).

Analysis:
{json.dumps(analysis, indent=2)}

Available Resources:
{json.dumps(resources[:10], indent=2)}  # Limit to first 10 resources

Each "Thing" should be a self-contained learning module with 1-5 tasks.
Each task should take 5-10 minutes.

Provide suggestions in JSON format:
{{
    "things": [
        {{
            "title": "Clear, descriptive title",
            "type": "learning_material|recipe|project|tutorial|case_study",
            "description": "What the user will learn",
            "estimated_total_time_min": number,
            "task_count": number (1-5),
            "task_outlines": [
                {{
                    "order": 1,
                    "title": "Task title",
                    "duration_min": number (5-10),
                    "content_type": "generated|video|article",
                    "resource_url": "url if using external resource, null if generated"
                }}
            ],
            "has_action_items": true|false
        }}
    ]
}}

Make Things progressive (beginner → intermediate).
Variety is important - mix different types and approaches.
"""

        response = await self._call_llm(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.7,
            max_tokens=6000
        )

        try:
            # Extract JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            result = json.loads(json_str)
            things = result.get("things", [])

            logger.info(f"Successfully parsed {len(things)} suggested Things")
            return things[:count]  # Limit to requested count

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse suggested Things: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            return []
