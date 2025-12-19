from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import gradio as gr
import os
import json
from pydantic import BaseModel, ValidationError #used to validate input/output data as schema check


load_dotenv(override=True)
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

openai = OpenAI()
deepseek = OpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )

pdf_info = PdfReader("info/sam_linkedin.pdf")
linkedin_text = ""
for page in pdf_info.pages:
    text =  page.extract_text()
    if text:
        linkedin_text += text

with open("info/summary.txt", encoding="utf-8") as f:
    summary = f.read()

name = "Sam Lu"

system_prompt = f"You are acting as {name}. You are answering questions on {name}'s website, \
particularly questions related to {name}'s career, background, skills and experience. \
Your responsibility is to represent {name} for interactions on the website as faithfully as possible. \
You are given a summary of {name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer, say so."

system_prompt += f"\n\n## Summary:\n{summary}\n\n## LinkedIn Profile:\n{linkedin_text}\n\n"
system_prompt += f"With this context, please chat with the user, always staying in character as {name}."

system_prompt

## for chat without evaluation
# def chat(message, history):
#     messages = [{"role": "system", "content": system_prompt}]+ history + [{"role": "user", "content": message}]
#     response = openai.chat.completions.create(model="gpt-4.1-nano", messages=messages)
#     return response.choices[0].message.content

# gr.ChatInterface(chat).launch() # for gradio 5.xx



## todo: 改成 async + streaming（真正商用寫法）

class Evaluation(BaseModel):
    is_acceptable: bool
    feedback: str

evaluator_system_prompt = f"You are an evaluator that decides whether a response to a question is acceptable. \
You are provided with a conversation between a User and an Agent. Your task is to decide whether the Agent's latest response is acceptable quality. \
The Agent is playing the role of {name} and is representing {name} on their website. \
The Agent has been instructed to be professional and engaging, as if talking to a potential client or future employer who came across the website. \
The Agent has been provided with context on {name} in the form of their summary and LinkedIn details. Here's the information: \
Criteria: \
- Professional \
- Clear \
- Appropriate for a personal / carrer website \
You MUST return ONLY valid JSON and DO NOT include any explanations and markdown of the JSON" 

evaluator_system_prompt += f"\n\n## Summary:\n{summary}\n\n## LinkedIn Profile:\n{linkedin_text}\n\n"
evaluator_system_prompt += f"With this context, please evaluate the latest response, replying with whether the response is acceptable and your feedback."

def generate_evaluator_user_prompt(reply: str, message: str, history):
    return f"""
You MUST reply in valid JSON with EXACTLY this schema:

{{
  "is_acceptable": boolean,
  "feedback": string
}}

Do not rename fields.
Do not add extra fields.

Conversation history:
{history}

User message:
{message}

Agent reply:
{reply}
"""



def evaluate(reply, message, history) -> Evaluation:
    messages = [{"role": "system", "content": evaluator_system_prompt}] + [{"role": "user", "content": generate_evaluator_user_prompt(reply, message, history)}]
    response = deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
        return Evaluation.model_validate(data)
    
    except (json.JSONDecodeError, ValidationError) as e:
        return Evaluation(
            is_acceptable=False,
            feedback=f"Evaluation response is not valid JSON or does not conform to schema: {str(e)}"
        )


evaluate_message = [{"role": "system", "content": system_prompt}] + [{"role": "user", "content": "do you hold a patent?"}] # doyou hold a patent? is an example for reject.
response = openai.chat.completions.create(model="gpt-4.1-nano", messages=evaluate_message)
reply = response.choices[0].message.content



evaluate(reply, "do you hold a patent?", evaluate_message[:1])


def retry(reply, message, history, feedback):
    updated_system_prompt = system_prompt + "\n\n## Previous answer rejected\nYou just tried to reply, but the quality control rejected your reply\n"
    updated_system_prompt += f"## Your attempted answer:\n{reply}\n\n"
    updated_system_prompt += f"## Reason for rejection:\n{feedback}\n\n"
    messages = [{"role": "system", "content": updated_system_prompt}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model="gpt-4.1-nano", messages=messages)
    
    return response.choices[0].message.content

def chat_with_evaluation(message, history):
    if "patent" in message:
        system = system_prompt + "\n\nEverything in your reply needs to be pig latin - \
            it is mandatory taht you respond only entirely ih pig latin"
    else:
        system = system_prompt

    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model="gpt-4.1-nano", messages=messages)
    reply = response.choices[0].message.content

    evaluation = evaluate(reply, message, history)

    if evaluation.is_acceptable:
        print("==Answer accepted==")
    else:
        print("X Answer rejected, retrying... X")
        print(f"Feedback: {evaluation.feedback}")
        reply = retry(reply, message, history, evaluation.feedback)
    return reply

gr.ChatInterface(chat_with_evaluation).launch()