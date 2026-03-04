# .env
from dotenv import load_dotenv
load_dotenv(override=True)

# 1. model
from autogen_ext.models.openai import OpenAIChatCompletionClient
model_client = OpenAIChatCompletionClient(model='gpt-4o-mini')

# 2. TextMessage
from autogen_agentchat.messages import TextMessage
message = TextMessage(content="I'd like to go to London", source='user')

# 3. agent
from autogen_agentchat.agents import AssistantAgent
agent = AssistantAgent(
    name='airline_agent',
    model_client=model_client,
    system_message='You are a helpful assistant for an airline. You give short, humorous answers.',
    model_client_stream=True # True ->即是顯示文字 ; False -> 等到全部文字生成完才顯示
)


# local DB for some info to LLM
import os
import sqlite3

if os.path.exists('tickets.db'):
    os.remove('tickets.db')


conn = sqlite3.connect('tickets.db')
c = conn.cursor()
c.execute('CREATE TABLE cities (city_name TEXT PRIMARY KEY, round_trip_price REAL)')
conn.commit()
conn.close()

# populate the DB
def save_city_price(city_name, round_trip_price):
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute('REPLACE INTO cities (city_name, round_trip_price) VALUES (?, ?)', (city_name.lower(), round_trip_price))
    conn.commit()
    conn.close()

# insert dummy data
save_city_price("London", 299)
save_city_price("Paris", 399)
save_city_price("Rome", 499)
save_city_price("Madrid", 550)
save_city_price("Barcelona", 580)
save_city_price("Berlin", 525)


# GET ticket price from DB for LLM
def get_city_price(city_name: str) ->float | None:
    'GET the roundtrip ticjket price to travel to the city'
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute('SELECT round_trip_price FROM cities WHERE city_name = ?', (city_name.lower(),))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

get_city_price("London")


ticket_price_agent = AssistantAgent(
    name="smart_airline_agent",
    model_client=model_client,
    system_message="You are a helpful assistant for an airline. You give short, humorous answers, including the price of a roundtrip ticket.",
    model_client_stream=True,
    tools=[get_city_price],
    reflect_on_tool_use=True
)

# assembly 1 2 3 by autogen_core
from autogen_core import CancellationToken

async def main():
    response = await ticket_price_agent.on_messages(
    [message],
    cancellation_token=CancellationToken()
    )
    print(response.chat_message.content)

# add encoding before LLM response includes emojis
import sys
sys.stdout.reconfigure(encoding='utf-8')

import asyncio
if __name__ == "__main__":
    asyncio.run(main())