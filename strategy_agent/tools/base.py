"""
base.py
=======
Common interface every tool implements. Enforcing this contract means the
orchestrator agent can call any tool the same way, and any tool's internal
logic (rule-based today) can later be swapped for a live LLM call (Claude /
GPT / DeepSeek) without changing the orchestrator or any other tool.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """All tools must expose a `name` and a `run(**kwargs) -> dict` method."""

    name: str = "base_tool"

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool and return a JSON-serializable dict."""
        raise NotImplementedError
