from dataclasses import dataclass
from autogen_core import AgentId, MessageContext, RoutedAgent, message_handler
from autogen_core import SingleThreadedAgentRuntime
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import asyncio

load_dotenv(override=True)


@dataclass
class Message:
    content: str


class SimpleAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__('Simple')
    
    @message_handler
    async def on_my_message(self, message: Message, ctx: MessageContext) -> Message:
        return Message(content= f'This is {self.id.type}-{self.id.key}. You said "{message.content}" and I disagree.')


class MyLLMAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__('LLMAgent')
        model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')
        self._delegate = AssistantAgent('LLMAgent', model_client=model_client)
    
    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        print(f'{self.id.type} received message: {message.content}')
        text_message = TextMessage(content=message.content, source='user')
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)

        assert isinstance(response.chat_message, TextMessage)
        reply = response.chat_message.content
        print(f'{self.id.type} responsed: {reply}')

        return Message(content=reply)


async def register_agent_type(runtime: SingleThreadedAgentRuntime):
    await SimpleAgent.register(runtime, 'simple_agent', lambda: SimpleAgent()) # the thrid parameter requted a factory function with .init()
    await MyLLMAgent.register(runtime, 'LLMAgent', lambda: MyLLMAgent())



async def invoke_simple_agent(runtime: SingleThreadedAgentRuntime):
    simple_agent_id = AgentId('simple_agent', 'default')
    response = await runtime.send_message(Message('Well hi there!'), simple_agent_id)
    print('<< simple_agent >>',response.content)


async def invoke_llm_agent(runtime: SingleThreadedAgentRuntime):
    llm_agent_id = AgentId('LLMAgent', 'default')
    response = await runtime.send_message(Message('Well hi there!'), llm_agent_id)
    print('<< llm_agent >>',response.content)

async def main1():
    runtime = SingleThreadedAgentRuntime() # should it be out of this function ?
    await register_agent_type(runtime)

    runtime.start() 
    await invoke_simple_agent(runtime)
    await invoke_llm_agent(runtime)

    await runtime.stop()
    await runtime.close()

PLAYER_INSTRCTION = 'You are playing rock, paper, scissors. Respond only with the one word, one of the following: paper, rock, or scissors in equally chance.'

class Player1Agent(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(model='gpt-4o-mini', temperature=1)
        self._delegate = AssistantAgent(
            name, 
            model_client=model_client,
            system_message=PLAYER_INSTRCTION
        )
    
    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        text_message= TextMessage(content=message.content, source='user')
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)

        assert isinstance(response.chat_message, TextMessage)
        return Message(content=response.chat_message.content)


class Player2Agent(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(model='gpt-4o-mini', temperature=0)
        self._delegate = AssistantAgent(
            name, 
            model_client=model_client,
            system_message=PLAYER_INSTRCTION
        )

    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        text_message = TextMessage(content=message.content, source='user')
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)
        assert isinstance(response.chat_message, TextMessage)
        return Message(content=response.chat_message.content)

JUDGE_PROMPT = 'You are judging a game of rock, paper, scissors. If the game result is a tie, restart the game until there is a winner. The players have made these choices:\n'
## Note: AutoGen 只是做訊息流分配, 要實現重啟遊戲需要由agent這邊寫code自行做判斷. 可搭配structured output做判定
## Langgraph 因為是使用Node, edge強制控制流程, 所以比較容易實現
class RockPaperScissorsAgent(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')
        self._delegate = AssistantAgent(
            name,
            model_client=model_client,
            system_message=JUDGE_PROMPT
        )
    
    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        instruction = 'Go'  
        rule_message = Message(content=instruction)
        inner_1 = AgentId('Sam', 'A')
        inner_2 = AgentId('Chris', 'B')
        response1 = await self.send_message(rule_message, inner_1)
        response2 = await self.send_message(rule_message, inner_2)

        result = f'Player 1: {response1.content}\nPlayer 2: {response2.content}\n'

        judge = f'{result}Who wins'
        judge_message = TextMessage(content=judge, source='user')
        judge_response = await self._delegate.on_messages([judge_message], ctx.cancellation_token)
        assert isinstance(judge_response.chat_message, TextMessage)
        return Message(content=result + judge_response.chat_message.content)


async def register_agent_type2(runtime: SingleThreadedAgentRuntime):
    await Player1Agent.register(runtime, 'Sam', lambda: Player1Agent('Sam'))
    await Player2Agent.register(runtime, 'Chris', lambda: Player2Agent('Chris'))
    await RockPaperScissorsAgent.register(runtime, 'rock_paper_scissors', lambda: RockPaperScissorsAgent('Kobe'))


async def main2():
    runtime = SingleThreadedAgentRuntime()
    await register_agent_type2(runtime)
    runtime.start()
    agent_id = AgentId('rock_paper_scissors', 'C')
    message = Message(content='Start !')
    response = await runtime.send_message(message, agent_id)
    print(response.content)

    await runtime.stop()
    await runtime.close()


if __name__ == '__main__':
    # asyncio.run(main1())
    asyncio.run(main2())