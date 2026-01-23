from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
import gradio as gr
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
import requests
import os
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
import asyncio
from playwright.async_api import async_playwright
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
import threading

load_dotenv(override=True)

# ==================== 設定 ====================
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_user = os.getenv("PUSHOVER_USER")
pushover_url = os.getenv("PUSHOVER_URL")

# ==================== State ====================
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ==================== 全域變數 ====================
graph = None
event_loop = None  # 背景事件循環
playwright_instance = None
browser_instance = None

# ==================== Pushover 工具 ====================
def push(text: str):
    """Send a push notification to the user"""
    try:
        requests.post(
            pushover_url,
            data={
                'token': pushover_token,
                'user': pushover_user,
                'message': text,
            },
            timeout=10
        )
        return "✅ Push notification sent successfully!"
    except Exception as e:
        return f"❌ Failed to send push notification: {str(e)}"

tool_push = Tool(
    name='send_push_notification',
    func=push,
    description='useful for sending a push notification to your mobile device with a custom message',
)

# ==================== 初始化瀏覽器和工具 ====================
async def setup_browser():
    """初始化 Playwright 瀏覽器和 LangGraph"""
    global graph, playwright_instance, browser_instance
    
    print("🌐 Starting Playwright browser...")
    playwright_instance = await async_playwright().start()
    browser_instance = await playwright_instance.chromium.launch(headless=False)
    
    print("🔧 Creating browser toolkit...")
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser_instance)
    browser_tools = toolkit.get_tools()
    
    print(f"✅ Found {len(browser_tools)} browser tools")
    
    # 組合所有工具
    all_tools = browser_tools + [tool_push]
    
    # 建立 LLM
    print("🤖 Initializing LLM...")
    llm = ChatOpenAI(model='gpt-4o-mini')
    llm_with_tools = llm.bind_tools(all_tools)
    
    # 定義 chatbot 節點
    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}
    
    # 建立 LangGraph
    print("📊 Building LangGraph...")
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools=all_tools))
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")
    
    # 編譯 graph with memory
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)
    
    print("✅ Setup complete!")
    print("\n🔧 Available tools:")
    for i, tool in enumerate(all_tools, 1):
        print(f"  {i}. {tool.name}: {tool.description}")
    
    return all_tools

# ==================== 背景事件循環 ====================
def run_event_loop():
    """在背景執行緒中運行事件循環"""
    global event_loop
    
    print("🔄 Starting background event loop...")
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    
    # 初始化瀏覽器
    event_loop.run_until_complete(setup_browser())
    
    # 保持事件循環運行
    print("✅ Event loop is running in background")
    event_loop.run_forever()

# ==================== Gradio Chat 函數 ====================
def chat(message, history):
    """
    處理使用者訊息
    這個函數在主執行緒(Gradio)中被呼叫
    將 async 任務提交到背景事件循環
    """
    if graph is None or event_loop is None:
        return "❌ Error: System not initialized. Please restart the application."
    
    try:
        print(f"\n{'='*60}")
        print(f"📨 User: {message}")
        print(f"{'='*60}")
        
        config = {"configurable": {"thread_id": "10"}}
        
        # 將 async 任務提交到背景事件循環
        future = asyncio.run_coroutine_threadsafe(
            graph.ainvoke(
                {"messages": [{"role": "user", "content": message}]}, 
                config=config
            ),
            event_loop  # 使用背景事件循環
        )
        
        # 等待結果 (最多 120 秒)
        result = future.result(timeout=120)
        
        response = result["messages"][-1].content
        
        print(f"\n{'='*60}")
        print(f"🤖 Assistant: {response[:200]}{'...' if len(response) > 200 else ''}")
        print(f"{'='*60}\n")
        
        return response
        
    except asyncio.TimeoutError:
        return "⏱️ Request timeout after 120 seconds. Please try again with a simpler request."
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg

# ==================== 主程式 ====================
def main():
    """主函數"""
    print("="*60)
    print("🤖 Browser Agent with Memory")
    print("="*60)
    
    # 1. 在背景執行緒啟動事件循環
    print("\n🚀 Starting background event loop...")
    loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    loop_thread.start()
    
    # 等待初始化完成
    import time
    time.sleep(3)
    
    if graph is None:
        print("❌ Failed to initialize. Please check the logs.")
        return
    
    # 2. 在主執行緒啟動 Gradio
    print("\n🚀 Launching Gradio interface...")
    print("="*60)
    print("✅ Application is ready!")
    print("📱 Open your browser at: http://127.0.0.1:7860")
    print("⚠️  Press Ctrl+C to stop")
    print("="*60)
    print()
    
    demo = gr.ChatInterface(
        chat,
        title="Browser Agent with Memory",
        description="Chat with an AI agent that can browse the web and send push notifications!",
        examples=[
            "Navigate to https://www.cnn.com and tell me the top news",
            "What is the current page URL?",
            "Extract the text from the current page",
            "Send me a push notification saying 'Hello from AI!'"
        ]
    )
    
    try:
        demo.launch(server_port=7860, share=False)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        # 清理資源
        if event_loop and browser_instance:
            future = asyncio.run_coroutine_threadsafe(
                browser_instance.close(),
                event_loop
            )
            future.result(timeout=5)
        if event_loop and playwright_instance:
            future = asyncio.run_coroutine_threadsafe(
                playwright_instance.stop(),
                event_loop
            )
            future.result(timeout=5)
        print("✅ Cleanup complete. Goodbye!")

if __name__ == "__main__":
    main()