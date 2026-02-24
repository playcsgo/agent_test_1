# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangGraph-based AI agent learning project (Udemy course, Chapter 4). Each lab file progressively builds more complex agent architectures, culminating in the "Sidekick" project — a browser-automation agent with worker-evaluator feedback loops.

## Commands

Package management is handled by `uv` with pyproject.toml in the parent directory (`../pyproject.toml`).

```bash
# Install dependencies
uv sync

# Run any lab file
uv run python lab1.py
uv run python lab3_2.py
uv run python lab4.py

# Install Playwright browsers (required for lab3+ browser tools)
uv run playwright install
```

No test suite or linter is configured.

## Architecture Progression

- **lab1.py** — Minimal LangGraph: hardcoded random response node, Gradio ChatInterface
- **lab2.py** — Adds LLM (GPT-4o-mini), tool calling (Serper search, Pushover notifications), conditional edges (`tools_condition`), SQLite-backed memory (`SqliteSaver`)
- **lab3.py / lab3_with_comment.py** — Adds Playwright browser toolkit as async tools, threading pattern (background asyncio event loop + Gradio on main thread)
- **lab3_2.py** — OOP refactor: `AgentService` class, `AsyncSqliteSaver` with aiosqlite, monkey-patching for compatibility
- **lab4.py** — **Sidekick project**: Worker-Evaluator dual-LLM architecture. Worker executes tasks with browser tools; Evaluator uses structured output (`EvaluatorOutput` Pydantic model) to assess success criteria. Conditional routing loops worker until criteria met or user input needed. Uses `gr.Blocks` for custom UI with success criteria input.
- **lab4_2.py** — Sidekick v2: lazy browser initialization via `nest_asyncio`, error handling improvements
- **test1.py** — Sidekick v3: `ProtectedStateGraph` (custom StateGraph subclass) with global error handling, `@with_timeout` decorator, thread-based `BrowserManager` for multi-session browser isolation

## Key Patterns

- **State definition**: `TypedDict` with `Annotated[list, add_messages]` for message accumulation
- **LangGraph 5-step pattern**: Define State → Create StateGraph → Add nodes → Add edges → Compile
- **Tool binding**: `llm.bind_tools(tools)` + `ToolNode` + `tools_condition` for the tool-calling loop
- **Async + Threading**: Background `asyncio` event loop in a daemon thread; Gradio runs on the main thread; `asyncio.run_coroutine_threadsafe()` bridges them
- **Memory/Checkpointing**: `MemorySaver` (in-memory), `SqliteSaver` (sync SQLite), `AsyncSqliteSaver` (async SQLite) — all use `thread_id` in config

## Environment Variables (via `.env`)

Required for lab2+: `OPENAI_API_KEY`, `SERPER_API_KEY`, `PUSHOVER_TOKEN`, `PUSHOVER_USER`, `PUSHOVER_URL`

LangSmith (optional): `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT`

## Notes

- `note.txt` and `Lab4_question.txt` contain study notes and architecture questions
- Comments in the codebase are primarily in Traditional Chinese (繁體中文)
- The `sidekick/` directory is a work-in-progress for extracting tools into a separate module
