from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field
from sidekick_tools import playwright_tools, other_tools
import uuid
import asyncio
from datetime import datetime

load_dotenv(override=True)

class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool


class EvaluatorOutput(BaseModel):
    success_criteria_met: bool = Field(description="Whether the success criteria were met or not")
    feedback: str = Field(description="Feedback on the work done, if any")
    user_input_needed: bool = Field(description="Whether user input is needed to proceed or not")


class Sidekick:
    def __init__(self):
        # announce global variables
        self.worker_llm_with_tools =None
        self.evaluator_llm_with_structured_output = None
        self.graph = None
        self.tools = None
        self.llm_with_tools = None
        self.sidekick_id = str(uuid.uuid4())[:8]
        self.memory = MemorySaver()
        self.browser = None
        self.playwright = None
        self.GPT_MODEL = 'gpt-4o-mini'
    
    async def setup(self):
        self.tools, self.browser, self.playwright = await playwright_tools()
        self.tools += await other_tools()
        # worker_llm = ChatOpenAI(model=self.GPT_MODEL)
        # self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)
        self.worker_llm_with_tools = ChatOpenAI(model=self.GPT_MODEL).bind_tools(self.tools)
        # evaluator_llm = ChatOpenAI(model=self.GPT_MODEL)
        # self.evaluator_llm_with_structured_output = evaluator_llm.with_structured_output(EvaluatorOutput)
        self.evaluator_llm_with_structured_output = ChatOpenAI(model=self.GPT_MODEL).with_structured_output(EvaluatorOutput)
        await self.build_graph()

    def worker(self, state: State) -> Dict[str, Any]:
        system_message = f"""You are a helpful assistant that can use tools to complete tasks.
    You keep working on a task until either you have a question or clarification for the user, or the success criteria is met.
    You have many tools to help you, including tools to browse the internet, navigating and retrieving web pages.
    You have a tool to run python code, but note that you would need to include a print() statement if you wanted to receive output.
    The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    This is the success criteria:
    {state["success_criteria"]}
    You should reply either with a question for the user about this assignment, or with your final response.
    If you have a question for the user, you need to reply by clearly stating your question. An example might be:

    Question: please clarify whether you want a summary or a detailed answer

    If you've finished, reply with the final answer, and don't ask a question; simply reply with the answer.
    """
        
        if state.get('feedback_on_work'):
            system_message += f"""
    Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
    Here is the feedback on why this was rejected:
    {state["feedback_on_work"]}
    With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""
            
        # Add in the system message
        found_system_message = False
        messages = state['messages']
        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                found_system_message = True
            
        if not found_system_message:
            # messages.insert(0, SystemMessage(content=system_message))
            messages = [SystemMessage(content=system_message)] + messages

        # invoke LLM with tools with modified messages
        response = self.worker_llm_with_tools.invoke(messages)

            # Return updated state
        return { 'messages': [response] }

    def work_router(self, state: State) -> str:
        last_message = state['messages'][-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return 'tools'
        else:
            return 'evaluator'
    
    def format_conversation(self, messages: List[Any]) -> str:
        conversation =  'Conversation history: \n\n'
        for message in messages:
            if isinstance(message, HumanMessage):
                conversation += f'User: {message.content}\n'
            elif isinstance(message, AIMessage):
                text = message.content or '[Tools use]'
                conversation += f'Assistant: {text}\n'
        return conversation

    def evaluator(self, state: State) -> State:
        last_response = state['messages'][-1].content

        system_message = """You are an evaluator that determines if a task has been completed successfully by an Assistant.
    Assess the Assistant's last response based on the given criteria. Respond with your feedback, and with your decision on whether the success criteria has been met,
    and whether more input is needed from the user."""

        user_message = f"""You are evaluating a conversation between the User and Assistant. You decide what action to take based on the last response from the Assistant.

    The entire conversation with the assistant, with the user's original request and all replies, is:
    {self.format_conversation(state["messages"])}

    The success criteria for this assignment is:
    {state["success_criteria"]}

    And the final response from the Assistant that you are evaluating is:
    {last_response}

    Respond with your feedback, and decide if the success criteria is met by this response.
    Also, decide if more user input is required, either because the assistant has a question, needs clarification, or seems to be stuck and unable to answer without help.

    The Assistant has access to a tool to write files. If the Assistant says they have written a file, then you can assume they have done so.
    Overall you should give the Assistant the benefit of the doubt if they say they've done something. But you should reject if you feel that more work should go into this.
    """
        if state['feedback_on_work']:
            user_message += f"Also, note that in a prior attempt from the Assistant, you provided this feedback: {state['feedback_on_work']}\n"
            user_message += "If you're seeing the Assistant repeating the same mistakes, then consider responding that user input is required."

        evauator_message = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        eval_result = self.evaluator_llm_with_structured_output.invoke(evauator_message)

        new_state = {
            'messages': [
                {
                    'role': 'assistant',
                    'content': f'Evaluator Feedback on this answer: {eval_result.feedback}.'
                }
            ],
            'feedback_on_work': eval_result.feedback,
            'success_criteria_met': eval_result.success_criteria_met,
            'user_input_needed': eval_result.user_input_needed
        }
        return new_state
    
    def route_based_on_evaluation(self, state: State) -> str:
        if state['success_criteria_met'] or state['user_input_needed']:
            return 'END'
        else:
            return 'worker'
    
    async def build_graph(self):
        # 1. Setup Graph with State
        graph_builder = StateGraph(State)

        # 2. Add nodes
        graph_builder.add_node('worker', self.worker)
        graph_builder.add_node('tools', ToolNode(tools=self.tools))
        graph_builder.add_node('evaluator', self.evaluator)

        # 3. Add edges
        graph_builder.add_conditional_edges(
            'worker', self.work_router, {
                'tools': 'tools',
                'evaluator': 'evaluator'
            }
        )
        graph_builder.add_edge('tools', 'worker')
        graph_builder.add_conditional_edges(
            'evaluator', self.route_based_on_evaluation, {
                'worker': 'worker',
                'END': END
            }
        )
        graph_builder.add_edge(START, 'worker')

        # 4. compile graph
        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message, success_criteria, history):
        config = { 'configurable': {'thread_id': self.sidekick_id} }

        state = {
            'messages': message,
            'success_criteria': success_criteria or 'The answer should be correct and complete based on the user\'s request',
            'feedback_on_work': None,
            'success_criteria_met': False,
            'user_input_needed': False
        }

        result = await self.graph.ainvoke(state, config=config)
        user = {'role': 'user', 'content': message}
        reply = {'role': 'assistant', 'content': result['messages'][-2].content}
        feedback = {'role': 'assistant', 'content': result['messages'][-1].content}

        return history + [user, reply, feedback]
    
    def cleanup(self):
        if self.browser:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.browser.close())
                if self.playwright:
                    loop.create_task(self.playwright.stop())
            except RuntimeError:
                asyncio.run(self.browser.close())
                if self.playwright:
                    asyncio.run(self.playwright.stop())