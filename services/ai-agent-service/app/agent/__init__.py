"""
AI Agent Module

Core components for SelfMate AI Agent:
- SelfMateAgent: Main AI agent with personality and capabilities
- ConversationManager: Advanced conversation management
"""

from .selfmate_agent import SelfMateAgent
from .conversation_manager import ConversationManager

__all__ = [
    "SelfMateAgent",
    "ConversationManager"
]