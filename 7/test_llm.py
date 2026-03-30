import os
from dotenv import load_dotenv
load_dotenv(override=True)
from openai import OpenAI

client = OpenAI(base_url='https://api.deepseek.com/v1', api_key=os.getenv('DEEPSEEK_API_KEY'))
resp = client.chat.completions.create(model='deepseek-chat', messages=[{'role': 'user', 'content': 'say hi'}])
print(resp.choices[0].message.content)