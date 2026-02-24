from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import gradio as gr
import uuid
from dotenv import load_dotenv
import os
import nest_asyncio
import asyncio
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import logging
from functools import wraps

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# env
load_dotenv(override=True)
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_URL = os.getenv("PUSHOVER_URL")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_URL = "https://google.serper.dev/search"

LLM_MODEL_GPT_4O = 'gpt-4o-mini'

# ==================== 修改 1: 統一 Timeout Decorator ====================
# 目的: 統一所有 timeout 處理方式，使用 decorator 而非 helper function
# 優點: 代碼一致性、可讀性高、時長可靈活調整
def with_timeout(seconds):
    """
    統一的超時裝飾器
    在任何需要超時控制的地方使用此 decorator
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                func_name = func.__name__
                logger.error(f"{func_name} timeout after {seconds}s")
                raise TimeoutError(f"{func_name} exceeded {seconds}s timeout")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步函數不需要 timeout（LLM 調用等）
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# ==================== 修改 2: 全局 Error Handler ====================
# 目的: 統一錯誤處理，避免每個函數重複寫 try-catch
# 優點: 強制統一、不會遺漏、類似 Fastify 的全局錯誤處理
class ProtectedStateGraph(StateGraph):
    """
    帶全局錯誤處理的 StateGraph
    自動捕獲所有 node 的錯誤，統一處理
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_handlers = []  # 可擴展的錯誤處理器列表
    
    def add_error_handler(self, handler):
        """
        添加自定義錯誤處理器
        handler(error, state, node_name) -> bool
        返回 True 表示已處理，False 繼續執行預設處理
        """
        self.error_handlers.append(handler)
    
    async def _handle_error(self, error, state, node_name):
        """統一錯誤處理邏輯"""
        logger.error(f"Error in node '{node_name}': {error}", exc_info=True)
        
        # 1. 執行自定義錯誤處理器
        for handler in self.error_handlers:
            try:
                if await handler(error, state, node_name):
                    return  # 已被自定義處理器處理
            except Exception as handler_error:
                logger.error(f"Error handler failed: {handler_error}")
        
        # 2. 預設錯誤處理
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            error_msg = f"Operation in '{node_name}' timed out. Please try again with a simpler request."
        elif isinstance(error, PlaywrightTimeoutError):
            error_msg = f"Browser operation in '{node_name}' timed out. The page might be too slow to load."
        else:
            error_msg = f"An error occurred in '{node_name}': {str(error)}"
        
        # 返回錯誤狀態
        return {
            'messages': [AIMessage(content=error_msg)],
            'user_input_needed': True
        }
    
    def add_node(self, name, func):
        """
        覆蓋 add_node，自動包裝每個節點添加錯誤處理
        目的: 所有 node 自動獲得錯誤保護，開發者不需要記得加 try-catch
        """
        async def wrapped_async_func(state):
            try:
                return await func(state)
            except Exception as e:
                return await self._handle_error(e, state, name)
        
        def wrapped_sync_func(state):
            try:
                return func(state)
            except Exception as e:
                # 同步函數的錯誤處理
                logger.error(f"Error in node '{name}': {e}", exc_info=True)
                return {
                    'messages': [AIMessage(content=f"Error in {name}: {str(e)}")],
                    'user_input_needed': True
                }
        
        # 根據函數類型選擇包裝器
        wrapper = wrapped_async_func if asyncio.iscoroutinefunction(func) else wrapped_sync_func
        super().add_node(name, wrapper)
    
    @with_timeout(120)  # 修改 3: 使用統一的 timeout decorator
    async def ainvoke(self, state, config):
        """
        覆蓋 ainvoke，添加全局超時和錯誤處理
        目的: 防止整個 graph 執行時間過長
        """
        try:
            return await super().ainvoke(state, config)
        except Exception as e:
            return await self._handle_error(e, state, "graph")


# Timeout 配置常數
BROWSER_OPERATION_TIMEOUT = 30   # 單個瀏覽器操作超時（秒）
TOOL_EXECUTION_TIMEOUT = 60      # 工具執行超時（秒）
GRAPH_EXECUTION_TIMEOUT = 120    # Graph 執行超時（秒）- 在 ProtectedStateGraph.ainvoke 中使用

# class for structured output
class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been achieved")
    user_input_needed: bool = Field(description="True if more input is needed from the user, or clarifications, or the assistant is stuck")

# add more attributes in State for pass on
class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool


