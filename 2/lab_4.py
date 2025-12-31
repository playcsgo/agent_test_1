from agents import Agent, Runner, trace, gen_trace_id, function_tool, WebSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import asyncio
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Dict

## SSL certification issue
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()


load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')
deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
sendgrand_api_key = os.getenv('SENDGRID_API_KEY')
sendgrid_email_from = os.environ.get('TEST_EMAIL')
sendgrid_email_to = os.environ.get('TEST_EMAIL')

GPT_MINI = 'gpt-4o-mini'

## Make a search Planner
MAX_SEARCH_ATTEMP = 3

planner_instructions = f"You are a helpful research assistant. Given a query, come up with a set of web searches \
to perform to best answer the query. Output {MAX_SEARCH_ATTEMP} terms to query for."

# Field 等於是給 LLM 看的 instruction. 
class WebSeachItem(BaseModel):
    reason: str = Field(description='Your reasoning for why this search is important to the query.')
    query: str = Field(description='The search term to use for the web search.')

class WebSearchPlan(BaseModel): 
    searches: list[WebSeachItem] = Field(description='The list of web searches to perform to best answer the query.')

planner_agent = Agent(
    name='Planner Agent',
    instructions=planner_instructions,
    model=GPT_MINI,
    output_type=WebSearchPlan
)


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

## Report writer
report_writer_instructions = ( ## () for change to next line with \n
    "You are a senior researcher tasked with writing a cohesive report for a research query. "
    "You will be provided with the original query, and some initial research done by a research assistant."
    "You should first come up with an outline for the report that describes the structure and "
    "flow of the report. Then, generate the report and return that as your final output."
    "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
    "for 5-10 pages of content, at least 1000 words."
)

class ReportData(BaseModel):
    short_summary: str = Field(description='2 to 3 sentences of summary of the findings')
    markdown_report: str = Field(description='The final report')
    follow_up_questions: list[str] = Field(description='Suggestion topics to research further, max 3')


report_writer_agent = Agent(
    name='Report Agent',
    instructions=report_writer_instructions,
    model=GPT_MINI,
    output_type=ReportData
)

## Email Agent as tool
@function_tool
def send_email_tool(subject:str, html_body: str) -> Dict[str, str]:
    sg = sendgrid.SendGridAPIClient(sendgrand_api_key)
    from_email = Email(sendgrid_email_from)
    to_email = To(sendgrid_email_to)
    content = Content('text/html', html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return 'success'

emailer_instructions = """You are able to send a nicely formatted HTML email based on a detailed report.
You will be provided with a detailed report. You should use your tool to send one email, providing the 
report converted into clean, well presented HTML with an appropriate subject line."""

email_agent = Agent(
    name='Email Agent',
    instructions=emailer_instructions,
    tools=[send_email_tool],
    model=GPT_MINI
)


## async function for parallel search 
async def plan_searches(query:str):
    """Apply planner agent to generate searching topics list"""
    print('planning')
    result = await Runner.run(planner_agent, f"Query: {query}")
    print(f"searching list: {result.final_output.searches}")
    return result.final_output

async def search(item: WebSeachItem):
    """Apply search agent for WebSearchTool"""
    print(f"searching {item.query}")
    message = f"Seach item: {item.query}, Reason of this item: {item.reason}"
    result = await Runner.run(search_agent, message)
    print(f"{item.query} seaching done")

    return result.final_output

async def perfrom_seaches(search_plan: WebSearchPlan):
    """call seach() for each item in seach_plan"""
    print('start searching...')
    task = [asyncio.create_task(search(item)) for item in search_plan.searches]
    results = await asyncio.gather(*task)
    print('all searching task done')
    
    return results


## report writer and send email
async def write_report(query:str, search_results: list[str]):
    """Apply report writer agent for generate report"""
    print('generating report...')
    message = f"Original Query: {query}. Summary search results: {search_results}"
    result = await Runner.run(report_writer_agent, message)
    print('report done')
    return result.final_output

async def send_email(report: ReportData):
    """Apply emailer agent to send a mail"""
    print('writing email...')
    result = await Runner.run(email_agent, report.markdown_report)
    print('Email sent')

    return report


## Conduct
query = "Latest AI Agent frameworks in 2025"

async def main():
    with trace('lab_4 deep search-1'):
        search_plan = await plan_searches(query)
        search_results = await perfrom_seaches(search_plan)
        report = await write_report(query, search_results)
        await send_email(report)
        print('process done')

if __name__ == '__main__':
    asyncio.run(main())