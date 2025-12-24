from dotenv import load_dotenv
from agents import Agent, Runner, trace
import asyncio

load_dotenv(override=True)

agent = Agent(
    name='Jokester',
    instructions="You are a professional jocker teller, especially on satirical black humor in one sentence.",
    model="gpt-4o-mini"
)

async def main():
    with trace("tell a joke"):
        result = await Runner.run(agent, "說個笑話")
        print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())