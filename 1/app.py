from openai import OpenAI
import json
import os
import requests ## for HTTP request
from pypdf import PdfReader
import gradio as gr
from dataclasses import dataclass
from typing import Callable, Dict, Any
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR
INFO_DIR = PROJECT_ROOT

openai = OpenAI()
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json" ## Pushover API endpoint

## check env 
if not pushover_user:
    print("Lack of PUSHOVER_USER in .env")
if not pushover_token:
    print("Lack of PUSHOVER_TOKEN in .env")

def push (message):
    try: 
        if not pushover_user or not pushover_token:
            print("LACK of PUSHOVER_USER or PUSHOVER_TOKEN")
            return

        print(f"Push: {message}")
        payload = {"user": pushover_user, "token": pushover_token, "message": message}
        requests.post(pushover_url, data=payload)
    except Exception as e:
            print("Push failed:", e)

def record_user_details(email, name="Name not Provided", notes="Note not provided"):
    push (f"Recording interest from {name}, with email {email} and notes {notes}")
    return {"requested": "ok"}

def record_unknown_question(question):
    push (f"Unknown question received: {question}")
    return {"recorded": "ok"}

## Define available tools for this agent, like RBAC allowed actions.
## 且使用 toolwhite list的寫法
@dataclass
class Tool_Spec:
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable

TOOLS = [
    Tool_Spec(
        name= "record_user_details",
        description= "Use this tool to record that a user is interested in being in touch and provided an email address",
        parameters = {
            "type": "object",
            "properties": {
                "email": { "type": "string" },
                "name": { "type": "string" },
                "notes": { "type": "string" },
            },
            "required": ["email"],
            "additionalProperties": False,
        },
        func=record_user_details,
    ),
    Tool_Spec(
        name="record_unknown_question",
        description="Record unanswered question",
        parameters={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
        func=record_unknown_question,
    ),
]

# Comprehension 語法糖
openai_tools = [
    {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        },
    }
    for t in TOOLS
]

TOOL_REGISTRY = {t.name: t.func for t in TOOLS}



# record_user_details_json = {
#     "name": "record_user_details",
#     "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "email": {
#                 "type": "string",
#                 "description": "The email address of this user"
#             },
#             "name": {
#                 "type": "string",
#                 "description": "The user's name, if they provided it"
#             }
#             ,
#             "notes": {
#                 "type": "string",
#                 "description": "Any additional information about the conversation that's worth recording to give context"
#             }
#         },
#         "required": ["email"],
#         "additionalProperties": False
#     }
# }

# record_unknown_question_json = {
#     "name": "record_unknown_question",
#     "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "question": {
#                 "type": "string",
#                 "description": "The question that couldn't be answered"
#             },
#         },
#         "required": ["question"],
#         "additionalProperties": False
#     }
# }




## 直接使用 if 來指派不同函數的(tool)的使用. 這個是最基本也是最可讀的方法
# def handle_tool_calls(tool_calls):
#     results = []
#     for tool_call in tool_calls:
#         tool_name = tool_call.function.name
#         arguments = json.loads(tool_call.function.arguments)
#         print(f"Tool called: {tool_name}")

#         if tool_name == "record_user_details":
#             result = record_user_details(**arguments)
#         elif tool_name == "record_unknown_question":
#             result = record_unknown_question(**arguments)
        
#         results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
#     return results


## 使用 globals 處理 tool_handle (危險)
# 使用 globals 執行 record_unknow_question
# 等於 record_unknown_question("this is a really hard question")
# globals()["record_unknow_question"]("this is a really hard question")


# def handle_tool_calls(tool_calls):
#     results = []
#     for tool_call in tool_calls:
#         tool_name =  tool_call.function.name
#         arguments = json.loads(tool_call.function.arguments)
#         print(f"Tool called: {tool_name}")

#         tool = globals().get(tool_name) ## using globals is dangerous, need to use registered tools as tool whitelist. 
#         result = tool(**arguments) if tool else {}
#         results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
    
#     return results




def handle_tool_calls(tool_calls):
    results = []

    for tool_call in tool_calls:
        tool_name =  tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}")

        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            raise ValueError(f"unknown tool: {tool_name}") # 等同於throw
        
        result = tool(**arguments)
        results.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id
        })
    return results

pdf_info = PdfReader("./info/sam_linkedin.pdf")
linkedin_text = ""
for page in pdf_info.pages:
    text =  page.extract_text()
    if text:
        linkedin_text += text

with open("./info/summary.txt", encoding="utf-8") as f:
    summary = f.read()

name = "Sam Lu"

system_prompt = f"You are acting as {name}. You are answering questions on {name}'s website, \
particularly questions related to {name}'s career, background, skills and experience. \
Your responsibility is to represent {name} for interactions on the website as faithfully as possible. \
You are given a summary of {name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

system_prompt += f"\n\n## Summary:\n{summary}\n\n## LinkedIn Profile:\n{linkedin_text}\n\n"
system_prompt += f"With this context, please chat with the user, always staying in character as {name}."

MAX_TOOL_ITERATIONS = 5
def chat(message, history):
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]

    too_iterations = 0
    
    while True:
        response = openai.chat.completions.create(model="gpt-4o-mini", messages = messages, tools = openai_tools)
        finish_reason = response.choices[0].finish_reason # finish_reason naming 是SPEC寫死的嗎?

        choice = response.choices[0]

        if finish_reason == "tool_calls":
            too_iterations += 1
            if too_iterations > MAX_TOOL_ITERATIONS:
                raise RuntimeError("Tool excess maximum retry")

            assistant_message = choice.message # response.choices 裡面有哪些東西?
            messages.append(assistant_message)

            tool_calls = assistant_message.tool_calls
            results = handle_tool_calls(tool_calls)
            messages.extend(results) # list.extend 語法
        else:
            return response.choices[0].message.content


demo = gr.ChatInterface(chat)
demo.queue()
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
)
