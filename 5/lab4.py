from dataclasses import dataclass
from autogen_core import AgentId, MessageContext, RoutedAgent, message_handler
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.langchain import LangChainToolAdapter
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools  import Tool
from dotenv import load_dotenv
import asyncio

# # gRPC runtime 需要知道如何序列化/反序列化你的自定義
# from autogen_core._serialization import try_get_known_serializers_for_type

load_dotenv(override=True)

ALL_IN_ONE_WORKER = False


# @dataclass
# class Message:
#     content: str

from pydantic import BaseModel
class Message(BaseModel):
    content: str

# wrap serper by adapter
def adapt_tools():
    tools = []
    serper = GoogleSerperAPIWrapper()
    langchain_serper = Tool(name='internet_search', func=serper.results, description='Useful for when you need to search the internet')
    autogen_serper = LangChainToolAdapter(langchain_serper)
    tools.append(autogen_serper)
    return tools  # 還是改成用 self.autogen_serper ?

tools = adapt_tools()

INSTRUCTION_PLAYER1 = "To help with a decision on whether to use AutoGen in a new AI Agent project, \
please research and briefly respond with reasons in favor of choosing AutoGen; the pros of AutoGen."

INSTRUCTION_PLAYER2 = "To help with a decision on whether to use AutoGen in a new AI Agent project, \
please research and briefly respond with reasons against choosing AutoGen; the cons of Autogen."

INSTRUCTION_JUDGE = "You must make a decision on whether to use AutoGen for a project. \
Your research team has come up with the following reasons for and against. \
Based purely on the research from your team, please respond with your decision and brief rationale."


class Player1Agent(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')
        self._delegate = AssistantAgent(
            name,
            model_client=model_client,
            tools=tools,
            reflect_on_tool_use=True
        )
    
    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        print('Player 1 handling')
        text_message = TextMessage(content=message.content, source='user')
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)
        assert isinstance(response.chat_message, TextMessage)
        return Message(content=response.chat_message.content)


class Player2Agent(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')
        self._delegate = AssistantAgent(
            name,
            model_client=model_client,
            tools=tools,
            reflect_on_tool_use=True
        )
    
    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        print('Player 2 handling')
        text_message = TextMessage(content=message.content, source='user')
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)
        assert isinstance(response.chat_message, TextMessage)
        return Message(content=response.chat_message.content)
    

class Judge(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')
        self._delegate = AssistantAgent(name, model_client=model_client)
    
    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        message1 = Message(content=INSTRUCTION_PLAYER1)
        message2 = Message(content=INSTRUCTION_PLAYER2)
        player1 = AgentId('player1', 'A')
        player2 = AgentId('player2', 'B')

        response1 = await self.send_message(message1, player1)
        response2 = await self.send_message(message2, player2)

        result = f'Pros of AutoGen:\n{response1.content}\n\n Cons of AutoGen:\n{response2.content}\n\n'
        judge_content = f'{INSTRUCTION_JUDGE}\n{result}Response with your decision and brief explanation'
        judge_message = TextMessage(content=judge_content, source='user')

        response3 = await self._delegate.on_messages([judge_message], ctx.cancellation_token)
        assert isinstance(response3.chat_message, TextMessage)
        return Message(content=result + '\n## Decision:\n\n' + response3.chat_message.content)



# GRPC host
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost
# apply grpc runtime
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime

async def main():
    host = GrpcWorkerAgentRuntimeHost(address='localhost:50051')
    host.start()
    agent_id = None
    worker = None
    if ALL_IN_ONE_WORKER:
        worker = GrpcWorkerAgentRuntime(host_address='localhost:50051')
        # worker.add_message_serializer(try_get_known_serializers_for_type(Message))
        await worker.start()
        await Player1Agent.register(worker, 'player1', lambda: Player1Agent('player1'))
        await Player2Agent.register(worker, 'player2', lambda: Player2Agent('player2'))
        await Judge.register(worker, 'judge', lambda: Judge('judge'))
        
        agent_id = AgentId('judge', 'C-1')
    else:
        worker1 = GrpcWorkerAgentRuntime(host_address='localhost:50051')
        # worker1.add_message_serializer(try_get_known_serializers_for_type(Message))
        await worker1.start()
        await Player1Agent.register(worker1, 'player1', lambda: Player1Agent('player1'))
    
        worker2 = GrpcWorkerAgentRuntime(host_address='localhost:50051')
        # worker2.add_message_serializer(try_get_known_serializers_for_type(Message))
        await worker2.start()
        await Player2Agent.register(worker2, 'player2', lambda: Player2Agent('player2'))
        
        worker = GrpcWorkerAgentRuntime(host_address='localhost:50051')
        # worker.add_message_serializer(try_get_known_serializers_for_type(Message))
        await worker.start()
        await Judge.register(worker, 'judge', lambda: Judge('judge'))
        
        agent_id = AgentId('judge', 'C-2')
    
    response = await worker.send_message(Message(content='Go'), agent_id)
    print('<FINAL RESULT>:' + response.content)
    
    await worker.stop()
    if not ALL_IN_ONE_WORKER:
        await worker1.stop()
        await worker2.stop()
    await host.stop()

if __name__ == '__main__':
    asyncio.run(main())