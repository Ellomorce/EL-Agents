"""Academic_websearch_agent for finding research papers using search tools."""
from google.adk import Agent
from google.adk.tools import google_search
from . import prompt

MODEL = "gemini-2.5-pro"

academic_websearch_agent = Agent(
    model=MODEL,
    name="academic_websearch_agent",
    instruction=prompt.ACADEMIC_WEBSEARCH_PROMPT,
    output_key="recent_citing_papers",
    tools=[google_search],
)