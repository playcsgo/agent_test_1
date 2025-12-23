from dotenv import load_dotenv
import os
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')
if (api_key):
    print(f"api_key exists, starts with {api_key[:5]}")
else:
    print("api_key does not exist!")

openai = OpenAI()
msg1 = [{"role": "user", "content": "Now, What business area is most worth exploring Agentic AI for profit? Just reply me the most profitable one."}]
res1 = openai.chat.completions.create(
    model="gpt-4.1-nano",
    messages=msg1
)

indusctry = res1.choices[0].message.content
msg2 =f"In industry: {indusctry}, what is the most pain point which can solved by Agentic AI? Just reply me the pain point, no solution required." 
res2 =openai.chat.completions.create(
    model="gpt-4.1-nano",
    messages = [{"role": "user", "content": msg2}]
)

pain_point = res2.choices[0].message.content
msg3 = f"Provide one profiable business model to sovle this pain point: {pain_point} in industry: {indusctry} by using Agentic AI. Just reply me the business model, no explanation required."
res3 = openai.chat.completions.create(
    model="gpt-4.1-nano",
    messages = [{"role": "user", "content": msg3}]
)
business_model = res3.choices[0].message.content

print("Industry:", indusctry)
print("Pain-point:", pain_point)
print("Pain-point:", business_model)