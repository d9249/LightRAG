"""Standalone implementation of LightRAG document APIs.

이 스크립트는 FastAPI 서버 없이도 `documents` 관련 기능을 테스트할 수 있도록,
LightRAG의 문서 파이프라인 로직을 파이썬 표준 라이브러리만으로 재구성했습니다.

주요 기능
---------
- 입력 디렉터리 스캔 및 파일 인덱싱 (`scan`)
- 파일 업로드 및 즉시 인덱싱 (`upload`)
- 텍스트 단일/다중 입력 처리 (`insert-text`, `insert-texts`)
- 문서 상태 조회, 페이지네이션, 트랙 상태 조회
- 문서/엔티티/관계 삭제, 전체 초기화, 캐시 삭제 등

실행 예시
---------

```bash
python3 documents_standalone.py insert-text --text "OpenAI와 Microsoft가 협력했습니다."
python3 documents_standalone.py documents
python3 documents_standalone.py upload --file NP_ABLGI_35.pdf
python3 documents_standalone.py scan
```

결과는 LightRAG의 REST API 응답 형식과 유사한 JSON으로 출력됩니다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# 경로 및 상수 정의
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent  # upload 디렉터리
DATA_DIR = BASE_DIR  # upload 루트에 바로 저장
INPUT_DIR = BASE_DIR / "inputs"
RAG_DIR = BASE_DIR / "rag_storage"

STORE_FILES: Dict[str, Path] = {
    "docs": RAG_DIR / "kv_store_full_docs.json",
    "doc_status": RAG_DIR / "kv_store_doc_status.json",
    "chunks": RAG_DIR / "kv_store_text_chunks.json",
    "entities": RAG_DIR / "kv_store_full_entities.json",
    "relations": RAG_DIR / "kv_store_full_relations.json",
    "chunk_vectors": RAG_DIR / "vdb_chunks.json",
    "entity_vectors": RAG_DIR / "vdb_entities.json",
    "relation_vectors": RAG_DIR / "vdb_relationships.json",
    "llm_cache": RAG_DIR / "kv_store_llm_response_cache.json",
}

PIPELINE_STATUS_FILE = RAG_DIR / "pipeline_status.json"
GRAPH_FILE = RAG_DIR / "graph_chunk_entity_relation.graphml"

DEFAULT_MAX_TOKEN = 120
DEFAULT_OVERLAP = 40


# ---------------------------------------------------------------------------
# 유틸리티 함수
# ---------------------------------------------------------------------------


def ensure_directories() -> None:
    """필요한 디렉터리를 모두 생성."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def generate_track_id(prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{prefix}_{timestamp}"


def compute_mdhash_id(content: str, prefix: str) -> str:
    hasher = hashlib.md5()
    hasher.update(content.encode("utf-8"))
    return f"{prefix}{hasher.hexdigest()}"


def simple_tokenize(text: str) -> List[str]:
    return [token for token in text.strip().split() if token]


def chunk_text(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKEN,
    overlap: int = DEFAULT_OVERLAP,
) -> List[Dict[str, Any]]:
    tokens = simple_tokenize(text)
    if not tokens:
        return []

    results: List[Dict[str, Any]] = []
    step = max(1, max_tokens - overlap)
    for index in range(0, len(tokens), step):
        slice_tokens = tokens[index : index + max_tokens]
        if not slice_tokens:
            continue
        chunk_text_value = " ".join(slice_tokens)
        results.append(
            {
                "content": chunk_text_value,
                "tokens": len(slice_tokens),
                "chunk_order_index": len(results),
            }
        )
    return results


ENTITY_REGEX = (""  # 대문자로 시작하는 단어들의 연속을 엔티티로 간주
                 "\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})*)\b")


def extract_entities(chunk_text_value: str) -> List[Dict[str, str]]:
    import re

    matches = re.findall(ENTITY_REGEX, chunk_text_value)
    entities: List[Dict[str, str]] = []
    for match in matches:
        cleaned = match.strip()
        if len(cleaned) < 3:
            continue
        entity_id = compute_mdhash_id(cleaned.lower(), "entity-")
        entities.append(
            {
                "entity_id": entity_id,
                "entity_name": cleaned,
                "description": f"Auto extracted entity: {cleaned}",
                "entity_type": "auto",
            }
        )
    return entities


