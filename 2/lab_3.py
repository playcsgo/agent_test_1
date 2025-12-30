from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, trace, function_tool, OpenAIChatCompletionsModel, input_guardrail, GuardrailFunctionOutput
from typing import Dict
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
from pydantic import BaseModel
import asyncio



load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
sendgrand_api_key = os.getenv('SENDGRID_API_KEY')
sendgrid_email_from = os.environ.get('TEST_EMAIL')
sendgrid_email_to = os.environ.get('TEST_EMAIL')

if not openai_api_key:
    print('lock of OPENAI_API_KEY at .env ')
if not deepseek_api_key:
    print('lock of DEEPSEEK_API_KEY at .env ')
if not sendgrand_api_key:
    print('lock of SENDGRID_API_KEY at .env ')
if not sendgrid_email_from:
    print('lock of TEST_EMAIL at .env ')
if not sendgrid_email_to:
    print('lock of TEST_EMAIL at .env ')


## SSL certification issue
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

## wrap of Deepseek model setting
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=deepseek_api_key)
deepseek_model = OpenAIChatCompletionsModel(model='deepseek-chat', openai_client=deepseek_client)


## build email handoff
@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """ Send out an email with the given subject and HTML body to all sales prospects """
    sg = sendgrid.SendGridAPIClient(api_key=sendgrand_api_key)
    from_email = Email(sendgrid_email_from)
    to_email = To(sendgrid_email_to)
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    response = sg.client.mail.send.post(request_body=mail)
    print(response.status_code)
    return response.status_code

subject_instructions = "You can write a subject for a cold sales email. \
You are given a message and you need to write a subject for an email that is likely to get a response."

html_instructions = "You can convert a text email body to an HTML email body. \
You are given a text email body which might have some markdown \
and you need to convert it to an HTML email body with simple, clear, compelling layout and design."

subject_writer = Agent(name='Email subject writer', instructions=subject_instructions, model='gpt-4o-mini')
subject_tool = subject_writer.as_tool(tool_name='subject_writer', tool_description='Write a subject for a cold sales mail')

html_converter = Agent(name='HTML email body converter', instructions=html_instructions, model='gpt-4o-mini')
html_tool = html_converter.as_tool(tool_name='html_converter', tool_description='Convert email test into html format content')

email_tools = [subject_tool, html_tool, send_html_email]

emailer_instructions = """
You are an email formatter and sender.

You MUST do the following steps in order:
1. Use subject_writer to generate the subject.
2. Use html_converter to generate the HTML body.
3. Use send_html_email to send the email.

Do NOT explain what you are doing.
Do NOT respond with natural language.
Always finish by calling send_html_email.
"""

emailer_agent = Agent(
    name='Email Manager',
    instructions=emailer_instructions,
    tools=email_tools,
    model='gpt-4o-mini',
    handoff_description='Convert an email to HTML and send it'
)


## build of agent for sales department 
instructions1 = "You are a sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write professional, serious cold emails."

instructions2 = "You are a humorous, engaging sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write witty, engaging cold emails that are likely to get a response."

instructions3 = "You are a busy sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write concise, to the point cold emails."


sales_agent1 = Agent(
    name='Professional Sales Agent',
    instructions=instructions1,
    model='gpt-4o-mini'
)

sales_agent2 = Agent(
    name='Humorous Sales Agent',
    instructions=instructions2,
    model=deepseek_model
)

sales_agent3 = Agent(
    name='Busy Sales Agent',
    instructions=instructions3,
    model=deepseek_model
)

description = 'write a cold sales mail.'

tool1 = sales_agent1.as_tool(tool_name='sales_agent1', tool_description=description)
tool2 = sales_agent2.as_tool(tool_name='sales_agent2', tool_description=description)
tool3 = sales_agent3.as_tool(tool_name='sales_agent3', tool_description=description)

draft_generate_tools = [tool1, tool2, tool3]
handoffs = [emailer_agent]

sales_manager_instructions = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
 
Follow these steps carefully:
1. Generate Drafts: Use all three draft_generate_tools to generate three different email drafts. Do not proceed until all three drafts are ready.
 
2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
You can use the tools multiple times if you're not satisfied with the results from the first try.
 
3. Handoff for Sending: Pass ONLY the winning email draft to the 'Email Manager' agent. The Email Manager will take care of formatting and sending.
 
Crucial Rules:
- You must use the sales agent tools to generate the drafts — do not write them yourself.
- You must hand off exactly ONE email to the Email Manager — never more than one.
"""

sales_manager = Agent(
    name='Sales Manager',
    instructions=sales_manager_instructions,
    tools=draft_generate_tools,
    handoffs=handoffs,
    model='gpt-4o-mini'
)

message = 'Send a cold sales mail'

async def main():
    with trace('lab_3'):
        return await Runner.run(sales_manager, message)

if __name__ == '__main__':
    asyncio.run(main())