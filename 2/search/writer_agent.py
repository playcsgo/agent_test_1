from pydantic import BaseModel, Field
from agents import Agent


LLM_MODEL = 'gpt-4o-mini'

INSTRUCTIONS=(
    "You are a professional research tasked with writting a cohesive report for a research query."
    "You will be provided with the original query, and reseach summary done by research agent."
    "You should first come up with an oputline for the report that describe the structure and flow of this report."
    "Then compose the report with given materials cohesively"
    "The fianl report sould be in markdown format and it should be lengthy and detailed."
    "Aim around 5 pages and around 500-1000 words of content"
)


class ReportData(BaseModel):
    short_summary:str = Field(description="A short 2-3 sentences summary of findings.")
    markdown_report:str = Field(description="The final report")
    follow_up_questions:list[str] = Field(description="Suggestion topic for further reseach if needed.")


writer_agent = Agent(
    name="WriterAgent",
    instructions=INSTRUCTIONS,
    model=LLM_MODEL,
    output_type=ReportData,
)