def extract_relations(entities: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    if len(entities) < 2:
        return []
    relations: List[Dict[str, str]] = []
    for source_idx, target_idx in zip(range(len(entities) - 1), range(1, len(entities))):
        source = entities[source_idx]
        target = entities[target_idx]
        relation_name = f"{source['entity_name']} related to {target['entity_name']}"
        relation_id = compute_mdhash_id(relation_name.lower(), "relation-")
        relations.append(
            {
                "relation_id": relation_id,
                "source": source["entity_id"],
                "target": target["entity_id"],
                "description": relation_name,
            }
        )
    return relations


def build_embedding_vector(text: str, dimensions: int = 8) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vector: List[float] = []
    for idx in range(dimensions):
        chunk = digest[idx * 4 : (idx + 1) * 4]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, b"\0")
        value = int.from_bytes(chunk, byteorder="big", signed=False)
        vector.append(value / 2**32)
    return vector


def sanitize_filename(filename: str, input_dir: Path) -> str:
    """문자열을 안전한 파일 이름으로 정제."""

    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")

    clean_name = filename.replace("/", "").replace("\\", "")
    clean_name = clean_name.replace("..", "")
    clean_name = "".join(c for c in clean_name if ord(c) >= 32 and c != "\x7f")
    clean_name = clean_name.strip().strip(".")
    if not clean_name:
        raise ValueError("Invalid filename after sanitization")

    candidate = (input_dir / clean_name).resolve()
    if not candidate.is_relative_to(input_dir.resolve()):
        raise ValueError("Unsafe filename detected")
    return clean_name


def get_unique_filename(target_dir: Path, original_name: str) -> str:
    base = Path(original_name).stem
    suffix = Path(original_name).suffix
    candidate = original_name
    counter = 1
    while (target_dir / candidate).exists():
        candidate = f"{base}_{counter:03d}{suffix}"
        counter += 1
    return candidate


def create_content_summary(text: str, limit: int = 160) -> str:
    stripped = " ".join(text.strip().split())
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class StorageState:
    docs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    doc_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    chunks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    chunk_vectors: Dict[str, List[float]] = field(default_factory=dict)
    entity_vectors: Dict[str, List[float]] = field(default_factory=dict)
    relation_vectors: Dict[str, List[float]] = field(default_factory=dict)
    llm_cache: Dict[str, Any] = field(default_factory=dict)


def load_state() -> StorageState:
    return StorageState(
        docs=load_json(STORE_FILES["docs"], {}),
        doc_status=load_json(STORE_FILES["doc_status"], {}),
        chunks=load_json(STORE_FILES["chunks"], {}),
        entities=load_json(STORE_FILES["entities"], {}),
        relations=load_json(STORE_FILES["relations"], {}),
        chunk_vectors=load_json(STORE_FILES["chunk_vectors"], {}),
        entity_vectors=load_json(STORE_FILES["entity_vectors"], {}),
        relation_vectors=load_json(STORE_FILES["relation_vectors"], {}),
        llm_cache=load_json(STORE_FILES["llm_cache"], {}),
    )


def persist_state(state: StorageState) -> None:
    save_json(STORE_FILES["docs"], state.docs)
    save_json(STORE_FILES["doc_status"], state.doc_status)
    save_json(STORE_FILES["chunks"], state.chunks)
    save_json(STORE_FILES["entities"], state.entities)
    save_json(STORE_FILES["relations"], state.relations)
    save_json(STORE_FILES["chunk_vectors"], state.chunk_vectors)
    save_json(STORE_FILES["entity_vectors"], state.entity_vectors)
    save_json(STORE_FILES["relation_vectors"], state.relation_vectors)
    save_json(STORE_FILES["llm_cache"], state.llm_cache)


def default_pipeline_status() -> Dict[str, Any]:
    return {
        "autoscanned": False,
        "busy": False,
        "job_name": "",
        "job_start": None,
        "docs": 0,
        "batchs": 0,
        "cur_batch": 0,
        "request_pending": False,
        "latest_message": "",
        "history_messages": [],
    }


def load_pipeline_status() -> Dict[str, Any]:
    return load_json(PIPELINE_STATUS_FILE, default_pipeline_status())


def save_pipeline_status(status: Dict[str, Any]) -> None:
    history = status.get("history_messages", [])
    if len(history) > 1000:
        status["history_messages"] = history[-1000:]
    save_json(PIPELINE_STATUS_FILE, status)


def append_history(status: Dict[str, Any], message: str) -> None:
    history = status.setdefault("history_messages", [])
    history.append(f"{iso_now()} - {message}")


