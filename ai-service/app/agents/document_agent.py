# document_agent.py
"""
Document Intelligence & RAG Agent for NBA Accreditation Evidence.

Responsibilities:
1. Grounded Question-Answering: Queries ingested institutional documents (syllabi,
   appointment letters, research papers, patent certificates, NBA SAR manual)
   and provides factually bounded answers with exact document citations.
2. Structured Entity Extraction: Parses unstructured documents to extract
   Course Outcomes (COs), assessment weightages, faculty designations, and DOIs.
3. Strict Verification & Provenance: Never hallucinates facts not present in the
   retrieved evidence passages. Declares missing information explicitly.

Note on RAG architecture:
  The backend (PostgreSQL/pgvector) is the single authoritative document store.
  This agent receives pre-retrieved passages from the backend RAG service and
  must NOT maintain its own vector store or perform its own retrieval.
"""

from typing import Any, Dict, List, Optional

from app.services.model_client import call_model


def _build_context_str(passages: List[Dict]) -> str:
    """Format retrieved passages into a numbered evidence block for the prompt."""
    if not passages:
        return "(No evidence passages were retrieved.)"
    lines = []
    for i, p in enumerate(passages, start=1):
        doc_name = p.get("document_name", "Unknown document")
        page = p.get("page_number", "?")
        heading = p.get("section_heading", "")
        content = p.get("content", "")
        header = f"[{i}] Source: {doc_name}, Page: {page}"
        if heading:
            header += f", Section: {heading}"
        lines.append(header)
        lines.append(content.strip())
        lines.append("")
    return "\n".join(lines)


def _build_sources_summary(passages: List[Dict]) -> List[Dict]:
    """Extract a deduplicated list of source references from passages."""
    seen: set = set()
    sources = []
    for p in passages:
        doc_name = p.get("document_name", "Unknown document")
        page = p.get("page_number", "?")
        key = (doc_name, page)
        if key not in seen:
            seen.add(key)
            sources.append({"document_name": doc_name, "page_number": page})
    return sources


def answer_document_query(
    query: str,
    passages: Optional[List[Dict]] = None,
    criterion_filter: Optional[str] = None,
    top_k: int = 4,
    mock_response: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform a RAG-grounded query using passages pre-retrieved from the backend RAG.

    The backend (PostgreSQL/pgvector) retrieves the passages; this agent only
    reasons over them and returns a grounded answer with citations.

    Args:
        query:            The accreditation question to answer.
        passages:         Pre-retrieved evidence passages from the backend RAG.
                          Each passage must have: document_name, page_number,
                          content. Optional fields: chunk_id, document_id,
                          section_heading, similarity_score.
        criterion_filter: Informational — which NBA criterion the query is for.
        top_k:            Informational — how many passages were requested.
        mock_response:    If set, bypasses the LLM and returns this text.

    Returns:
        Dictionary containing:
        - query
        - answer (LLM generated with citations)
        - sources (list of cited source documents and page numbers)
        - chunks_retrieved_count
    """
    if passages is None:
        passages = []

    sources = _build_sources_summary(passages)
    context_str = _build_context_str(passages)

    # Build factually bounded RAG prompt
    prompt = f"""
You are the Document Intelligence & RAG Agent in an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to answer the following accreditation query
STRICTLY using the retrieved evidence passages provided below.

==================================================
GROUNDING & CITATION RULES
==================================================

1. Base your answer ONLY on the provided evidence passages.
2. DO NOT assume, extrapolate, or invent facts not present in the text.
3. ALWAYS cite the source document and page number for every claim made
   (e.g., "[Source: Course_Syllabus.pdf, Page: 2]").
4. If the retrieved evidence does not contain the answer, explicitly state:
   "The uploaded institutional documents do not contain information regarding this query."
5. Never hallucinate numbers, accreditation grades, or compliance approvals.

==================================================
RETRIEVED DOCUMENT EVIDENCE PASSAGES
==================================================

{context_str}

==================================================
USER QUERY
==================================================

"{query}"

==================================================
ANSWER WITH CITATIONS
==================================================
"""

    answer_text = call_model(
        prompt=prompt,
        max_output_tokens=1500,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )

    return {
        "status": "success",
        "query": query,
        "criterion_filter": criterion_filter,
        "answer": answer_text,
        "sources": sources,
        "chunks_retrieved_count": len(passages)
    }


def extract_structured_entities_from_document(
    document_text: str,
    target_criterion: str = "Criterion 3",
    mock_response: Optional[str] = None
) -> str:
    """
    Extract structured academic entities (e.g. COs, Bloom levels, SFR fields, research DOIs)
    from unstructured document text.
    """
    prompt = f"""
You are the Document Intelligence Agent in an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to extract structured accreditation information
for {target_criterion} from the document text provided below.

==================================================
EXTRACTION RULES
==================================================

1. Extract ONLY facts explicitly stated in the document text.
2. DO NOT invent course codes, names, percentages, or faculty designations.
3. If an entity is not mentioned, omit it or mark it as "Not specified in document".
4. Format the output cleanly with clear labels or JSON structure.

==================================================
DOCUMENT TEXT
==================================================

{document_text[:4000]}

==================================================
STRUCTURED EXTRACTED ENTITIES
==================================================
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=1800,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )
