from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
import asyncio
import certifi


load_dotenv(override = True)
sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
test_eamil_address = os.environ.get('TEST_EMAIL')
test_eamil_from = os.environ.get('TEST_EMAIL_FROM')
os.environ['SSL_CERT_FILE'] = certifi.where()

# def send_test_email():
#     sg = sendgrid.SendGridAPIClient(sendgrid_api_key)
#     from_email = Email(test_eamil_address)
#     to_email = To(test_eamil_address)
#     content = Content('text/plain', 'This is a test email')
#         # text/plain: 純文字
#         # test/html: HTML 
#     mail = Mail(
#         from_email,   # 寄件者
#         to_email,     # 收件者
#         "TEST email", # title
#         content       # 內容
#         ).get()
#         ## 使用Mail helper 組成信件
#     response = sg.client.mail.send.post(request_body=mail)
#     print(response.status_code)

# send_test_email()

company_name = 'Sam AI LLT'
company_service_info = 'SaaS tool for cs2 training'

instrctions1 = f"You are a sales agent working for {company_name}, a company provides {company_service_info}. \
You are write professional, serious cold emails."

instrctions2 = f"You are a humorous and engaging sales agent working for {company_name}, a company provides {company_service_info}. \
You are write witty, engaging and humor cold emails."

instrctions3 = f"You are a busy sales agent working for {company_name}, a company provides {company_service_info}. \
You are write concise, to the point cold emails."

sales_agent1 = Agent(
    name='Professional Sales Agent',
    instructions=instrctions1,
    model='gpt-4o-mini'
)
sales_agent2 = Agent(
    name='Humor Sales Agent',
    instructions=instrctions2,
    model='gpt-4o-mini'
)
sales_agent3 = Agent(
    name='Busy Sales Agent',
    instructions=instrctions3,
    model='gpt-4o-mini'
)

message = 'write a cold salse mail'

## using tool by function_tool



@function_tool  ## pack this function to a LLM callable tool
def send_email(body: str):  ## tool name is send_email.
    """ Send out an email with the given body to all sales prospects """  ## as description
    sg = sendgrid.SendGridAPIClient(sendgrid_api_key)             ## function action
    from_email =  Email(test_eamil_address)
    to_email = To(test_eamil_address)
    content = Content('text/plain', body)

    ##.get() 會把它轉成「SendGrid API 要的 JSON payload dict」，等一下拿去當 request body
    mail = Mail(from_email, to_email, "Test Mail by Lab2", content).get()
    response = sg.client.mail.send.post(request_body=mail)
    print(response.status_code)
    return response.status_code

## Convert agent into a tool by .as_tool()
tool1 = sales_agent1.as_tool(tool_name="salse_agent1", tool_description="Generate a cold sales email as a professional salse")
tool2 = sales_agent2.as_tool(tool_name="salse_agent2", tool_description="Generate a cold sales email as a humor salse")
tool3 = sales_agent3.as_tool(tool_name="salse_agent3", tool_description="Generate a cold sales email as a busy sales")

tools1 = [tool1, tool2, tool3, send_email]



instrctions4 = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
 
Follow these steps carefully:
1. Generate Drafts: Use all three sales_agent tools to generate three different email drafts. Do not proceed until all three drafts are ready.
 
2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
 
3. Use the send_email tool to send the best email (and only the best email) to the user.
 