def write_graphml(state: StorageState) -> None:
    lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<graphml xmlns=\"http://graphml.graphdrawing.org/xmlns\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd\">",
        "  <key id=\"d0\" for=\"node\" attr.name=\"label\" attr.type=\"string\"/>",
        "  <key id=\"d1\" for=\"node\" attr.name=\"type\" attr.type=\"string\"/>",
        "  <key id=\"d2\" for=\"edge\" attr.name=\"label\" attr.type=\"string\"/>",
        "  <graph id=\"G\" edgedefault=\"undirected\">",
    ]

    for doc_id, doc in state.docs.items():
        label = create_content_summary(doc.get("content", ""), limit=50)
        label = label.replace("\"", "'")
        lines.append(
            f"    <node id=\"{doc_id}\"><data key=\"d0\">{label}</data><data key=\"d1\">document</data></node>"
        )

    for chunk_id, chunk in state.chunks.items():
        label = f"Chunk {chunk.get('chunk_order_index', 0)}"
        lines.append(
            f"    <node id=\"{chunk_id}\"><data key=\"d0\">{label}</data><data key=\"d1\">chunk</data></node>"
        )
        doc_id = chunk.get("doc_id")
        if doc_id:
            edge_id = compute_mdhash_id(f"{doc_id}:{chunk_id}", "edge-")
            lines.append(
                f"    <edge id=\"{edge_id}\" source=\"{doc_id}\" target=\"{chunk_id}\"><data key=\"d2\">contains</data></edge>"
            )

    for entity_id, entity in state.entities.items():
        label = entity.get("entity_name", "entity").replace("\"", "'")
        lines.append(
            f"    <node id=\"{entity_id}\"><data key=\"d0\">{label}</data><data key=\"d1\">entity</data></node>"
        )
        for chunk_id in entity.get("chunk_ids", []):
            if chunk_id in state.chunks:
                edge_id = compute_mdhash_id(f"{chunk_id}:{entity_id}", "edge-")
                lines.append(
                    f"    <edge id=\"{edge_id}\" source=\"{chunk_id}\" target=\"{entity_id}\"><data key=\"d2\">mentions</data></edge>"
                )

    for relation_id, relation in state.relations.items():
        source = relation.get("source")
        target = relation.get("target")
        label = relation.get("description", "").replace("\"", "'")
        if source and target:
            lines.append(
                f"    <edge id=\"{relation_id}\" source=\"{source}\" target=\"{target}\"><data key=\"d2\">{label}</data></edge>"
            )

    lines.append("  </graph>")
    lines.append("</graphml>")

    GRAPH_FILE.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# DocumentManager: 입력 디렉터리 관리
# ---------------------------------------------------------------------------


class DocumentManager:
    def __init__(self, input_dir: Path):
        self.base_input_dir = input_dir
        self.supported_extensions = {
            ".txt",
            ".md",
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".csv",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".log",
            ".conf",
            ".ini",
            ".properties",
            ".sql",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".go",
            ".rb",
            ".php",
            ".html",
            ".htm",
        }

    def scan_directory_for_new_files(self, state: StorageState) -> List[Path]:
        processed = {
            status.get("file_path")
            for status in state.doc_status.values()
            if status.get("file_path")
        }
        new_files: List[Path] = []
        for file_path in self.base_input_dir.glob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.supported_extensions:
                continue
            if str(file_path) in processed:
                continue
            new_files.append(file_path)
        new_files.sort()
        return new_files

    def is_supported_file(self, filename: str) -> bool:
        return any(filename.lower().endswith(ext) for ext in self.supported_extensions)


# ---------------------------------------------------------------------------
# DocumentPipeline: 문서 처리 로직
# ---------------------------------------------------------------------------


