from vetri_ai.rag.rag_engine import RAGEngine


def test_rag_retrieves_architecture():
    assert RAGEngine().retrieve("Home Assistant backend")
