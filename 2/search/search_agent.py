from agents import Agent, WebSearchTool, ModelSettings

LLM_MODEL = 'gpt-4o-mini'
INSTRUCTIONS = (
    "You are a professional research assistance."
    "Gavin a search term and you seach the web for that term and provide a concise summary as result."
    "Write succintly, no need to have complete sentences or good grammar."
    "This will be consumed by someone synthesizing a report, so its vital you capture the "
    "essence and ignore any fluff. Do not include any additional commentary other than the summary itself."
)

search_agent = Agent(
    name="SeachAgent",
    instructions=INSTRUCTIONS,
    tools=[WebSearchTool(search_context_size="low")],
    model=LLM_MODEL,
    model_settings=ModelSettings(tool_choice="required")
)