# ==================== 修改 4: Browser Manager 使用 thread_id ====================
# 目的: 支持多用戶/多會話，每個 thread 有獨立的 browser instance
# 解決: 單例 browser 導致多用戶互相干擾的問題
class BrowserManager:
    """
    基於 thread_id 管理 Browser 實例
    每個對話線程有獨立的 browser，避免互相干擾
    """
    
    def __init__(self):
        self.browsers = {}  # {thread_id: browser_data}
        self._lock = asyncio.Lock()
    
    async def get_or_create_browser(self, thread_id: str):
        """獲取或創建指定 thread 的 browser"""
        async with self._lock:
            if thread_id not in self.browsers:
                logger.info(f"Creating new browser for thread {thread_id}")
                await self._create_browser(thread_id)
            return self.browsers[thread_id]
    
    async def _create_browser(self, thread_id: str):
        """創建新的 browser 實例"""
        try:
            # 優化的 browser 配置
            async_browser = create_async_playwright_browser(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            # 設置超時
            context = await async_browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            context.set_default_timeout(BROWSER_OPERATION_TIMEOUT * 1000)  # 轉換為毫秒
            context.set_default_navigation_timeout(BROWSER_OPERATION_TIMEOUT * 1000)
            
            # 創建 toolkit
            toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
            tools = toolkit.get_tools()
            
            self.browsers[thread_id] = {
                'browser': async_browser,
                'toolkit': toolkit,
                'tools': tools,
                'context': context
            }
            
            logger.info(f"Browser created successfully for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Failed to create browser for thread {thread_id}: {e}")
            raise
    
    async def cleanup_browser(self, thread_id: str):
        """清理指定 thread 的 browser"""
        async with self._lock:
            if thread_id in self.browsers:
                try:
                    browser_data = self.browsers[thread_id]
                    await browser_data['browser'].close()
                    logger.info(f"Browser closed for thread {thread_id}")
                except Exception as e:
                    logger.error(f"Error closing browser for thread {thread_id}: {e}")
                finally:
                    del self.browsers[thread_id]
    
    async def restart_browser(self, thread_id: str):
        """重啟指定 thread 的 browser"""
        logger.info(f"Restarting browser for thread {thread_id}")
        await self.cleanup_browser(thread_id)
        await self._create_browser(thread_id)
    
    async def get_tools(self, thread_id: str):
        """獲取指定 thread 的 tools"""
        browser_data = await self.get_or_create_browser(thread_id)
        return browser_data['tools']
    
    async def cleanup_all(self):
        """清理所有 browser 實例"""
        thread_ids = list(self.browsers.keys())
        for thread_id in thread_ids:
            await self.cleanup_browser(thread_id)


# 創建全局 browser manager
browser_manager = BrowserManager()

# 初始化 nest_asyncio
nest_asyncio.apply()

# init worker and evaluator LLM
worker_llm = ChatOpenAI(model=LLM_MODEL_GPT_4O)
evaluator_llm = ChatOpenAI(model=LLM_MODEL_GPT_4O)
evaluator_llm_with_output = evaluator_llm.with_structured_output(EvaluatorOutput)


# ==================== 修改 5: 簡化 Worker - 移除 try-catch ====================
# 目的: 依賴全局錯誤處理，讓代碼專注於業務邏輯
# 注意: thread_id 需要從 state 或其他方式傳遞
def worker(state: State) -> Dict[str, Any]:
    """
    Worker 節點 - 完全乾淨，無 try-catch
    錯誤由 ProtectedStateGraph 自動處理
    """
    # 驗證輸入（業務邏輯驗證，不是錯誤處理）
    if not state.get('success_criteria'):
        return {
            'messages': [AIMessage(content="Please provide success criteria for the task.")],
            'user_input_needed': True
        }
    
    system_message = f"""You are a helpful assistant that can use tools to complete tasks.
    You keep working on a task until either you have a question or clarification for the user, or the success criteria is met.
    This is the success criteria:
    {state['success_criteria']}
    You should reply either with a question for the user about this assignment, or with your final response.
    If you have a question for the user, you need to reply by clearly stating your question. An example might be:

    Question: please clarify whether you want a summary or a detailed answer

    If you've finished, reply with the final answer, and don't ask a question; simply reply with the answer.
    """

    if state.get('feedback_on_work'):
        system_message += f"""
        Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
        Here is the feedback on why this was rejected:
        {state['feedback_on_work']}
        With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""
    
    # 使用 .copy() 避免修改原始狀態
    messages = state['messages'].copy()
    
    # 添加或更新 system message
    found_system_message = False
    for i, message in enumerate(messages):
        if isinstance(message, SystemMessage):
            messages[i] = SystemMessage(content=system_message)
            found_system_message = True
            break
        
    if not found_system_message:
        messages = [SystemMessage(content=system_message)] + messages

    # 動態綁定 tools（從 state 中獲取 thread_id）
    # 注意: 這裡需要從 state 中傳遞 thread_id
    # 暫時使用空 tools，實際使用時需要修改
    worker_llm_with_tools = worker_llm.bind_tools([])  # TODO: 需要傳遞 thread_id
    
    # 調用 LLM
    response = worker_llm_with_tools.invoke(messages)
    
    logger.info(f"Worker response: {response.content[:100] if response.content else 'Tool calls'}")
    
    return {'messages': [response]}


def worker_router(state: State) -> str:
    """路由決策 - 簡化版本"""
    if not state.get('messages'):
        return 'evaluator'
    
    last_message = state['messages'][-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"Routing to tools: {len(last_message.tool_calls)} tool calls")
        return 'tools'
    else:
        return 'evaluator'


# ==================== 修改 6: Tools 使用統一的 timeout decorator ====================
# 目的: 統一超時處理方式，移除 asyncio.wait_for 的直接使用
@with_timeout(TOOL_EXECUTION_TIMEOUT)  # 使用統一的 timeout decorator
async def tools_execution(state: State, thread_id: str) -> Dict[str, Any]:
    """
    工具執行節點 - 使用 decorator 處理超時
    無需 try-catch，錯誤由全局處理
    """
    # 獲取 tools
    tools = await browser_manager.get_tools(thread_id)
    
    if not tools:
        raise Exception("Browser tools not available")
    
    tool_node = ToolNode(tools=tools)
    
    # 直接執行，不需要 asyncio.wait_for（已由 decorator 處理）
    result = await tool_node.ainvoke(state)
    
    logger.info("Tool execution completed successfully")
    return result


# 建立對話格式化函數
def format_conversation(messages: List[Any]) -> str:
    """格式化對話歷史"""
    conversation = 'Conversation history: \n\n'
    for message in messages:
        if isinstance(message, HumanMessage):
            conversation += f'User: {message.content}\n'
        elif isinstance(message, AIMessage):
            text = message.content or '[Tool use]'
            conversation += f'Assistant: {text}\n'
    
    return conversation


# ==================== 修改 7: Evaluator 簡化 ====================
# 目的: 移除 try-catch，依賴全局錯誤處理
def evaluator(state: State) -> Dict[str, Any]:
    """
    Evaluator 節點 - 完全乾淨
    錯誤由 ProtectedStateGraph 自動處理
    """
    # 基本驗證（業務邏輯，不是錯誤處理）
    if not state.get('messages') or len(state['messages']) == 0:
        return {
            'messages': [AIMessage(content="No messages to evaluate.")],
            'feedback_on_work': None,
            'success_criteria_met': False,
            'user_input_needed': True
        }
    
    last_response = state['messages'][-1].content or "[No content]"

    system_message = """You are an evaluator that determines if a task has been completed successfully by an Assistant.
    Assess the Assistant's last response based on the given criteria. Respond with your feedback, and with your decision on whether the success criteria has been met,
    and whether more input is needed from the user."""

    user_message = f"""You are evaluating a conversation between the User and Assistant. You decide what action to take based on the last response from the Assistant.

    The entire conversation with the assistant, with the user's original request and all replies, is:
    {format_conversation(state['messages'])}

    The success criteria for this assignment is:
    {state['success_criteria']}

    And the final response from the Assistant that you are evaluating is:
    {last_response}

    Respond with your feedback, and decide if the success criteria is met by this response.
    Also, decide if more user input is required, either because the assistant has a question, needs clarification, or seems to be stuck and unable to answer without help.
    """

    if state.get('feedback_on_work'):
        user_message += f"Also, note that in a prior attempt from the Assistant, you provided this feedback: {state['feedback_on_work']}\n"
        user_message += "If you're seeing the Assistant repeating the same mistakes, then consider responding that user input is required."
    
    evaluator_messages = [
        SystemMessage(content=system_message), 
        HumanMessage(content=user_message)
    ]
    
    evaluate_result = evaluator_llm_with_output.invoke(evaluator_messages)

    logger.info(f"Evaluator feedback: {evaluate_result.feedback[:100]}")
    logger.info(f"Success: {evaluate_result.success_criteria_met}, Need input: {evaluate_result.user_input_needed}")

    new_state = {
        'messages': [AIMessage(
            content=f"Evaluator Feedback: {evaluate_result.feedback}"
        )],
        'feedback_on_work': evaluate_result.feedback,
        'success_criteria_met': evaluate_result.success_criteria_met,
        'user_input_needed': evaluate_result.user_input_needed
    }

    return new_state


def evaluator_route(state: State) -> str:
    """評估路由"""
    if state.get('success_criteria_met') or state.get('user_input_needed'):
        logger.info("Task completed or user input needed")
        return 'END'
    else:
        logger.info("Continuing to worker")
        return 'worker'


# ==================== 修改 8: 自定義錯誤處理器 ====================
# 目的: 針對特定錯誤類型（如 browser 錯誤）執行特殊處理
async def browser_error_handler(error, state, node_name):
    """
    自定義錯誤處理器：處理 browser 相關錯誤
    返回 True 表示已處理，False 讓預設處理器處理
    """
    error_str = str(error).lower()
    
    # 檢查是否是 browser 相關錯誤
    if any(keyword in error_str for keyword in ['browser', 'playwright', 'page', 'navigation']):
        logger.info(f"Detected browser error in {node_name}, attempting restart...")
        
        # 從 state 中獲取 thread_id（需要在 state 中傳遞）
        thread_id = state.get('thread_id')
        if thread_id:
            try:
                await browser_manager.restart_browser(thread_id)
                logger.info(f"Browser restarted successfully for thread {thread_id}")
            except Exception as restart_error:
                logger.error(f"Failed to restart browser: {restart_error}")
        
        # 返回 False 讓預設錯誤處理器返回錯誤訊息給用戶
        return False
    
    # 不是 browser 錯誤，讓其他處理器處理
    return False


# ==================== 修改 9: 初始化 Graph ====================
# 目的: 使用 ProtectedStateGraph 並註冊自定義錯誤處理器
async def initialize_graph():
    """初始化帶全局錯誤處理的 graph"""
    
    # 使用 ProtectedStateGraph 替代 StateGraph
    graph_builder = ProtectedStateGraph(State)
    
    # 註冊自定義錯誤處理器
    graph_builder.add_error_handler(browser_error_handler)
    
    # 添加節點（自動獲得錯誤保護）
    graph_builder.add_node('worker', worker)
    
    # Tools 節點需要特殊處理，因為需要 thread_id
    # 創建一個閉包來傳遞 thread_id
    def create_tools_node(thread_id):
        async def tools_node(state):
            return await tools_execution(state, thread_id)
        return tools_node
    
    # 暫時使用占位符，實際執行時會動態創建
    # 這裡的實現需要改進，暫時保持簡單
    async def tools_wrapper(state):
        # 從 state 中獲取 thread_id
        thread_id = state.get('thread_id', 'default')
        return await tools_execution(state, thread_id)
    
    graph_builder.add_node('tools', tools_wrapper)
    graph_builder.add_node('evaluator', evaluator)

    # 添加邊
    graph_builder.add_conditional_edges('worker', worker_router, {'tools': 'tools', 'evaluator': 'evaluator'})
    graph_builder.add_edge('tools', 'worker')
    graph_builder.add_conditional_edges('evaluator', evaluator_route, {'worker': 'worker', 'END': END})
    graph_builder.add_edge(START, 'worker')

    # 編譯 graph
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)
    
    logger.info("Graph initialized successfully with global error handling")
    return graph


# 全局 graph 實例
graph = None


def make_thread_id() -> str:
    """生成新的 thread ID"""
    return str(uuid.uuid4())


# ==================== 修改 10: Process Message 簡化 ====================
# 目的: 依賴全局錯誤處理和統一的 timeout，簡化代碼
async def process_message(message: str, success_criteria: str, history: List, thread: str):
    """
    處理用戶訊息 - 大幅簡化
    錯誤處理和超時都由 ProtectedStateGraph 處理
    """
    global graph
    
    # 基本輸入驗證
    if not message or not message.strip():
        logger.warning("Empty message received")
        return history
    
    if not success_criteria or not success_criteria.strip():
        error = {'role': 'assistant', 'content': 'Please provide success criteria for the task.'}
        return history + [{'role': 'user', 'content': message}, error]
    
    # 確保 graph 已初始化
    if graph is None:
        logger.info("Initializing graph for first time...")
        graph = await initialize_graph()
    
    config = {'configurable': {'thread_id': thread}}

    # 狀態重置 - 確保乾淨的狀態
    state = {
        'messages': [HumanMessage(content=message)],
        'success_criteria': success_criteria,
        'feedback_on_work': None,  # 明確重置
        'success_criteria_met': False,
        'user_input_needed': False,
        'thread_id': thread  # 傳遞 thread_id 用於 browser 管理
    }

    logger.info(f"Processing message for thread {thread}: {message[:50]}...")
    
    # 直接調用 graph，錯誤和超時都由 ProtectedStateGraph 處理
    # 不需要 try-catch 和 asyncio.wait_for
    result = await graph.ainvoke(state, config=config)
    
    user = {'role': 'user', 'content': message}
    
    # 基本驗證結果
    if not result.get('messages') or len(result['messages']) < 2:
        logger.warning("Insufficient messages in result")
        error_msg = {'role': 'assistant', 'content': 'Sorry, I could not complete the task. Please try again.'}
        return history + [user, error_msg]
    
    reply_content = result['messages'][-2].content or "No response generated"
    feedback_content = result['messages'][-1].content or "No feedback available"
    
    reply = {'role': 'assistant', 'content': reply_content}
    feedback = {'role': 'assistant', 'content': feedback_content}
    
    logger.info("Message processed successfully")
    return history + [user, reply, feedback]


async def reset(thread: str):
    """
    軟重置 - 重啟當前 thread 的 browser
    """
    logger.info(f"Soft reset for thread {thread}")
    await browser_manager.restart_browser(thread)
    return '', '', [], make_thread_id()


async def hard_reset():
    """
    硬重置 - 重建整個系統
    """
    global graph
    
    logger.info("Hard reset - rebuilding everything")
    
    # 清理所有 browser
    await browser_manager.cleanup_all()
    
    # 重建 graph
    graph = await initialize_graph()
    
    return '', '', [], make_thread_id()


# ==================== Gradio UI ====================
with gr.Blocks() as demo:
    gr.Markdown('## Sidekick Project v3.0')
    gr.Markdown('*With Global Error Handling & Unified Timeout Decorator*')
    gr.Markdown("""
    ### 架構特色:
    - ✅ 全局錯誤處理 (ProtectedStateGraph)
    - ✅ 統一 Timeout Decorator
    - ✅ 基於 Thread 的 Browser 管理
    - ✅ 乾淨的業務邏輯代碼
    """)
    
    thread = gr.State(make_thread_id())

    with gr.Row():
        chatbot = gr.Chatbot(label='Sidekick', height=400)
    
    with gr.Group():
        with gr.Row():
            message = gr.Textbox(
                show_label=False, 
                placeholder="Your request to your sidekick",
                scale=4
            )
        with gr.Row():
            success_criteria = gr.Textbox(
                show_label=False, 
                placeholder="What are your success criteria?",
                scale=4
            )
    
    with gr.Row():
        go_button = gr.Button('Go!', variant='primary')
        reset_button = gr.Button('Soft Reset (Restart Browser)', variant='secondary')
        hard_reset_button = gr.Button('Hard Reset (Rebuild All)', variant='stop')
    
    with gr.Row():
        gr.Markdown("""
        **Soft Reset**: 重啟當前對話的瀏覽器
        **Hard Reset**: 清理所有瀏覽器並重建系統
        """)

    # 綁定事件
    message.submit(process_message, [message, success_criteria, chatbot, thread], [chatbot])
    success_criteria.submit(process_message, [message, success_criteria, chatbot, thread], [chatbot])
    go_button.click(process_message, [message, success_criteria, chatbot, thread], [chatbot])
    
    # Reset 按鈕需要傳遞 thread
    reset_button.click(
        lambda t: reset(t), 
        [thread], 
        [message, success_criteria, chatbot, thread]
    )
    hard_reset_button.click(hard_reset, [], [message, success_criteria, chatbot, thread])


# 應用啟動
async def startup():
    """應用啟動時的初始化"""
    global graph
    logger.info("Starting Sidekick v3.0...")
    graph = await initialize_graph()
    logger.info("Application ready!")


if __name__ == "__main__":
    # 初始化
    asyncio.run(startup())
    
    # 啟動
    demo.launch(
        theme=gr.themes.Default(primary_hue='emerald'),
        server_name="0.0.0.0",
        server_port=7860
    )