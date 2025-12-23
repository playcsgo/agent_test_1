from dotenv import load_dotenv
import os
import json
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')
deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')

if (not openai_api_key or not deepseek_api_key):
    print(f"API keys not found at env! OpenAI: {bool(openai_api_key)}, Deepseek: {bool(deepseek_api_key)}")

request = "Give a hard question so that I can rank different LLMs."
request += "Reply me only the question, no explanation."

answers = []
models = []

# Get a quesiton for test LLMs
openai = OpenAI()
model = "gpt-4.1-nano"
response = openai.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": request}]
)
question = response.choices[0].message.content

msg = [{"role": "user", "content": question}]


# Get answers from different LLMs
openai = OpenAI()
model = "gpt-4.1-nano"
response = openai.chat.completions.create(
    model=model,
    messages=msg
)
answers.append(response.choices[0].message.content)
models.append(model)

openai = OpenAI()
model = "gpt-4.1-mini"
response = openai.chat.completions.create(
    model=model,
    messages=msg
)
answers.append(response.choices[0].message.content)
models.append(model)


deepseek = OpenAI(
    api_key=deepseek_api_key,
    base_url="https://api.deepseek.com/v1",
)
model = "deepseek-chat"

response = deepseek.chat.completions.create(
    model=model,
    messages=msg
)
answers.append(response.choices[0].message.content)
models.append(model)

judege_prompt = f"""You are an expert in evaluating answers from different language models. Rank the answers and reply in JSON with following format:
{{"results": ["best competitor number", "second best competitor number", "third best competitor number", ...]}}

questions: {question}
answers: {answers}
"""

# Judge the answers
openai = OpenAI()
model = "gpt-5-mini"
messages = [{"role": "user", "content": judege_prompt}]
response = openai.chat.completions.create(
    model=model,
    messages=messages
)
results = response.choices[0].message.content
results_dict = json.loads(results)
ranks = results_dict["results"]

for index, result in enumerate(ranks):
    model = models[int(result) - 1]
    print(f"Rank {index + 1}: {model}")
