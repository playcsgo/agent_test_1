# 不要在模組級別初始化瀏覽器
# 改為延遲初始化

from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import gradio as gr
import uuid
from dotenv import load_dotenv
import os
import nest_asyncio
import asyncio

# env
load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_MODEL_GPT_4O = 'gpt-4o-mini'

# 應用 nest_asyncio
nest_asyncio.apply()

# class for structured output
class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been achieved")
    user_input_needed: bool = Field(description="True if more input is needed from the user, or clarifications, or the assistant is stuck")

# add more attributes in State for pass on
class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool

# 全局變量來存儲 graph
graph = None
tools = None

async def initialize_browser_and_graph():
    """延遲初始化瀏覽器和圖"""
    global graph, tools
    
    if graph is not None:
        return graph
    
    # 創建瀏覽器和工具
    async_browser = create_async_playwright_browser(headless=False)
    toolkit = PlayWrightBrowserToolkit(async_browser=async_browser)
    tools = toolkit.get_tools()
    
    # init worker and evaluator LLM
    worker_llm = ChatOpenAI(model=LLM_MODEL_GPT_4O)
    worker_llm_with_tools = worker_llm.bind_tools(tools)
    
    evaluator_llm = ChatOpenAI(model=LLM_MODEL_GPT_4O)
    evaluator_llm_with_output = evaluator_llm.with_structured_output(EvaluatorOutput)
    
    # create worker node
    def worker(state: State) -> Dict[str, Any]:
        system_message = f"""You are a helpful assistant that can use tools to complete tasks.
        You keep working on a task until either you have a question or clarification for the user, or the success criteria is met.
        This is the success criteria:
        {state['success_criteria']}
        You should reply either with a question for the user about this assignment, or with your final response.
        If you have a question for the user, you need to reply by clearly stating your question. An example might be:

        Question: please clarify whether you want a summary or a detailed answer

        If you've finished, reply with the final answer, and don't ask a question; simply reply with the answer.
        """

        if state.get('feedback_on_work'):
            system_message += f"""
            Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
            Here is the feedback on why this was rejected:
            {state['feedback_on_work']}
            With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""
        
        # Add system message to messages for invoke
        found_system_message = False
        messages = list(state['messages'])
        for i, message in enumerate(messages):
            if isinstance(message, SystemMessage):
                messages[i] = SystemMessage(content=system_message)
                found_system_message = True
                break
            
        if not found_system_message:
            messages = [SystemMessage(content=system_message)] + messages

        # Invoke LLM
        response = worker_llm_with_tools.invoke(messages)
        
        return {'messages': [response]}

    def worker_router(state: State) -> str:
        last_message = state['messages'][-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return 'tools'
        else:
            return 'evaluator'

    def format_conversation(messages: List[Any]) -> str:
        conversation = 'Conversation history: \n\n'
        for message in messages:
            if isinstance(message, HumanMessage):
                conversation += f'User: {message.content}\n'
            elif isinstance(message, AIMessage):
                text = message.content or '[Tools use]'
                conversation += f'Assistant: {text}\n'
        
        return conversation

    def evaluator(state: State) -> Dict[str, Any]:
        last_response = state['messages'][-1].content

        system_message = """You are an evaluator that determines if a task has been completed successfully by an Assistant.
        Assess the Assistant's last response based on the given criteria. Respond with your feedback, and with your decision on whether the success criteria has been met,
        and whether more input is needed from the user."""

        user_message = f"""You are evaluating a conversation between the User and Assistant. You decide what action to take based on the last response from the Assistant.

        The entire conversation with the assistant, with the user's original request and all replies, is:
        {format_conversation(state['messages'])}

        The success criteria for this assignment is:
        {state['success_criteria']}

        And the final response from the Assistant that you are evaluating is:
        {last_response}

        Respond with your feedback, and decide if the success criteria is met by this response.
        Also, decide if more user input is required, either because the assistant has a question, needs clarification, or seems to be stuck and unable to answer without help.
        """

        if state.get('feedback_on_work'):
            user_message += f"Also, note that in a prior attempt from the Assistant, you provided this feedback: {state['feedback_on_work']}\n"
            user_message += "If you're seeing the Assistant repeating the same mistakes, then consider responding that user input is required."
        
        evaluator_messages = [SystemMessage(content=system_message), HumanMessage(content=user_message)]
        evaluate_result = evaluator_llm_with_output.invoke(evaluator_messages)

        new_state = {
            'messages': [AIMessage(
                content=f"Evaluator Feedback on this answer: {evaluate_result.feedback}"
            )],
            'feedback_on_work': evaluate_result.feedback,
            'success_criteria_met': evaluate_result.success_criteria_met,
            'user_input_needed': evaluate_result.user_input_needed
        }

        return new_state

    def evaluator_route(state: State) -> str:
        if state['success_criteria_met'] or state['user_input_needed']:
            return 'END'
        else:
            return 'worker'
    
    # init graph
    graph_builder = StateGraph(State)
    
    graph_builder.add_node('worker', worker)
    graph_builder.add_node('tools', ToolNode(tools=tools))
    graph_builder.add_node('evaluator', evaluator)
    
    graph_builder.add_conditional_edges('worker', worker_router, {'tools': 'tools', 'evaluator': 'evaluator'})
    graph_builder.add_edge('tools', 'worker')
    graph_builder.add_conditional_edges('evaluator', evaluator_route, {'worker': 'worker', 'END': END})
    graph_builder.add_edge(START, 'worker')
    
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)
    
    return graph


def make_thread_id() -> str:
    return str(uuid.uuid4())

async def process_message(message, success_criteria, history, thread):
    # 確保圖已初始化
    current_graph = await initialize_browser_and_graph()
    
    config = {'configurable': {'thread_id': thread}}

    state = {
        'messages': [HumanMessage(content=message)],
        'success_criteria': success_criteria,
        "feedback_on_work": None,
        "success_criteria_met": False,
        "user_input_needed": False
    }

    try:
        result = await current_graph.ainvoke(state, config=config)
        user = {'role': 'user', 'content': message}
        reply = {'role': 'assistant', 'content': result['messages'][-2].content}
        feedback = {'role': 'assistant', 'content': result['messages'][-1].content}

        return history + [user, reply, feedback]
    except Exception as e:
        error_msg = {'role': 'assistant', 'content': f'Error: {str(e)}'}
        return history + [{'role': 'user', 'content': message}, error_msg]

async def reset():
    return '', '', [], make_thread_id()


# launch with gradio
with gr.Blocks() as demo:
    gr.Markdown('## Sidekick Project')
    thread = gr.State(make_thread_id())

    with gr.Row():
        chatbot = gr.Chatbot(label='Sidekick', height=300)
    with gr.Group():
        with gr.Row():
            message = gr.Textbox(show_label=False, placeholder="Your request to your sidekick")
        with gr.Row():
            success_criteria = gr.Textbox(show_label=False, placeholder="What are your success criteria?")
    with gr.Row():
        reset_button = gr.Button('Reset', variant='stop')
        go_button = gr.Button('Go!', variant='primary')

    message.submit(process_message, [message, success_criteria, chatbot, thread], [chatbot])
    success_criteria.submit(process_message, [message, success_criteria, chatbot, thread], [chatbot])
    go_button.click(process_message, [message, success_criteria, chatbot, thread], [chatbot])
    reset_button.click(reset, [], [message, success_criteria, chatbot, thread])

demo.launch(theme=gr.themes.Default(primary_hue='emerald'))