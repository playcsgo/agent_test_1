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

async def register_agent_type(runtime: SingleThreadedAgentRuntime):
    await SimpleAgent.register(runtime, 'simple_agent', lambda: SimpleAgent())

async def register_agent_id(runtime: SingleThreadedAgentRuntime):
    agent_id = AgentId('simple_agent', 'default')
    response = await runtime.send_message(Message('Well hi there!'), agent_id)
    print('<< register_agent_id >>',response.content)

async def main():
    runtime = SingleThreadedAgentRuntime() # should it be out of this function ?
    await register_agent_type(runtime)

    runtime.start() 
    await register_agent_id(runtime)

    await runtime.stop()
    await runtime.close()




if __name__ == '__main__':
    asyncio.run(main())