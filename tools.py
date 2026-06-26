"""
Azure-backed tools for the medical agent.
Each function is decorated with @beta_tool so the SDK auto-generates the JSON schema
and the tool runner can call them automatically.
"""

import json
import logging
import uuid
import httpx
from datetime import datetime, timezone
from anthropic import beta_tool
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
from config import config

logger = logging.getLogger(__name__)

# Lazy-init Azure clients so missing env vars surface clearly at first use
_search_client: SearchClient | None = None
_blob_service: BlobServiceClient | None = None
_table_service: TableServiceClient | None = None
UNANSWERED_TABLE = "unansweredqueries"


def _get_table_service() -> TableServiceClient | None:
    global _table_service
    if _table_service is None:
        try:
            _table_service = TableServiceClient.from_connection_string(config.STORAGE_CONN_STR)
            _table_service.create_table_if_not_exists(UNANSWERED_TABLE)
        except Exception as exc:
            logger.warning("Table Storage not available: %s", exc)
            return None
    return _table_service


def _log_unanswered_query(query: str) -> None:
    service = _get_table_service()
    if service is None:
        return
    try:
        table = service.get_table_client(UNANSWERED_TABLE)
        table.upsert_entity({
            "PartitionKey": "unanswered",
            "RowKey": str(uuid.uuid4()),
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Logged unanswered query: %s", query)
    except Exception as exc:
        logger.warning("Failed to log unanswered query: %s", exc)


def _get_search_client() -> SearchClient:
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(
            endpoint=config.SEARCH_ENDPOINT,
            index_name=config.SEARCH_INDEX,
            credential=AzureKeyCredential(config.SEARCH_KEY),
        )
    return _search_client


def _get_blob_service() -> BlobServiceClient:
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobServiceClient.from_connection_string(config.STORAGE_CONN_STR)
    return _blob_service


# ---------------------------------------------------------------------------
# Tool 1: Search medical knowledge base (Azure AI Search / RAG)
# ---------------------------------------------------------------------------

@beta_tool
def search_medical_knowledge(query: str, top_k: int = 5) -> str:
    """
    Search the medical knowledge base for information about diseases, symptoms, and treatments.
    Call this when the user describes symptoms, names a disease, or asks about medical conditions.

    Args:
        query: Medical query — symptoms, disease names, body parts, or clinical terms.
        top_k: Number of top results to return (default 5, max 10).
    """
    top_k = min(top_k, 10)
    try:
        client = _get_search_client()
        results = client.search(
            search_text=query,
            top=top_k,
            select=["title", "content", "source", "category"],
        )
        docs = [
            {
                "title": r.get("title", ""),
                "content": (r.get("content") or "")[:600],
                "source": r.get("source", ""),
                "category": r.get("category", ""),
            }
            for r in results
        ]
        if not docs:
            _log_unanswered_query(query)
            return json.dumps({"found": False, "message": "No results found for this query."})
        return json.dumps({"found": True, "count": len(docs), "results": docs}, indent=2)
    except Exception as exc:
        logger.error("Azure AI Search error: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool 2: Drug information (OpenFDA — free, no key required)
# ---------------------------------------------------------------------------

@beta_tool
def get_drug_information(drug_name: str) -> str:
    """
    Retrieve FDA-sourced information about a drug: indications, warnings, side effects, and dosage.
    Call this before recommending any medication so you can cite accurate, official drug data.

    Args:
        drug_name: Generic or brand name of the drug (e.g. "ibuprofen", "amoxicillin").
    """
    url = "https://api.fda.gov/drug/label.json"
    params = {
        "search": f'openfda.generic_name:"{drug_name}"+OR+openfda.brand_name:"{drug_name}"',
        "limit": 1,
    }
    try:
        with httpx.Client(timeout=10.0) as http:
            resp = http.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if not data.get("results"):
            return json.dumps({"found": False, "message": f"No FDA label found for '{drug_name}'."})

        r = data["results"][0]

        def _first(key: str, limit: int = 400) -> str:
            val = r.get(key)
            return (val[0] if isinstance(val, list) and val else "")[:limit]

        info = {
            "name": drug_name,
            "indications": _first("indications_and_usage"),
            "warnings": _first("warnings"),
            "adverse_reactions": _first("adverse_reactions"),
            "dosage_notes": _first("dosage_and_administration"),
            "contraindications": _first("contraindications"),
        }
        return json.dumps({"found": True, "drug": info}, indent=2)
    except httpx.HTTPStatusError as exc:
        logger.error("OpenFDA HTTP error: %s", exc)
        return json.dumps({"error": f"OpenFDA returned {exc.response.status_code}"})
    except Exception as exc:
        logger.error("Drug lookup error: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool 3: Retrieve treatment guideline from Azure Blob Storage
# ---------------------------------------------------------------------------

@beta_tool
def get_treatment_guideline(document_name: str) -> str:
    """
    Retrieve a clinical treatment guideline or medical protocol document from Azure Blob Storage.
    Use this when you want evidence-based protocols for a specific condition.
    Document names follow the pattern '<condition>-guidelines.txt' (e.g. 'diabetes-guidelines.txt').

    Args:
        document_name: Blob filename including extension (e.g. 'hypertension-guidelines.txt').
    """
    try:
        service = _get_blob_service()
        blob = service.get_blob_client(
            container=config.STORAGE_CONTAINER,
            blob=document_name,
        )
        content: str = blob.download_blob().readall().decode("utf-8")
        # Trim to avoid excessive context usage — the agent can call again for more
        return json.dumps({"found": True, "document": document_name, "content": content[:2500]})
    except Exception as exc:
        logger.warning("Blob retrieval failed for '%s': %s", document_name, exc)
        return json.dumps({"found": False, "message": f"Document '{document_name}' not available."})


# Exported list consumed by agent.py
TOOLS = [search_medical_knowledge, get_drug_information, get_treatment_guideline]
