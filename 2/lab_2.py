from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
import asyncio
import certifi
import os
import certifi




load_dotenv(override = True)
sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
test_eamil_address = os.environ.get('TEST_EMAIL')
os.environ['SSL_CERT_FILE'] = certifi.where()

def send_test_email():
    sg = sendgrid.SendGridAPIClient(sendgrid_api_key)
    from_email = Email(test_eamil_address)
    to_email = To(test_eamil_address)
    content = Content('text/plain', 'This is a test email')
        # text/plain: 純文字
        # test/html: HTML 
    mail = Mail(
        from_email,   # 寄件者
        to_email,     # 收件者
        "TEST email", # title
        content       # 內容
        ).get()
        ## 使用Mail helper 組成信件
    response = sg.client.mail.send.post(request_body=mail)
    print(response.status_code)

send_test_email()