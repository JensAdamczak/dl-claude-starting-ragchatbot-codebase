"""Tests for the FastAPI API endpoints."""

import pytest


# ── POST /api/query ──────────────────────────────────────────────────────────


class TestQueryEndpoint:
    """Tests for POST /api/query."""

    def test_query_with_session_id(self, client, mock_rag_system):
        """Existing session_id is forwarded to RAGSystem.query."""
        resp = client.post(
            "/api/query",
            json={"query": "What is RAG?", "session_id": "existing_session"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Mock answer"
        assert data["sources"] == ["Source A"]
        assert data["session_id"] == "existing_session"
        mock_rag_system.query.assert_called_once_with("What is RAG?", "existing_session")

    def test_query_without_session_id_creates_session(self, client, mock_rag_system):
        """When session_id is omitted a new session is created."""
        resp = client.post("/api/query", json={"query": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "test_session_1"
        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with("Hello", "test_session_1")

    def test_query_returns_empty_sources(self, client, mock_rag_system):
        """Response includes an empty sources list when RAG returns none."""
        mock_rag_system.query.return_value = ("Direct answer", [])
        resp = client.post("/api/query", json={"query": "Hi"})
        assert resp.status_code == 200
        assert resp.json()["sources"] == []

    def test_query_missing_query_field(self, client):
        """Missing required 'query' field returns 422."""
        resp = client.post("/api/query", json={"session_id": "s1"})
        assert resp.status_code == 422

    def test_query_empty_body(self, client):
        """Empty JSON body returns 422."""
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_query_rag_exception_returns_500(self, client, mock_rag_system):
        """Internal RAG error surfaces as HTTP 500."""
        mock_rag_system.query.side_effect = RuntimeError("vector store down")
        resp = client.post(
            "/api/query",
            json={"query": "fail", "session_id": "s1"},
        )
        assert resp.status_code == 500
        assert "vector store down" in resp.json()["detail"]

    def test_query_session_creation_failure_returns_500(self, client, mock_rag_system):
        """Error during session creation surfaces as HTTP 500."""
        mock_rag_system.session_manager.create_session.side_effect = RuntimeError("db full")
        resp = client.post("/api/query", json={"query": "Hi"})
        assert resp.status_code == 500

    def test_query_with_long_input(self, client, mock_rag_system):
        """Endpoint accepts a long query string."""
        long_query = "word " * 500
        resp = client.post(
            "/api/query",
            json={"query": long_query, "session_id": "s1"},
        )
        assert resp.status_code == 200
        mock_rag_system.query.assert_called_once_with(long_query, "s1")


# ── GET /api/courses ─────────────────────────────────────────────────────────


class TestCoursesEndpoint:
    """Tests for GET /api/courses."""

    def test_courses_success(self, client):
        """Returns course count and titles."""
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Intro to AI", "Advanced ML"]

    def test_courses_empty_catalog(self, client, mock_rag_system):
        """Returns zeros when no courses are loaded."""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_analytics_error_returns_500(self, client, mock_rag_system):
        """Internal analytics error surfaces as HTTP 500."""
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("chroma crash")
        resp = client.get("/api/courses")
        assert resp.status_code == 500
        assert "chroma crash" in resp.json()["detail"]


# ── Response schema validation ───────────────────────────────────────────────


class TestResponseSchemas:
    """Verify the JSON shape matches the Pydantic response models."""

    def test_query_response_has_required_keys(self, client):
        resp = client.post(
            "/api/query",
            json={"query": "test", "session_id": "s1"},
        )
        keys = set(resp.json().keys())
        assert keys == {"answer", "sources", "session_id"}

    def test_courses_response_has_required_keys(self, client):
        resp = client.get("/api/courses")
        keys = set(resp.json().keys())
        assert keys == {"total_courses", "course_titles"}
