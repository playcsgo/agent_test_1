from typing import Annotated
from pydantic import BaseModel
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
import gradio as gr
import random

load_dotenv(override=True)

# pool for foo
nouns =['cat', 'dog', 'car', 'house', 'tree']
adjectives = ['big', 'small', 'red', 'fast', 'bright']

# step 1 - define state class
class State(BaseModel):
    messages: Annotated[list, add_messages]

# step 2 - start graph_builder with state class
graph_builder = StateGraph[State, None, State, State](State)

# step 3 - create a node
def first_node(old_state: str) -> State:
    reply = f'{random.choice(nouns)} are {random.choice(adjectives)}.'
    messages = [{'role': 'assistant', 'content': reply}]

    new_state = State(messages=messages)

    return new_state
graph_builder.add_node('first_node', first_node)

# step 4 - create Edges to define flow
graph_builder.add_edge(START, 'first_node')
graph_builder.add_edge('first_node', END)

# step 5 - compile the graph
graph = graph_builder.compile()


def chat(user_input: str, history: str):
    message = {'role': 'user', 'content': user_input}
    messages = [message]
    state = State(messages=messages)
    result = graph.invoke(state)
    print(result)

    return result['messages'][-1].content

print(graph.get_graph().draw_ascii())

gr.ChatInterface(chat).launch()