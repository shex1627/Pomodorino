"""Base agent class for all LLM-powered agents."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import anthropic
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all LLM agents in the system."""

    def __init__(self, model: Optional[str] = None):
        """Initialize the agent with LLM client.

        Args:
            model: Optional model override. Defaults to configured model.
        """
        self.model = model or settings.anthropic_model
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        logger.info(f"Initialized {self.__class__.__name__} with model {self.model}")

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's primary function.

        Args:
            input_data: Input parameters for the agent

        Returns:
            Dictionary containing agent's output
        """
        pass

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Call LLM with the given prompts.

        Args:
            system_prompt: System-level instruction for the LLM
            user_message: User message/query
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            LLM response text
        """
        try:
            logger.debug(f"Calling LLM with model {self.model}")
            logger.debug(f"System prompt length: {len(system_prompt)} chars")
            logger.debug(f"User message length: {len(user_message)} chars")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )

            result = response.content[0].text
            logger.debug(f"LLM response length: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise

    def _build_prompt(self, template: str, **kwargs) -> str:
        """Build a prompt from template and variables.

        Args:
            template: Prompt template with {variable} placeholders
            **kwargs: Variables to substitute into template

        Returns:
            Formatted prompt string
        """
        return template.format(**kwargs)
