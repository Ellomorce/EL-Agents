"""Module for storing and retrieving agent instructions.

This module defines functions that return instruction prompts for the root agent.
These instructions guide the agent's behavior, workflow, and tool usage.
"""

def return_instructions() -> str:

    default_prompt = """
    You are a AI Agent.
    """

    return default_prompt