"""
Menu Chat Agent — ADK LlmAgent definition.

This file is pure wiring: it connects the prompt, tools, and model.
- Prompt lives in: agents/prompts/menu_chat.py
- Tools live in:   agents/tools.py
- Model name from: helpers/config.py
- LiteLlm wraps the model for OpenAI provider routing
"""

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from src.agents.prompts.menu_chat import MENU_CHAT_INSTRUCTION, MENU_CHAT_DESCRIPTION
from src.agents.tools import search_menu, get_menu_items
from src.helpers.config import get_settings

settings = get_settings()

root_agent = LlmAgent(
    name="MenuChatAgent",
    model=LiteLlm(model=f"openai/{settings.OPENAI_CHAT_MODEL}"),
    instruction=MENU_CHAT_INSTRUCTION,
    description=MENU_CHAT_DESCRIPTION,
    tools=[search_menu, get_menu_items],
)
