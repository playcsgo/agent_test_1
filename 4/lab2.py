from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
import gradio as gr
import os
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import GoogleSerperAPIWrapper
import requests

load_dotenv(override=True)
serper = GoogleSerperAPIWrapper()
pushover_token=os.getenv("PUSHOVER_TOKEN")
pushover_user=os.getenv("PUSHOVER_USER")
pushover_url =os.getenv("PUSHOVER_URL")

tool_search = Tool(
    name='search',
    func=serper.run,
    description='useful for when you need to answer questions about current events or find specific information on the web',
)

def push(text: str):
    requests.post(
        pushover_url,
        data={
            'token': pushover_token,
            'user': pushover_user,
            'message': text,
        })

tool_push = Tool(
    name='send_push_notification',
    func=push,
    description='useful for sending a push notification to your mobile device with a custom message',
)

my_tools = [tool_search, tool_push]

# Apply Graph 5 steps
class State(TypedDict):
    messages: Annotated[list, add_messages]

# graph_builder =  StateGraph[State, None, State, State](State)
graph_builder = StateGraph(State)

# 建立 llm 抽象層
llm = ChatOpenAI(model='gpt-4o-mini')

# 有哪些tools可以使用
llm_with_tools = llm.bind_tools(my_tools)

def chatbot(state: State)-> State:
    return {'messages': [llm_with_tools.invoke(state['messages'])]}

# add a tool_node
graph_builder.add_node('chatbot', chatbot)
graph_builder.add_node('tools', ToolNode(tools=my_tools))

# 判斷是否使用工具 tools_condition為條件函數
graph_builder.add_conditional_edges('chatbot', tools_condition, 'toolss')

graph_builder.add_edge('tools', 'chatbot')
graph_builder.add_edge(START, 'chatbot')

graph = graph_builder.compile()
print(graph.get_graph().draw_ascii())


def chat(user_input: str, history: str):
    result = graph.invoke({
        'messages': [{
            'role': 'user',
            'content': user_input
        }]
    })
    return result['messages'][-1].content

gr.ChatInterface(chat).launch()

## check mermaid png
# import io
# from PIL import Image
# png_data = graph.get_graph().draw_mermaid_png()
# img = Image.open(io.BytesIO(png_data))
# img.show() 