Crucial Rules:
- You must use the sales agent tools to generate the drafts — do not write them yourself.
- You must send ONE email using the send_email tool — never more than one.
"""


salse_manager = Agent(name="Salses Manager", instructions=instrctions4, tools=tools1, model="gpt-4o-mini")

## Create a handoffs
subject_instractions =  "You can write a subject for a cold sales email. \
You are given a message and you need to write a subject for an email that is likely to get a response."
html_instrctions = "You can convert a text email body to an HTML email body. \
You are given a text email body which might have some markdown \
and you need to convert it to an HTML email body with simple, clear, compelling layout and design."

subject_writer = Agent(name="Email subject writer", instructions=subject_instractions, model="gpt-4o-mini")
subject_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject based on mail content")

html_converter = Agent(name="HTML email body converter", instructions=html_instrctions, model="gpt-4o-mini")
html_tool = html_converter.as_tool(tool_name="html_converter", tool_description="Convert eamil into html format")

@function_tool
def send_html_email(subject: str, body: str) -> Dict[str, str]:
    """ Send out an email with the given subject and HTML body to all sales prospects """
    sg = sendgrid.SendGridAPIClient(sendgrid_api_key)
    from_email =  Email(test_eamil_from)
    to_email = To(test_eamil_address)
    content = Content('text/plain', body)
    mail = Mail(from_email, to_email, subject, content).get()
    response = sg.client.mail.send.post(request_body=mail)
    print (response.status_code)
    return response.status_code

tools2 = [subject_tool, html_tool, send_html_email]

instrctions5 = "You are an email formatter and sender. You receive the body of an email to be sent. \
You first use the subject_writer tool to write a subject for the email, then use the html_converter tool to convert the body to HTML. \
Finally, you use the send_html_email tool to send the email with the subject and HTML body."

EMAIL_MANAGER = "Email Manager"

emailier_agent = Agent(
    name=EMAIL_MANAGER,
    instructions=instrctions5,
    tools=tools2,
    model="gpt-4o-mini",
    handoff_description="Convert an email to HTML and send it"  ## let root agnet knows when can handoff task to
)

sales_manager_instructions_2 = f"""
You are a  Sales manager. Your goal is to find the single best cold sales email using the sales_agent tools.

Foolow these steps carefully:
1. Generate Drafts: Use all three sales_agent tools to generate three different email drafts. Do no process until all three draft are ready.

2. Evaluate and select: Review these draft and choose the single best mail using your judgement of which one is most like get positive feedback.
You can use tools multiple times if you are not satisfied with the results from the first try, but no more than 5 times.

3. Handoff for Sending: Pass ONLY the winnning mail draft to the {EMAIL_MANAGER} agent. The {EMAIL_MANAGER} will take care of formatting and sneding.

Crucial Rules:
- You must use the sales agent tools to generate the draft - do not write them yourself
- You must hand off exactly ONE mail to the {EMAIL_MANAGER} - no more than one.
"""

sales_manager_2 = Agent(
    name="Sales Manager 2",
    instructions=sales_manager_instructions_2,
    tools=tools1,
    handoffs=[emailier_agent],
    model="gpt-4o-mini"
)

message2 = "Send out a cold sales email addressed to Dear CEO from Alice"

async def main():

    ## single mail by streamed
    # result = Runner.run_streamed(
    #     sales_agent1,
    #     input='Write a cold sales mail'
    #     )
    
    # async for event in result.stream_events():
    #     if(
    #         event.type == 'raw_response_event'
    #         and isinstance(event.data, ResponseTextDeltaEvent)
    #     ):
    #         print(event.data.delta, end="", flush=True) 
    #             # 使用 flush = True 是立刻把buffer內容傳到terminal 避免像是卡住

    

#     with trace('Parallel cold mail'):
#         results = await asyncio.gather(
#             Runner.run(sales_agent1, message),
#             Runner.run(sales_agent2, message),
#             Runner.run(sales_agent3, message),
#         )

#     outputs = [result.final_output for result in results]

#     emails = "emails:\n\n" + "\n\n Email: \n\n".join(outputs)

#     for output in outputs:
#         print(output + '\n\n')

#     sales_picker = Agent(
#         name = 'sales_picker',
#         instructions = 'You pick the best cold sales email from the given options. \
# Imagine you are a customer and pick the one you are most likely to respond to. \
# Do not give an explanation; reply with the selected email only.',
#         model = 'gpt-4o-mini'
#     )

#     best = await Runner.run(sales_picker, emails)

    with trace("Salse Manager"):
        await Runner.run(sales_manager_2, message2)
    
if __name__ == '__main__':
    asyncio.run(main())

## note: 
# async def main() 提供 async context
# Runner.run_streamed() 拿到 stream handle
# async for event in result.stream_events() 消費事件
# asyncio.run(main()) 在腳本中啟動 event loop