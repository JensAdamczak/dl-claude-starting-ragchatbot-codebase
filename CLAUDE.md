# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Install dependencies
uv sync

# Start the server (from project root)
./run.sh

# Or manually
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app runs at http://localhost:8000. FastAPI auto-docs at http://localhost:8000/docs.

Requires a `.env` file in the project root with `ANTHROPIC_API_KEY=sk-ant-...` (copy from `.env.example`).

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about course materials. It's a single-server app where FastAPI serves both the API and the static frontend.

### Query Flow (the critical path)

1. **Frontend** (`frontend/script.js`) sends `POST /api/query {query, session_id}` to the backend.
2. **FastAPI** (`backend/app.py`) creates a session if needed, delegates to `RAGSystem.query()`.
3. **RAGSystem** (`backend/rag_system.py`) retrieves conversation history, then calls `AIGenerator.generate_response()` with Claude's tool-use capability enabled.
4. **AIGenerator** (`backend/ai_generator.py`) makes a **first Claude API call** with the `search_course_content` tool available. Claude decides whether to search or answer directly.
5. If Claude invokes the tool: **CourseSearchTool** (`backend/search_tools.py`) calls **VectorStore.search()** (`backend/vector_store.py`), which queries ChromaDB with semantic embeddings.
6. **AIGenerator** makes a **second Claude API call** with the search results injected as tool results (tools disabled on this call) to synthesize the final answer.
7. Sources are collected from the tool, the exchange is saved to session history, and the response flows back as JSON.

### Two-call pattern in AIGenerator

`ai_generator.py` uses a two-call pattern: the first call includes tools so Claude can decide to search; the second call (in `_handle_tool_execution`) passes search results back without tools so Claude synthesizes a final answer. The second call is skipped if Claude answers directly (stop_reason == "end_turn").

### Vector Store: Two ChromaDB Collections

`VectorStore` manages two separate collections:
- **`course_catalog`** — one entry per course (title as document, metadata includes instructor/link/lessons). Used for fuzzy course name resolution via embedding similarity.
- **`course_content`** — text chunks from course lessons with metadata (course_title, lesson_number, chunk_index). Used for semantic content search.

Course name filtering works by first querying `course_catalog` to resolve a partial name to an exact title, then using that title as a `where` filter on `course_content`.

### Document Format

Course documents in `docs/` must follow this structure:
```
Course Title: [name]
Course Link: [url]
Course Instructor: [name]

Lesson N: [title]
Lesson Link: [url]
[lesson content...]
```

`DocumentProcessor` parses this format, splits content into sentence-based chunks (800 chars, 100 char overlap), and prepends lesson context to the first chunk of each lesson.

### Session Management

`SessionManager` tracks conversation history in-memory per session (max 2 exchanges = 4 messages). History is formatted as a plain string and appended to the system prompt, not sent as separate messages.

### Key Configuration (backend/config.py)

All tunable parameters are centralized in `Config`: model names, chunk size/overlap, max search results, max history length, ChromaDB path. The config loads `ANTHROPIC_API_KEY` from `.env` via python-dotenv.

### Frontend

Vanilla HTML/CSS/JS with no build step. `script.js` manages session state, sends queries via fetch, and renders responses with `marked.js` for markdown parsing. Sources are displayed in collapsible `<details>` elements.

### Tool System

Tools implement the `Tool` ABC (`search_tools.py`) with `get_tool_definition()` and `execute()`. `ToolManager` registers tools, provides definitions to Claude, and dispatches execution. Sources are tracked via `last_sources` on the tool instance and collected/reset by `RAGSystem` after each query.
