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

async def main():
    runtime = SingleThreadedAgentRuntime() # should it be out of this function ?
    await register_agent_type(runtime)

    runtime.start() 
    await invoke_simple_agent(runtime)
    await invoke_llm_agent(runtime)

    await runtime.stop()
    await runtime.close()


if __name__ == '__main__':
    asyncio.run(main())