class DocumentPipeline:
    def __init__(self) -> None:
        ensure_directories()
        self.manager = DocumentManager(INPUT_DIR)

    # 공통 헬퍼 -------------------------------------------------------------

    def _start_job(self, job_name: str, total_docs: int) -> Dict[str, Any]:
        status = load_pipeline_status()
        status.update(
            {
                "busy": True,
                "job_name": job_name,
                "job_start": iso_now(),
                "docs": total_docs,
                "batchs": total_docs,
                "cur_batch": 0,
                "latest_message": job_name,
                "request_pending": False,
            }
        )
        append_history(status, f"Start job '{job_name}' for {total_docs} documents")
        save_pipeline_status(status)
        return status

    def _complete_job(self, status: Dict[str, Any], message: str) -> None:
        status["busy"] = False
        status["latest_message"] = message
        append_history(status, message)
        save_pipeline_status(status)

    def _process_documents(
        self,
        documents: List[Dict[str, Any]],
        job_name: str,
    ) -> Tuple[List[str], List[str], Dict[str, str]]:
        if not documents:
            return [], [], {}

        state = load_state()

        duplicates: List[str] = []
        for doc in documents:
            if doc["doc_id"] in state.doc_status:
                duplicates.append(doc["doc_id"])

        docs_to_process = [doc for doc in documents if doc["doc_id"] not in state.doc_status]

        status = self._start_job(job_name, len(docs_to_process))

        processed: List[str] = []
        failed: Dict[str, str] = {}

        for index, doc in enumerate(docs_to_process, start=1):
            status["cur_batch"] = index
            status["latest_message"] = f"Processing {doc['doc_id']}"
            append_history(status, status["latest_message"])
            save_pipeline_status(status)

            try:
                self._process_single_document(state, doc)
                processed.append(doc["doc_id"])
            except Exception as exc:  # pylint: disable=broad-except
                failed_message = str(exc)
                failed[doc["doc_id"]] = failed_message
                self._mark_failed_document(state, doc, failed_message)

        persist_state(state)
        write_graphml(state)

        completion = f"Job '{job_name}' finished: {len(processed)} processed, {len(failed)} failed"
        self._complete_job(status, completion)

        return processed, duplicates, failed

    def _process_single_document(self, state: StorageState, doc: Dict[str, Any]) -> None:
        text = doc["text"].strip()
        if not text:
            raise ValueError("문서 내용이 비어 있습니다.")

        chunk_dicts = chunk_text(text)
        if not chunk_dicts:
            raise ValueError("토큰화 결과가 비어 있어 문서를 처리할 수 없습니다.")

        chunk_ids: List[str] = []
        chunk_entities: Dict[str, List[str]] = {}
        relation_ids: List[str] = []
        doc_entity_set: set[str] = set()

        for chunk in chunk_dicts:
            chunk_id = compute_mdhash_id(
                f"{doc['doc_id']}:{chunk['chunk_order_index']}:{chunk['content']}",
                "chunk-",
            )
            chunk_ids.append(chunk_id)
            state.chunks[chunk_id] = {
                "content": chunk["content"],
                "tokens": chunk["tokens"],
                "chunk_order_index": chunk["chunk_order_index"],
                "doc_id": doc["doc_id"],
                "file_path": doc.get("file_path", ""),
            }
            state.chunk_vectors[chunk_id] = build_embedding_vector(chunk["content"])

            entities = extract_entities(chunk["content"])
            entity_ids = self._merge_entities(state, doc["doc_id"], chunk_id, entities)
            chunk_entities[chunk_id] = entity_ids
            doc_entity_set.update(entity_ids)

            relations = extract_relations(entities)
            relation_ids.extend(
                self._merge_relations(state, doc["doc_id"], chunk_id, relations)
            )

        state.docs[doc["doc_id"]] = {
            "content": text,
            "file_path": doc.get("file_path", ""),
            "chunk_ids": chunk_ids,
            "entity_ids": sorted(doc_entity_set),
            "relation_ids": sorted(set(relation_ids)),
            "track_id": doc.get("track_id"),
            "metadata": doc.get("metadata", {}),
        }

        summary = create_content_summary(text)
        now = iso_now()
        state.doc_status[doc["doc_id"]] = {
            "id": doc["doc_id"],
            "content_summary": summary,
            "content_length": len(text),
            "status": "PROCESSED",
            "created_at": now,
            "updated_at": now,
            "track_id": doc.get("track_id"),
            "chunks_count": len(chunk_ids),
            "error_msg": None,
            "metadata": doc.get("metadata"),
            "file_path": doc.get("file_path", ""),
        }

    def _merge_entities(
        self,
        state: StorageState,
        doc_id: str,
        chunk_id: str,
        entities: Iterable[Dict[str, str]],
    ) -> List[str]:
        linked: List[str] = []
        for entity in entities:
            entity_id = entity["entity_id"]
            entry = state.entities.setdefault(
                entity_id,
                {
                    "entity_name": entity["entity_name"],
                    "entity_type": entity.get("entity_type", "auto"),
                    "description": entity.get("description", ""),
                    "doc_ids": [],
                    "chunk_ids": [],
                },
            )
            if doc_id not in entry["doc_ids"]:
                entry["doc_ids"].append(doc_id)
            if chunk_id not in entry["chunk_ids"]:
                entry["chunk_ids"].append(chunk_id)
            if len(entity.get("description", "")) > len(entry.get("description", "")):
                entry["description"] = entity["description"]

            embedding = build_embedding_vector(entity["entity_name"])
            previous = state.entity_vectors.get(entity_id)
            if previous:
                state.entity_vectors[entity_id] = [
                    float((a + b) / 2.0) for a, b in zip(previous, embedding)
                ]
            else:
                state.entity_vectors[entity_id] = embedding
            linked.append(entity_id)
        return linked

    def _merge_relations(
        self,
        state: StorageState,
        doc_id: str,
        chunk_id: str,
        relations: Iterable[Dict[str, str]],
    ) -> List[str]:
        linked: List[str] = []
        for relation in relations:
            relation_id = relation["relation_id"]
            entry = state.relations.setdefault(
                relation_id,
                {
                    "source": relation["source"],
                    "target": relation["target"],
                    "description": relation.get("description", ""),
                    "doc_ids": [],
                    "chunk_ids": [],
                },
            )
            if doc_id not in entry["doc_ids"]:
                entry["doc_ids"].append(doc_id)
            if chunk_id not in entry["chunk_ids"]:
                entry["chunk_ids"].append(chunk_id)
            if len(relation.get("description", "")) > len(entry.get("description", "")):
                entry["description"] = relation["description"]

            embedding = build_embedding_vector(entry["description"] or relation_id)
            previous = state.relation_vectors.get(relation_id)
            if previous:
                state.relation_vectors[relation_id] = [
                    float((a + b) / 2.0) for a, b in zip(previous, embedding)
                ]
            else:
                state.relation_vectors[relation_id] = embedding
            linked.append(relation_id)
        return linked

    def _mark_failed_document(
        self, state: StorageState, doc: Dict[str, Any], message: str
    ) -> None:
        now = iso_now()
        state.doc_status[doc["doc_id"]] = {
            "id": doc["doc_id"],
            "content_summary": create_content_summary(doc["text"]),
            "content_length": len(doc["text"]),
            "status": "FAILED",
            "created_at": now,
            "updated_at": now,
            "track_id": doc.get("track_id"),
            "chunks_count": 0,
            "error_msg": message,
            "metadata": doc.get("metadata"),
            "file_path": doc.get("file_path", ""),
        }

    # 공개 메서드 ---------------------------------------------------------

    def scan(self) -> Dict[str, Any]:
        state = load_state()
        new_files = self.manager.scan_directory_for_new_files(state)
        if not new_files:
            message = "No new files found in input directory."
            status = load_pipeline_status()
            append_history(status, message)
            save_pipeline_status(status)
            return {
                "status": "scanning_started",
                "message": message,
                "track_id": generate_track_id("scan"),
            }

        documents: List[Dict[str, Any]] = []
        track_id = generate_track_id("scan")
        for path in new_files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            documents.append(
                {
                    "doc_id": compute_mdhash_id(text, "doc-"),
                    "text": text,
                    "file_path": str(path),
                    "metadata": {"source": str(path)},
                    "track_id": track_id,
                }
            )

        processed, duplicates, failed = self._process_documents(
            documents, job_name="Scanning input directory"
        )

        message = (
            f"Scan completed: processed={len(processed)}, duplicates={len(duplicates)}, failed={len(failed)}"
        )
        return {"status": "scanning_started", "message": message, "track_id": track_id}

    def upload(self, source: Path) -> Dict[str, Any]:
        if not source.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {source}")

        safe_name = sanitize_filename(source.name, INPUT_DIR)
        if not self.manager.is_supported_file(safe_name):
            raise ValueError("Unsupported file type for upload")

        target_name = get_unique_filename(INPUT_DIR, safe_name)
        target_path = INPUT_DIR / target_name
        if target_path.exists():
            return {
                "status": "duplicated",
                "message": f"File '{target_name}' already exists in the input directory.",
                "track_id": "",
            }

        shutil.copy2(source, target_path)
        text = target_path.read_text(encoding="utf-8", errors="ignore")
        track_id = generate_track_id("upload")
        documents = [
            {
                "doc_id": compute_mdhash_id(text, "doc-"),
                "text": text,
                "file_path": str(target_path),
                "metadata": {"source": str(target_path)},
                "track_id": track_id,
            }
        ]

        processed, duplicates, failed = self._process_documents(
            documents, job_name="Uploading document"
        )

        if failed:
            status = "failure"
            message = f"Failed to process upload: {failed}"
        elif not processed:
            status = "duplicated"
            message = "Document already exists and was not reprocessed."
        else:
            status = "success"
            message = f"File '{target_name}' uploaded and processed successfully."

        return {"status": status, "message": message, "track_id": track_id}

    def insert_text(self, text: str, file_source: Optional[str]) -> Dict[str, Any]:
        track_id = generate_track_id("insert")
        documents = [
            {
                "doc_id": compute_mdhash_id(text, "doc-"),
                "text": text,
                "file_path": file_source or "",
                "metadata": {"source": file_source} if file_source else {},
                "track_id": track_id,
            }
        ]
        processed, duplicates, failed = self._process_documents(
            documents, job_name="Inserting text"
        )

        status = "success"
        if failed:
            status = "failure"
        elif duplicates and not processed:
            status = "duplicated"

        message = (
            f"Text processed. processed={len(processed)}, duplicates={len(duplicates)}, failed={len(failed)}"
        )
        return {"status": status, "message": message, "track_id": track_id}

    def insert_texts(
        self, texts: List[str], file_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        track_id = generate_track_id("insert")
        file_sources = file_sources or []
        if file_sources and len(file_sources) != len(texts):
            raise ValueError("file_sources 길이는 texts 길이와 같아야 합니다.")

        documents: List[Dict[str, Any]] = []
        for idx, text in enumerate(texts):
            source = file_sources[idx] if idx < len(file_sources) else None
            documents.append(
                {
                    "doc_id": compute_mdhash_id(text, "doc-"),
                    "text": text,
                    "file_path": source or "",
                    "metadata": {"source": source} if source else {},
                    "track_id": track_id,
                }
            )

        processed, duplicates, failed = self._process_documents(
            documents, job_name="Inserting texts"
        )

        if failed and processed:
            status = "partial_success"
        elif failed and not processed:
            status = "failure"
        elif duplicates and not processed:
            status = "duplicated"
        else:
            status = "success"

        message = (
            f"Texts processed. processed={len(processed)}, duplicates={len(duplicates)}, failed={len(failed)}"
        )
        return {"status": status, "message": message, "track_id": track_id}

    def documents(self) -> Dict[str, Any]:
        state = load_state()
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for doc_id, status in state.doc_status.items():
            entry = dict(status)
            entry.setdefault("id", doc_id)
            grouped[entry.get("status", "UNKNOWN")].append(entry)

        for docs in grouped.values():
            docs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return {"statuses": grouped}

    def pipeline_status(self) -> Dict[str, Any]:
        status = load_pipeline_status()
        status.setdefault("history_messages", [])
        return status

    def delete_documents(self, doc_ids: List[str]) -> Dict[str, Any]:
        if not doc_ids:
            raise ValueError("삭제할 문서 ID를 입력하세요.")

        state = load_state()
        status = self._start_job(
            job_name=f"Deleting {len(doc_ids)} documents", total_docs=len(doc_ids)
        )

        deleted: List[str] = []
        not_found: List[str] = []

        for index, doc_id in enumerate(doc_ids, start=1):
            status["cur_batch"] = index
            status["latest_message"] = f"Deleting {doc_id}"
            append_history(status, status["latest_message"])
            save_pipeline_status(status)

            if doc_id not in state.doc_status:
                not_found.append(doc_id)
                continue

            self._delete_single_document(state, doc_id)
            deleted.append(doc_id)

        persist_state(state)
        write_graphml(state)

        message = (
            f"Deletion finished. deleted={len(deleted)}, not_found={len(not_found)}"
        )
        self._complete_job(status, message)

        return {
            "status": "deletion_started",
            "message": message,
            "doc_id": ", ".join(doc_ids),
        }

    def _delete_single_document(self, state: StorageState, doc_id: str) -> None:
        doc = state.docs.get(doc_id, {})
        chunk_ids = doc.get("chunk_ids", [])
        entity_ids = doc.get("entity_ids", [])
        relation_ids = doc.get("relation_ids", [])

        for chunk_id in chunk_ids:
            state.chunks.pop(chunk_id, None)
            state.chunk_vectors.pop(chunk_id, None)

        for entity_id in entity_ids:
            entry = state.entities.get(entity_id)
            if not entry:
                continue
            entry["doc_ids"] = [d for d in entry.get("doc_ids", []) if d != doc_id]
            entry["chunk_ids"] = [c for c in entry.get("chunk_ids", []) if c not in chunk_ids]
            if not entry["doc_ids"]:
                state.entities.pop(entity_id, None)
                state.entity_vectors.pop(entity_id, None)

        for relation_id in relation_ids:
            entry = state.relations.get(relation_id)
            if not entry:
                continue
            entry["doc_ids"] = [d for d in entry.get("doc_ids", []) if d != doc_id]
            entry["chunk_ids"] = [c for c in entry.get("chunk_ids", []) if c not in chunk_ids]
            if not entry["doc_ids"]:
                state.relations.pop(relation_id, None)
                state.relation_vectors.pop(relation_id, None)

        state.docs.pop(doc_id, None)
        state.doc_status.pop(doc_id, None)

    def clear_documents(self) -> Dict[str, Any]:
        state = StorageState()
        persist_state(state)
        write_graphml(state)

        # 입력 디렉터리 파일 삭제
        deleted_files = 0
        for file_path in INPUT_DIR.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                deleted_files += 1

        status = self._start_job("Clearing documents", 0)
        message = f"All documents cleared. Deleted files: {deleted_files}"
        self._complete_job(status, message)

        return {"status": "success", "message": message}

    def clear_cache(self) -> Dict[str, Any]:
        state = load_state()
        state.llm_cache = {}
        persist_state(state)
        append_history(load_pipeline_status(), "Cleared cache")
        return {"status": "success", "message": "Successfully cleared cache"}

    def delete_entity(self, entity_name: str) -> Dict[str, Any]:
        state = load_state()
        target_id = None
        for entity_id, entity in state.entities.items():
            if entity.get("entity_name") == entity_name:
                target_id = entity_id
                break

        if not target_id:
            return {
                "status": "not_found",
                "doc_id": "",
                "message": f"Entity '{entity_name}' not found.",
                "status_code": 404,
                "file_path": None,
            }

        state.entities.pop(target_id, None)
        state.entity_vectors.pop(target_id, None)

        relations_to_remove = [
            rel_id
            for rel_id, rel in state.relations.items()
            if rel.get("source") == target_id or rel.get("target") == target_id
        ]
        for rel_id in relations_to_remove:
            state.relations.pop(rel_id, None)
            state.relation_vectors.pop(rel_id, None)

        for doc in state.docs.values():
            doc["entity_ids"] = [eid for eid in doc.get("entity_ids", []) if eid != target_id]
            doc["relation_ids"] = [rid for rid in doc.get("relation_ids", []) if rid not in relations_to_remove]

        persist_state(state)
        write_graphml(state)

        return {
            "status": "success",
            "doc_id": "",
            "message": f"Entity '{entity_name}' deleted.",
            "status_code": 200,
            "file_path": None,
        }

    def delete_relation(self, source: str, target: str) -> Dict[str, Any]:
        state = load_state()
        target_id = None
        for relation_id, relation in state.relations.items():
            if relation.get("source") == source and relation.get("target") == target:
                target_id = relation_id
                break

        if not target_id:
            return {
                "status": "not_found",
                "doc_id": "",
                "message": f"Relation {source}->{target} not found.",
                "status_code": 404,
                "file_path": None,
            }

        state.relations.pop(target_id, None)
        state.relation_vectors.pop(target_id, None)

        for doc in state.docs.values():
            doc["relation_ids"] = [rid for rid in doc.get("relation_ids", []) if rid != target_id]

        persist_state(state)
        write_graphml(state)

        return {
            "status": "success",
            "doc_id": "",
            "message": f"Relation {source}->{target} deleted.",
            "status_code": 200,
            "file_path": None,
        }

    def track_status(self, track_id: str) -> Dict[str, Any]:
        state = load_state()
        documents: List[Dict[str, Any]] = []
        status_summary: Dict[str, int] = defaultdict(int)

        for status in state.doc_status.values():
            if status.get("track_id") != track_id:
                continue
            documents.append(status)
            status_summary[str(status.get("status"))] += 1

        return {
            "track_id": track_id,
            "documents": documents,
            "total_count": len(documents),
            "status_summary": status_summary,
        }

    def paginated(
        self,
        page: int,
        page_size: int,
        status_filter: Optional[str],
        sort_field: str,
        sort_direction: str,
    ) -> Dict[str, Any]:
        state = load_state()
        documents = list(state.doc_status.values())

        if status_filter:
            documents = [doc for doc in documents if doc.get("status") == status_filter]

        reverse = sort_direction.lower() == "desc"
        if sort_field == "created_at":
            documents.sort(key=lambda doc: doc.get("created_at", ""), reverse=reverse)
        elif sort_field == "updated_at":
            documents.sort(key=lambda doc: doc.get("updated_at", ""), reverse=reverse)
        elif sort_field == "file_path":
            documents.sort(key=lambda doc: doc.get("file_path", ""), reverse=reverse)
        else:  # default id
            documents.sort(key=lambda doc: doc.get("id", ""), reverse=reverse)

        total_count = len(documents)
        start = (page - 1) * page_size
        end = start + page_size
        page_docs = documents[start:end]

        status_counts = defaultdict(int)
        for doc in state.doc_status.values():
            status_counts[doc.get("status", "UNKNOWN")] += 1

        total_pages = (total_count + page_size - 1) // page_size if page_size else 1

        return {
            "documents": page_docs,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "status_counts": dict(status_counts),
        }

    def status_counts(self) -> Dict[str, Any]:
        state = load_state()
        counts = defaultdict(int)
        for doc in state.doc_status.values():
            counts[doc.get("status", "UNKNOWN")] += 1
        return {"status_counts": dict(counts)}


# ---------------------------------------------------------------------------
# CLI 구현
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone LightRAG Document API")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="Scan input directory for new files")

    upload_parser = subparsers.add_parser("upload", help="Upload and index a file")
    upload_parser.add_argument("--file", required=True, help="File path to upload")

    insert_parser = subparsers.add_parser("insert-text", help="Insert single text")
    insert_parser.add_argument("--text", required=True, help="Text content")
    insert_parser.add_argument("--file-source", help="Optional source info")

    insert_texts_parser = subparsers.add_parser(
        "insert-texts", help="Insert multiple texts"
    )
    insert_texts_parser.add_argument(
        "--text",
        dest="texts",
        action="append",
        required=True,
        help="Text content (repeatable)",
    )
    insert_texts_parser.add_argument(
        "--file-source",
        dest="file_sources",
        action="append",
        help="Optional file source (repeatable)",
    )

    subparsers.add_parser("documents", help="List documents by status")
    subparsers.add_parser("pipeline-status", help="Show pipeline status")

    delete_parser = subparsers.add_parser("delete-document", help="Delete documents")
    delete_parser.add_argument(
        "--doc-id",
        dest="doc_ids",
        action="append",
        required=True,
        help="Document ID to delete (repeatable)",
    )

    subparsers.add_parser("clear-documents", help="Clear all documents and files")
    subparsers.add_parser("clear-cache", help="Clear LLM cache")

    delete_entity_parser = subparsers.add_parser(
        "delete-entity", help="Delete an entity"
    )
    delete_entity_parser.add_argument("--name", required=True, help="Entity name")

    delete_relation_parser = subparsers.add_parser(
        "delete-relation", help="Delete a relation"
    )
    delete_relation_parser.add_argument("--source", required=True, help="Source entity ID")
    delete_relation_parser.add_argument("--target", required=True, help="Target entity ID")

    track_parser = subparsers.add_parser("track-status", help="Get status by track ID")
    track_parser.add_argument("--track-id", required=True, help="Track ID")

    paginated_parser = subparsers.add_parser("paginated", help="Get documents paginated")
    paginated_parser.add_argument("--page", type=int, default=1)
    paginated_parser.add_argument("--page-size", type=int, default=50)
    paginated_parser.add_argument("--status", help="Filter by status")
    paginated_parser.add_argument(
        "--sort-field",
        choices=["created_at", "updated_at", "id", "file_path"],
        default="updated_at",
    )
    paginated_parser.add_argument(
        "--sort-direction", choices=["asc", "desc"], default="desc"
    )

    subparsers.add_parser("status-counts", help="Get document status counts")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pipeline = DocumentPipeline()

    try:
        if args.command == "scan":
            result = pipeline.scan()
        elif args.command == "upload":
            result = pipeline.upload(Path(args.file))
        elif args.command == "insert-text":
            result = pipeline.insert_text(args.text, args.file_source)
        elif args.command == "insert-texts":
            result = pipeline.insert_texts(args.texts, args.file_sources)
        elif args.command == "documents":
            result = pipeline.documents()
        elif args.command == "pipeline-status":
            result = pipeline.pipeline_status()
        elif args.command == "delete-document":
            result = pipeline.delete_documents(args.doc_ids)
        elif args.command == "clear-documents":
            result = pipeline.clear_documents()
        elif args.command == "clear-cache":
            result = pipeline.clear_cache()
        elif args.command == "delete-entity":
            result = pipeline.delete_entity(args.name)
        elif args.command == "delete-relation":
            result = pipeline.delete_relation(args.source, args.target)
        elif args.command == "track-status":
            result = pipeline.track_status(args.track_id)
        elif args.command == "paginated":
            result = pipeline.paginated(
                page=args.page,
                page_size=args.page_size,
                status_filter=args.status,
                sort_field=args.sort_field,
                sort_direction=args.sort_direction,
            )
        elif args.command == "status-counts":
            result = pipeline.status_counts()
        else:
            parser.error(f"Unknown command: {args.command}")
            return 1

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

