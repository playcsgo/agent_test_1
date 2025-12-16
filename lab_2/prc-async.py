import os
import json
import asyncio
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')
deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')

if (not openai_api_key or not deepseek_api_key):
    print(f"API keys not found at env! OpenAI: {bool(openai_api_key)}, Deepseek: {bool(deepseek_api_key)}")


request = "Give a hard question so that I can rank different LLMs."
request += "Reply me only the question, no explanation."

openai_sync = OpenAI()
question_res = openai_sync.chat.completions.create(
    model="gpt-4.1-nano",
    messages=[{"role": "user", "content": request}]
)
question = question_res.choices[0].message.content

async def ask_llm(client: AsyncOpenAI, model: str, message: list[str]):
    response = await client.chat.completions.create(
        model=model,
        messages=message
    )
    return response.choices[0].message.content.strip()

async def get_all_answers(question: str):
    message = [{"role": "user", "content": question}]

    tasks = []
    models = []

    openai_async = AsyncOpenAI()
    deepseek_async = AsyncOpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )

    for model in ["gpt-4.1-nano", "gpt-4.1-mini"]:
        tasks.append(ask_llm(openai_async, model, message))
        models.append(model)
    
    for model in ["deepseek-chat"]:
        tasks.append(ask_llm(deepseek_async, model, message))
        models.append(model)
    
    answers = await asyncio.gather(*tasks)
    
    return models, answers

models, answers = asyncio.run(get_all_answers(question))

## for check usage
# for i, (m, a) in enumerate(zip(models, answers), start=1):
#     print(f"[{i}] {m} answer:\n{a}\n")


judge_prompt = f"""
You are an expert in evaluating answers from different language models.

Rank the answers and reply in JSON with following format:
{{
  "results": ["best competitor number", "second best competitor number", "third best competitor number", ...]
}}

Question: {question}
Answers: {answers}
"""

judge_res = openai_sync.chat.completions.create(
    model="gpt-5-mini",
    messages=[{"role": "user", "content": judge_prompt}]
)

results_raw = judge_res.choices[0].message.content
results_dict = json.loads(results_raw)
ranks = results_dict["results"]

for index, result in enumerate(ranks):
    model_name = models[int(result) - 1]
    print(f"Rank {index + 1}: {model_name}")