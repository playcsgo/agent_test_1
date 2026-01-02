import sendgrid 
from sendgrid.helpers.mail import Email, To, Mail, Content
from agents import Agent, function_tool
from dotenv import load_dotenv
import os
from typing import Dict
import certifi


os.environ['SSL_CERT_FILE'] = certifi.where()
load_dotenv(override=True)

sendgrand_api_key = os.getenv('SENDGRID_API_KEY')
sendgrid_email_from = os.environ.get('TEST_EMAIL')
sendgrid_email_to = os.environ.get('TEST_EMAIL')


@function_tool
def send_email(subject:str, html_body:str) -> Dict[str, str]:
    sg = sendgrid.SendGridAPIClient(sendgrand_api_key)
    from_email = Email(sendgrid_email_from)
    to_email = To(sendgrid_email_to)
    content= Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    res =sg.client.mail.send.post(request_body=mail)
    print("mail process", res.status_code)
    return res.status_code

INSTRUCTIONS =  """You are able to send a nicely formatted HTML email based on a detailed report.
You will be provided with a detailed report. You should use your tool to send one email, providing the 
report converted into clean, well presented HTML with an appropriate subject line."""
LLM_MODEL = 'gpt-4o-mini'

email_agent = Agent(
    name='EmailAgent',
    instructions=INSTRUCTIONS,
    tools=[send_email],
    model=LLM_MODEL,
)