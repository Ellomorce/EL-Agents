"""Academic paper abstract agent for finding new research lines"""
from google.adk import Agent
from . import prompt

MODEL = "gemini-2.5-pro"

paper_abstract_agent = Agent(
    model=MODEL,
    name="paper_abstract_agent",
    instruction=prompt.ACADEMIC_PAPER_ABSTRACTING_PROMPT,
)