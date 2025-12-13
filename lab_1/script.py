from dotenv import load_dotenv

load_dotenv(override=True)

import os
openai_api_key = os.getenv('OPENAI_API_KEY')

if(openai_api_key):
    print(f"OpenAI API KEY is exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API KEY is not exists")

from openai import OpenAI
openai = OpenAI()
messages1 =  [{"role": "user", "content": "what is 2+2?"}]

response1 = openai.chat.completions.create(
    model= "gpt-4.1-nano",
    messages = messages1
)
print(response1.choices[0].message)
print('---------------------')

quesiton = "please propse a hard, challenging question to assess someone's IQ. Respond only with the question."
messages2 =  [{"role": "user", "content": quesiton}]
response2 = openai.chat.completions.create(
    model= "gpt-4.1-nano",
    messages = messages2
)
generated_question = response2.choices[0].message.content
print("Generated question:", generated_question)

message3 = [{"role": "user", "content": generated_question}]
response3 = openai.chat.completions.create(
    model= "gpt-4.1-nano",
    messages = message3
)

print('---------------------')

generated_answer = response3.choices[0].message.content

from rich.console import Console
from rich.markdown import Markdown

console = Console()
console.print(Markdown(generated_answer))

print('=== script1.py done ===')