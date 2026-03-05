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


# set model_client for AG
model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')

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

def main():
    asyncio.run(describe_image())


if __name__ == "__main__":
    main() 