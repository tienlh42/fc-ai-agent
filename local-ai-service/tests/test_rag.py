from io import BytesIO
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.dependencies import get_document_storage, get_rag_service
from app.main import app
from app.rag.document_storage import DocumentStorage
from app.rag.rag_service import RagService


def make_rag(**overrides) -> RagService:
    defaults = {
        "embedding_service": Mock(),
        "vector_store": Mock(),
        "retriever": Mock(),
        "ollama_base_url": "http://ollama:11434",
        "chat_model": "qwen3:4b",
        "timeout": 120,
        "temperature": 0.1,
        "chunk_size": 100,
        "chunk_overlap": 10,
    }
    defaults.update(overrides)
    return RagService(**defaults)


def test_ingest_chunks_embeds_and_stores_document() -> None:
    embedding_service = Mock()
    embedding_service.embed.return_value = [[0.1], [0.2]]
    vector_store = Mock()
    rag = make_rag(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    count = rag.ingest("doc-1", "a " * 80, {"title": "Doc"})

    assert count == 2
    chunks = embedding_service.embed.call_args.args[0]
    vector_store.replace_document.assert_called_once_with(
        document_id="doc-1",
        chunks=chunks,
        embeddings=[[0.1], [0.2]],
        metadata={"title": "Doc"},
    )


def test_query_retrieves_top_five_and_calls_chat_model() -> None:
    retriever = Mock()
    retriever.retrieve.return_value = [
        {
            "id": "doc-1:0",
            "text": "Thông tin cần tìm.",
            "metadata": {"document_id": "doc-1"},
            "distance": 0.1,
        }
    ]
    response = Mock()
    response.json.return_value = {"message": {"content": "Câu trả lời."}}
    response.raise_for_status.return_value = None
    session = Mock()
    session.post.return_value = response
    rag = make_rag(retriever=retriever, session=session)

    result = rag.query("Câu hỏi?", top_k=5)

    retriever.retrieve.assert_called_once_with("Câu hỏi?", 5)
    assert result["answer"] == "Câu trả lời."
    request_json = session.post.call_args.kwargs["json"]
    assert "Thông tin cần tìm." in request_json["messages"][1]["content"]
    assert "Câu hỏi?" in request_json["messages"][1]["content"]


def test_rag_query_api_defaults_to_top_five() -> None:
    rag = Mock()
    rag.query.return_value = {"answer": "OK", "sources": []}
    app.dependency_overrides[get_rag_service] = lambda: rag
    try:
        response = TestClient(app).post(
            "/rag/query", json={"question": "Quy trình là gì?"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    rag.query.assert_called_once_with("Quy trình là gì?", 5)


def test_document_storage_saves_extracts_and_reads_text_file(tmp_path) -> None:
    storage = DocumentStorage(str(tmp_path), max_file_size=1024)

    stored = storage.save_and_extract(
        BytesIO("Quy trình nghỉ phép".encode("utf-8")),
        "quy-trinh.txt",
        "leave-policy",
    )

    assert stored["text"] == "Quy trình nghỉ phép"
    assert stored["document_id"] == "leave-policy"
    loaded = storage.get("leave-policy")
    assert loaded["original_filename"] == "quy-trinh.txt"
    assert open(loaded["path"], "rb").read() == "Quy trình nghỉ phép".encode("utf-8")


def test_rag_file_ingest_api_stores_and_indexes_file(tmp_path) -> None:
    storage = DocumentStorage(str(tmp_path), max_file_size=1024)
    rag = Mock()
    rag.ingest.return_value = 1
    app.dependency_overrides[get_document_storage] = lambda: storage
    app.dependency_overrides[get_rag_service] = lambda: rag
    try:
        response = TestClient(app).post(
            "/rag/ingest/file",
            files={"file": ("policy.txt", "Nghỉ phép trước ba ngày.", "text/plain")},
            data={
                "document_id": "policy-1",
                "metadata": '{"title":"Quy trình nghỉ phép"}',
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["document_id"] == "policy-1"
    rag.ingest.assert_called_once()
    assert rag.ingest.call_args.args[0] == "policy-1"
    assert rag.ingest.call_args.args[2]["filename"] == "policy.txt"
