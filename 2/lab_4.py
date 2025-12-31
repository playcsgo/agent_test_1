from agents import Agent, Runner, trace, gen_trace_id, function_tool, WebSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import asyncio
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content


load_dotenv(override=True)
GPT_MINI = 'gpt-4o-mini'


## OpenAI Hosted Tools
    # WebSearchTool

search_instructions = "You are a research assistant. Given a search term, you search the web for that term and \
produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 \
words. Capture the main points. Write succintly, no need to have complete sentences or good \
grammar. This will be consumed by someone synthesizing a report, so it's vital you capture the \
essence and ignore any fluff. Do not include any additional commentary other than the summary itself."

search_agent = Agent(
    name='Search Agent',
    instructions=search_instructions,
    tools=[WebSearchTool(search_context_size='low')],
    model=GPT_MINI,
    model_settings=ModelSettings(tool_choice='required') ## to force agent use WebSearchTool
)

message1 = "Latest AI Agent frameworks in 2025"

async def main():
    with trace('lab_4 deep search-1'):
        result = await Runner.run(search_agent, message1)
    print(result.final_output)

if __name__ == '__main__':
    asyncio.run(main())