from pydantic import BaseModel, Field
from agents import Agent


SEARCH_ITEM_AMOUT = 5
LLM_MODEL = 'gpt-4o-mini'

INSTRUCTIONS = (
    "You are a helpful research asssistance." 
    "Jobduty is breakdown the input query into a list of search items which are the key words of this query for further web search"
    "with a specific reason."
    f"The key words should be rank as priority and the max. amount of search iterms is {SEARCH_ITEM_AMOUT}"
    )

class WebSearchItem(BaseModel):
    query: str = Field(description="The keywords breakdown from the query")
    reason: str = Field(description="The reason why this seach item is necessary for this query")

class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web seaches to perform to best answer the query")
    reason: str = Field(description="Why you choose these items as key components of this query")

planner_agent = Agent(
    name="PlannerAgent",
    instructions=INSTRUCTIONS,
    model=LLM_MODEL,
    output_type=WebSearchPlan
)