"""
Uploads EndlessMedical JSON data to Azure AI Search index.
Run once to populate the medical-knowledge index.
"""

import json
import re
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType
)
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os

load_dotenv()

ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX = os.getenv("AZURE_SEARCH_INDEX", "medical-knowledge")

BOOKS_DIR = os.path.join(os.path.dirname(__file__), "books")


def safe_id(raw: str, prefix: str = "") -> str:
    return prefix + re.sub(r"[^a-zA-Z0-9_\-]", "_", raw)


def create_index():
    client = SearchIndexClient(ENDPOINT, AzureKeyCredential(KEY))
    index = SearchIndex(
        name=INDEX,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
        ]
    )
    try:
        client.create_index(index)
        print("Index created.")
    except Exception:
        client.create_or_update_index(index)
        print("Index already exists — updated.")


def upload_batch(search_client, docs):
    results = search_client.upload_documents(documents=docs)
    failed = [r for r in results if not r.succeeded]
    if failed:
        print(f"  {len(failed)} documents failed to upload")


def load_diseases(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for entry in data:
        name = entry.get("name", "")
        text = entry.get("text", "")
        laytext = entry.get("laytext", text)
        category = entry.get("category", "")
        alias = entry.get("alias", "")
        icd10 = entry.get("ICD10", "")
        risk = entry.get("Risk", "")
        flags = []
        if entry.get("IsRare"):
            flags.append("rare disease")
        if entry.get("IsImmLifeThreatening"):
            flags.append("life threatening")
        if entry.get("IsCantMiss"):
            flags.append("cannot miss diagnosis")
        if entry.get("IsGenderSpecific"):
            flags.append("gender specific")

        content_parts = [text, laytext]
        if alias:
            content_parts.append(f"Also known as: {alias}")
        if icd10:
            content_parts.append(f"ICD-10: {icd10}")
        if category:
            content_parts.append(f"Category: {category}")
        if risk:
            content_parts.append(f"Risk level: {risk}")
        if flags:
            content_parts.append(", ".join(flags))

        docs.append({
            "id": safe_id(name, "dis_"),
            "title": laytext or text,
            "content": " | ".join(filter(None, content_parts)),
            "source": "EndlessMedical-Diseases",
            "category": category,
        })
    return docs


def load_symptoms(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for entry in data:
        name = entry.get("name", "")
        text = entry.get("text", "")
        laytext = entry.get("laytext", text)
        category = entry.get("category", "")
        alias = entry.get("alias", "")
        subcats = " | ".join(filter(None, [
            entry.get("subcategory1", ""),
            entry.get("subcategory2", ""),
            entry.get("subcategory3", ""),
            entry.get("subcategory4", ""),
        ]))

        content_parts = [text, laytext]
        if alias:
            content_parts.append(f"Also known as: {alias}")
        if category:
            content_parts.append(f"Category: {category}")
        if subcats:
            content_parts.append(f"Subcategory: {subcats}")
        if entry.get("IsInvasive"):
            content_parts.append("invasive test")

        docs.append({
            "id": safe_id(name, "sym_"),
            "title": laytext or text,
            "content": " | ".join(filter(None, content_parts)),
            "source": "EndlessMedical-Symptoms",
            "category": category,
        })
    return docs


def upload_all(docs: list[dict], label: str):
    search_client = SearchClient(ENDPOINT, INDEX, AzureKeyCredential(KEY))
    batch_size = 500
    print(f"Uploading {len(docs)} {label} documents...")
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        upload_batch(search_client, batch)
        print(f"  Uploaded {min(i + batch_size, len(docs))}/{len(docs)}")
    print(f"Done uploading {label}.")


if __name__ == "__main__":
    create_index()

    diseases = load_diseases(os.path.join(BOOKS_DIR, "DiseasesOutput.json"))
    upload_all(diseases, "diseases")

    symptoms = load_symptoms(os.path.join(BOOKS_DIR, "SymptomsOutput.json"))
    upload_all(symptoms, "symptoms")

    print("\nAll done! Your medical knowledge base is ready.")
