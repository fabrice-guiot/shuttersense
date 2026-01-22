"""
Agent API module for distributed agent architecture.

This module provides REST endpoints for agent operations:
- Agent registration with tokens
- Heartbeat updates
- Job claiming and execution
- Progress reporting
"""

from backend.src.api.agent.routes import router

__all__ = ["router"]
