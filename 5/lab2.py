from dotenv import load_dotenv
from io import BytesIO
from PIL import Image
import requests
from autogen_agentchat.messages import TextMessage, MultiModalMessage
from autogen_core import Image as AGImage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from pydantic import BaseModel, Field
from typing import Literal
import asyncio

# apply adpter trun Langchain tools to AG tools.
from autogen_ext.tools.langchain import LangChainToolAdapter
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools.simple import Tool

load_dotenv(override=True)


# read image by PIL and BytesIO
url = 'https://edwarddonner.com/wp-content/uploads/2024/10/from-software-engineer-to-AI-DS.jpeg'
pil_imlage = Image.open(BytesIO(requests.get(url).content))
img = AGImage(pil_imlage)


# compose mulit-modal message with text and image
multi_modal_message = MultiModalMessage(
    content=["Describe the content of this image in detail", img], 
    source="User"
    )


# define a pydantic class as structured output
class ImageDescription(BaseModel):
    scene: str = Field(description='Briefly, the overall scene of the image')
    message: str = Field(description='The point that the image is trying to convey')
    style: str = Field(description='The artistic style of the image')
    orientation: Literal["portrait", "landscape", "square"] = Field(description='The orientation of the image')

# enhance function of searcher
serper = GoogleSerperAPIWrapper()

def search_with_sources(query: str) -> str:
    results = serper.results(query)
    output = []
    for r in results.get("organic", []):
        output.append(f"Title: {r.get('title')}\nURL: {r.get('link')}\nSnippet: {r.get('snippet')}\n")
    return "\n".join(output)

# apply Langchain tools to AG tools through adapter
prompt = """Your task is to find a one-way non-stop flight from JFK to LHR for tomorrow afternoon.
Search online multiple times using different queries to find at least 3 different flight options.
Verify each option is truly non-stop and confirm the price from the source.
Next, write all the deals to a file called flights.md with full details.
Finally, select the one you think is best and reply with a short summary.
Reply with the selected flight only, and only after you have written the details to the file.
You MUST call the write_file tool before replying."""


langchain_serper = Tool(name='internet_search', func=search_with_sources, description='useful for when you need to search the internet')
autogen_serper = LangChainToolAdapter(langchain_serper)
autogen_tools = [autogen_serper]

langchain_file_management_tools = FileManagementToolkit(root_dir='sandbox').get_tools()
for tool in langchain_file_management_tools:
    autogen_tools.append(LangChainToolAdapter(tool))

# for tool in autogen_tools:
#     print(tool.name, tool.description)

# set model_client for AG
model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')

agent = AssistantAgent(name='searcher', model_client=model_client, tools=autogen_tools, reflect_on_tool_use=True)
message = TextMessage(content=prompt, source='user')

# create assistant agent with that model_client
describer = AssistantAgent(
    name='describer',
    model_client=model_client,
    system_message='You are good at providing detailed descriptions of images',
    output_content_type=ImageDescription
)


# action function
async def describe_image():
    'send mulit-modal message to assistant agent and print the response'
    response = await describer.on_messages([multi_modal_message], cancellation_token=CancellationToken())
    reply = response.chat_message.content
    print(reply)

async def search_flight():
    'send text message to assistant agent and print the response'
    response = await agent.on_messages([message], cancellation_token=CancellationToken())
    reply = response.chat_message.content
    print(reply)

    followup_message = TextMessage(content='OK, proceed', source='user')
    await agent.on_messages([followup_message], cancellation_token=CancellationToken())



# async def write_flight_details_to_file():
#     'open file and write down the flight details'
#     message = TextMessage(content = 'Ok, proceed', source='user')
#     result = await agent.on_messages([message], cancellation_token=CancellationToken())
#     for message in reuslt.inner_messages:



# apply Team interactions
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import  TextMentionTermination

primary_agent = AssistantAgent(
    name='primary_agent',
    model_client=model_client,
    tools=autogen_tools,
    system_message='You are a helpful AI research assistant who looks for promising deals on flights. Incorporate any feedback you receive.',
)

evaluation_agent = AssistantAgent(
    name='evaluation_agent',
    model_client=model_client,
    system_message='Provide constructive feedback. Respond with "APPROVE" when your feedback is addressed.',
)

text_termination = TextMentionTermination('APPROVE')

team = RoundRobinGroupChat([primary_agent, evaluation_agent], termination_condition=text_termination, max_turns=20)


# work as a team
async def team_search_flight():
    'let primary_agent search for flight deals and evaluation_agent provide feedback until the deal is good enough'
    initial_message = TextMessage(content=prompt, source='user')
    response = await team.run(task=initial_message)
    for message in response.messages:
        print(f"{message.source}:\n{message.content}\n\n")

    followup_message = TextMessage(content='OK, proceed', source='user')
    await team.run(task=followup_message)


## MCP teaser 
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools

# Get the fectch  tool from mcp-server-fetch.
async def fetch_with_mcp():
    fetch_mcp_server = StdioServerParams(command='uvx', args=['mcp-server-fetch'], read_timeout_seconds=30)
    fetcher = await mcp_server_tools(fetch_mcp_server)

    model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')
    agent = AssistantAgent(
        name='fetcher',
        model_client=model_client,
        tools=fetcher,
        reflect_on_tool_use=True
    )

    result = await agent.run(task='Review website "https://ani.gamer.com.tw", and provide TOP 3 to me.')
    print(result.messages[-1].content)
    

def main():
    # asyncio.run(describe_image())
    # asyncio.run(search_flight())
    # asyncio.run(team_search_flight())
    asyncio.run(fetch_with_mcp())
    


if __name__ == "__main__":
    main() 