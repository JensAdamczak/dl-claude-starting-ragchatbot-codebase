"""Shared fixtures for RAG system tests."""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# Add backend to sys.path so imports like `from rag_system import ...` work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Test FastAPI app — mirrors backend/app.py routes but skips StaticFiles mount
# so tests don't require the ../frontend directory to exist.
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str

class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def _build_test_app(rag_system):
    """Create a FastAPI app with the same routes as production but no static files."""
    app = FastAPI()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """A fully-mocked RAGSystem suitable for API-level tests.

    Defaults:
      - query() returns ("Mock answer", ["Source A"])
      - session_manager.create_session() returns "test_session_1"
      - get_course_analytics() returns 2 courses
    """
    rag = MagicMock()
    rag.query.return_value = ("Mock answer", ["Source A"])
    rag.session_manager.create_session.return_value = "test_session_1"
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Intro to AI", "Advanced ML"],
    }
    return rag


@pytest.fixture
def test_app(mock_rag_system):
    """FastAPI test application wired to the mock RAG system."""
    return _build_test_app(mock_rag_system)


@pytest.fixture
def client(test_app):
    """Synchronous TestClient for the test app."""
    return TestClient(test_app)
