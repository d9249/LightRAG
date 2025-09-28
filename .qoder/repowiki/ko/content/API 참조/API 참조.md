
# API 참조

<cite>
**이 문서에서 참조된 파일**   
- [document_routes.py](file://lightrag/api/routers/document_routes.py)
- [graph_routes.py](file://lightrag/api/routers/graph_routes.py)
- [query_routes.py](file://lightrag/api/routers/query_routes.py)
- [ollama_api.py](file://lightrag/api/routers/ollama_api.py)
- [auth.py](file://lightrag/api/auth.py)
- [config.py](file://lightrag/api/config.py)
</cite>

## 목차
1. [문서 관리 API](#문서-관리-api)
2. [그래프 조회 및 시각화 API](#그래프-조회-및-시각화-api)
3. [검색 쿼리 API](#검색-쿼리-api)
4. [Ollama 호환 API](#ollama-호환-api)
5. [인증 및 보안](#인증-및-보안)
6. [오류 응답 코드](#오류-응답-코드)

## 문서 관리 API

LightRAG 서버는 문서 업로드, 삭제, 상태 조회 등을 위한 다양한 API 엔드포인트를 제공합니다. 이러한 엔드포인트는 `document_routes.py` 파일에 정의되어 있으며, 인증이 필요합니다.

### 문서 업로드

문서를 업로드하고 처리 파이프라인에 추가합니다.

**HTTP 메서드**: `POST`  
**URL 패턴**: `/documents/upload`  
**인증 방법**: JWT 토큰 또는 API 키

#### 요청 스키마
- **Content-Type**: `multipart/form-data`
- **파라미터**:
  - `file` (필수): 업로드할 파일

#### 응답 스키마
```json
{
  "status": "success",
  "message": "File 'document.pdf' uploaded successfully. Processing will continue in background.",
  "track_id": "upload_20250729_170612_abc123"
}
```

- **status**: 업로드 상태 (`success`, `duplicated`, `failure`)
- **message**: 작업 결과에 대한 상세 메시지
- **track_id**: 처리 진행 상황을 추적하기 위한 ID

#### 사용 예시
```bash
curl -X POST "http://localhost:9621/documents/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@path/to/document.pdf"
```

```python
import requests

url = "http://localhost:9621/documents/upload"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
files = {"file": open("path/to/document.pdf", "rb")}

response = requests.post(url, headers=headers, files=files)
print(response.json())
```

**Section sources**
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L1600-L1720)

### 문서 삭제

하나 이상의 문서를 삭제합니다.

**HTTP 메서드**: `DELETE`  
**URL 패턴**: `/documents/delete_document`  
**인증 방법**: JWT 토큰 또는 API 키

#### 요청 스키마
```json
{
  "doc_ids": ["doc_123", "doc_456"],
  "delete_file": true
}
```

- **doc_ids** (필수): 삭제할 문서 ID 목록
- **delete_file** (선택): 입력 디렉터리에서 해당 파일도 삭제할지 여부 (기본값: `false`)

#### 응답 스키마
```json
{
  "status": "deletion_started",
  "message": "Document deletion for 2 documents has been initiated. Processing will continue in background.",
  "doc_id": "doc_123, doc_456"
}
```

- **status**: 삭제 작업 상태 (`deletion_started`, `busy`, `not_allowed`)
- **message**: 작업 결과에 대한 상세 메시지
- **doc_id**: 삭제 요청된 문서 ID

#### 사용 예시
```bash
curl -X DELETE "http://localhost:9621/documents/delete_document" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": ["doc_123", "doc_456"], "delete_file": true}'
```

```python
import requests

url = "http://localhost:9621/documents/delete_document"
headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "doc_ids": ["doc_123", "doc_456"],
    "delete_file": True
}

response = requests.delete(url, headers=headers, json=data)
print(response.json())
```

**Section sources**
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L2000-L2050)

### 문서 목록 조회

시스템에 있는 모든 문서의 상태를 조회합니다.

**HTTP 메서드**: `GET`  
**URL 패턴**: `/documents`  
**인증 방법**: JWT 토큰 또는 API 키

#### 응답 스키마
```json
{
  "statuses": {
    "PROCESSED": [
      {
        "id": "doc_123456",
        "content_summary": "Research paper on machine learning",
        "content_length": 15240,
        "status": "PROCESSED",
        "created_at": "2025-03-31T12:34:56",
        "updated_at": "2025-03-31T12:35:30",
        "track_id": "upload_20250729_170612_abc123",
        "chunks_count": 12,
        "error_msg": null,
        "metadata": {"author": "John Doe", "year": 2025},
        "file_path": "research_paper.pdf"
      }
    ],
    "PENDING": [
      {
        "id": "doc_789012",
        "content_summary": "Pending document",
        "content_length": 5000,
        "status": "PENDING",
        "created_at": "2025-03-31T10:00:00",
        "updated_at": "2025-03-31T10:00:00",
        "track_id": "upload_20250331_100000_abc123",
        "chunks_count": null,
        "error_msg": null,
        "metadata": null,
        "file_path": "pending_doc.pdf"
      }
    ]
  }
}
```

- **statuses**: 문서 상태별로 그룹화된 문서 목록
  - 각 문서는 `DocStatusResponse` 스키마를 따릅니다.

#### 사용 예시
```bash
curl -X GET "http://localhost:9621/documents" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

```python
import requests

url = "http://localhost:9621/documents"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

response = requests.get(url, headers=headers)
print(response.json())
```

**Section sources**
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L2250-L2300)

## 그래프 조회 및 시각화 API

LightRAG 서버는 지식 그래프를 조회하고 조작하기 위한 API를 제공합니다. 이러한 엔드포인트는 `graph_routes.py` 파일에 정의되어 있으며, 인증이 필요합니다.

### 그래프 레이블 목록 조회

지식 그래프에 존재하는 모든 레이블을 조회합니다.

**HTTP 메서드**: `GET`  
**URL 패턴**: `/graph/label/list`  
**인증 방법**: JWT 토큰 또는 API 키

#### 응답 스키마
```json
["base", "entity", "relation"]
```

- 문자열 배열 형태로 레이블 목록을 반환합니다.

#### 사용 예시
```bash
curl -X GET "http://localhost:9621/graph/label/list" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

```python
import requests

url = "http://localhost:9621/graph/label/list"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

response = requests.get(url, headers=headers)
print(response.json())
```

**Section sources**
- [graph_routes.py](file://lightrag/api/routers/graph_routes.py#L50-L70)

### 지식 그래프 조회

지정된 레이블을 포함하는 연결된 하위 그래프를 조회합니다.

**HTTP 메서드**: `GET`  
**URL 패턴**: `/graphs`  
**인증 방법**: JWT 토큰 또는 API 키

#### 쿼리 파라미터
- **label** (필수): 시작 노드의 레이블
- **max_depth** (선택): 하위 그래프의 최대 깊이 (기본값: `3`, 최소값: `1`)
- **max_nodes** (선택): 반환할 최대 노드 수 (기본값: `1000`, 최소값: `1`)

#### 응답 스키마
```json
{
  "nodes": [
    {"id": "entity1", "label": "Person", "properties": {"name": "Alice"}},
    {"id": "entity2", "label": "Organization", "properties": {"name": "CompanyX"}}
  ],
  "edges": [
    {"source": "entity1", "target": "entity2", "label": "WORKS_AT", "properties": {"since": "2020"}}
  ]
}
```

- **nodes**: 노드 목록
- **edges**: 엣지 목록

#### 사용 예시
```bash
curl -X GET "http://localhost:9621/graphs?label=Person&max_depth=2&max_nodes=500" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

```python
import requests

url = "http://localhost:9621/graphs"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
params = {"label": "Person", "max_depth": 2, "max_nodes": 500}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

**Section sources**
- [graph_routes.py](file://lightrag/api/routers/graph_routes.py#L72-L100)

### 엔티티 존재 여부 확인

지정된 이름의 엔티티가 지식 그래프에 존재하는지 확인합니다.

**HTTP 메서드**: `GET`  
**URL 패턴**: `/graph/entity/exists`  
**인증 방법**: JWT 토큰 또는 API 키

#### 쿼리 파라미터
- **name** (필수): 확인할 엔티티 이름

#### 응답 스키마
```json
{"exists": true}
```

- **exists**: 엔티티 존재 여부를 나타내는 부울 값

#### 사용 예시
```bash
curl -X GET "http://localhost:9621/graph/entity/exists?name=Alice" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

```python
import requests

url = "http://localhost:9621/graph/entity/exists"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
params = {"name": "Alice"}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

**Section sources**
- [graph_routes.py](file://lightrag/api/routers/graph_routes.py#L102-L120)

## 검색 쿼리 API

LightRAG 서버는 검색 쿼리를 처리하기 위한 API를 제공합니다. 이러한 엔드포인트는 `query_routes.py` 파일에 정의되어 있으며, 인증이 필요합니다.

### 쿼리 요청

사용자 쿼리를 처리하고 RAG 기능을 사용하여 응답을 생성합니다.

**HTTP 메서드**: `POST`  
**URL 패턴**: `/query`  
**인증 방법**: JWT 토큰 또는 API 키

#### 요청 스키마
```json
{
  "query": "What is machine learning?",
  "mode": "mix",
  "only_need_context": false,
  "only_need_prompt": false,
  "response_type": "Multiple Paragraphs",
  "top_k": 60,
  "chunk_top_k": 10,
  "max_entity_tokens": 1000,
  "max_relation_tokens": 8000,
  "max_total_tokens": 30000,
  "conversation_history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi, how can I help you?"}
  ],
  "history_turns": 2,
  "ids": ["doc_123"],
  "user_prompt": "Use mermaid format for diagrams",
  "enable_rerank": true
}
```

- **query** (필수): 쿼리 텍스트
- **mode** (선택): 쿼리 모드 (`local`, `global`, `hybrid`, `naive`, `mix`, `bypass`) (기본값: `mix`)
- **only_need_context** (선택): 검색된 컨텍스트만 반환할지 여부
- **only_need_prompt** (선택): 생성된 프롬프트만 반환할지 여부
- **response_type** (선택): 응답 형식 (예: `Multiple Paragraphs`, `Single Paragraph`, `Bullet Points`)
- **top_k** (선택): 검색할 상위 항목 수
- **chunk_top_k** (선택): 벡터 검색에서 처음 검색하고 리랭킹 후 유지할 텍스트 청크 수
- **max_entity_tokens** (선택): 통합 토큰 제어 시스템에서 엔티티 컨텍스트에 할당된 최대 토큰 수
- **max_relation_tokens** (선택): 통합 토큰 제어 시스템에서 관계 컨텍스트에 할당된 최대 토큰 수
- **max_total_tokens** (선택): 전체 쿼리 컨텍스트에 대한 최대 총 토큰 예산
- **conversation_history** (선택): 컨텍스트를 유지하기 위한 과거 대화 기록
- **history_turns** (선택): 응답 컨텍스트에서 고려할 완전한 대화 턴 수
- **ids** (선택): 결과를 필터링할 ID 목록
- **user_prompt** (선택): 쿼리에 사용할 사용자 제공 프롬프트
- **enable_rerank** (선택): 검색된 텍스트 청크에 리랭킹을 활성화할지 여부 (기본값: `true`)

#### 응답 스키마
```json
{
  "response": "Machine learning is a subset of artificial intelligence..."
}
```

- **response**: 생성된 응답

#### 사용 예시
```bash
curl -X POST "http://localhost:9621/query" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "mode": "mix"
  }'
```

```python
import requests

url = "http://localhost:9621/query"
headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "query": "What is machine learning?",
    "mode": "mix"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

**Section sources**
- [query_routes.py](file://lightrag/api/routers/query_routes.py#L113-L175)

### 스트리밍 쿼리 요청

검색-증강 생성(RAG) 쿼리를 수행하고 응답을 스트리밍합니다.

**HTTP 메서드**: `POST`  
**URL 패턴**: `/query/stream`  
**인증 방법**: JWT 토큰 또는 API 키

#### 요청 스키마
- `query_routes.py`의 `QueryRequest`와 동일

#### 응답 스키마
- **Content-Type**: `application/x-ndjson`
- 여러 JSON 객체를 줄바꿈으로 구분하여 스트리밍

```json
{"response": "Machine"}
{"response": " learning"}
{"response": " is a subset of artificial intelligence..."}
```

#### 사용 예시
```bash
curl -X POST "http://localhost:9621/query/stream" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "mode": "mix"
  }'
```

```python
import requests

def stream_query():
    url = "http://localhost:9621/query/stream"
    headers = {
        "Authorization": "Bearer YOUR_JWT_TOKEN",
        "Content-Type": "application/json"
    }
    data = {
        "query": "What is machine learning?",
        "mode": "mix"
    }

    response = requests.post(url, headers=headers, json=data, stream=True)
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))

stream_query()
```

**Section sources**
- [query_routes.py](file://lightrag/api/routers/query_routes.py#L173-L202)

## Ollama 호환 API

LightRAG 서버는 Ollama와 호환되는 API를 제공하여 Ollama를 지원하는 AI 챗봇 프론트엔드(예: Open WebUI)에서 쉽게 접근할 수 있도록 합니다. 이러한 엔드포인트는 `ollama_api.py` 파일에 정의되어 있으며, 인증이 필요합니다.

### Ollama 버전 정보

Ollama 버전 정보를 가져옵니다.

**HTTP 메서드**: `GET`  
**URL 패턴**: `/api/version`  
**인증 방법**: JWT 토큰 또는 API 키

#### 응답 스키마
```json
{"version": "0.9.3"}
```

#### 사용 예시
```bash
curl -X GET "http://localhost:9621/api/version" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

```python
import requests

url = "http://localhost:9621/api/version"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

response = requests.get(url, headers=headers)
print(response.json())
```

**Section sources**
- [ollama_api.py](file://lightrag/api/routers/ollama_api.py#L212-L220)

### 사용 가능한 모델 목록

사용 가능한 모델을 목록으로 반환합니다.

**HTTP 메서드**: `GET`  
**URL 패턴**: `/api/tags`  
**인증 방법**: JWT 토큰 또는 API 키

#### 응답 스키마
```json
{
  "models": [
    {
      "name": "lightrag:latest",
      "model": "lightrag:latest",
      "modified_at": "2024-01-15T00:00:00Z",
      "size": 7365960935,
      "digest": "sha256:lightrag",
      "details": {
        "parent_model": "",
        "format": "gguf",
        "family": "lightrag",
        "families": ["lightrag"],
        "parameter_size": "13B",
        "quantization_level": "Q4_0"
      }
    }
  ]
}
```

#### 사용 예시
```bash
curl -X GET "http://localhost:9621/api/tags" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

```python
import requests

url = "http://localhost:9621/api/tags"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

response = requests.get(url, headers=headers)
print(response.json())
```

**Section sources**
- [ollama_api.py](file://lightrag/api/routers/ollama_api.py#L222-L240)

### 채팅 완성 요청

Ollama 모델처럼 채팅 완성 요청을 처리합니다.

**HTTP 메서드**: `POST`  
**URL 패턴**: `/api/chat`  
**인증 방법**: JWT 토큰 또는 API 키

#### 요청 스키마
```json
{
  "model": "lightrag:latest",
  "messages": [
    {"role": "user", "content": "What is machine learning?"}
  ],
  "stream": false,
  "options": {},
  "system": "You are a helpful assistant."
}
```

- **model**: 사용할 모델 이름
- **messages**: 메시지 목록
- **stream**: 스트리밍 응답 여부
- **options**: 추가 옵션
- **system**: 시스템 프롬프트

#### 응답 스키마
```json
{
  "model": "lightrag:latest",
  "created_at": "2024-01-15T00:00:00Z",
  "message": {
    "role": "assistant",
    "content": "Machine learning is a subset of artificial intelligence..."
  },
  "done": true,
  "done_reason": "stop",
  "total_duration": 123456789,
  "load_duration": 0,
  "prompt_eval_count": 10,
  "prompt_eval_duration": 123456,
  "eval_count": 50,
  "eval_duration": 12345678
}
```

#### Open WebUI 통합 방법
LightRAG 서버를 시작한 후, Open WebUI 관리 패널에서 Ollama 유형의 연결을 추가합니다. 그러면 `lightrag:latest`라는 모델이 Open WebUI의 모델 관리 인터페이스에 나타납니다. 사용자는 채팅 인터페이스를 통해 LightRAG에 쿼리를 보낼 수 있습니다. 이 사용 사례의 경우, LightRAG를 서비스로 설치하는 것이 가장 좋습니다.

Open WebUI는 세션 제목 및 세션 키워드 생성 작업에 LLM을 사용합니다. 따라서 Ollama 챗 완성 API는 OpenWebUI 세션 관련 요청을 감지하고 이를 기본 LLM에 직접 전달합니다.

#### 사용 예시
```bash
curl -X POST "http://localhost:9621/api/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lightrag:latest",
    "messages": [
      {"role": "user", "content": "What is machine learning?"}
    ],
    "stream": false
  }'
```

```python
import requests

url = "http://localhost:9621/api/chat"
headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "model": "lightrag:latest",
    "messages": [
        {"role": "user", "content": "What is machine learning?"}
    ],
    "stream": False
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

**Section sources**
- [ollama_api.py](file://lightrag/api/routers/ollama_api.py#L459-L550)

## 인증 및 보안

LightRAG 서버는 JWT 기반 인증과 API 키 인증을 지원합니다. 보안 고려사항은 `auth.py` 및 `config.py` 파일에 정의되어 있습니다.

### 인증 방법

- **JWT 토큰**: `auth.py`에서 `AuthHandler` 클래스를 사용하여 생성 및 검증합니다.
- **API 키**: 환경 변수 `LIGHTRAG_API_KEY`를 통해 설정할 수 있습니다.

### 설정

- **API 키**: `config.py`의 `global_args.key`를 통해 설정합니다.
- **JWT 비밀 키**: `config.py`의 `global_args.token_secret`를 통해 설정합니다.
- **토큰 만료 시간**: `config.py`의 `global_args.token_expire_hours` 및 `global_args.guest_token_expire_hours`를 통해 설정합니다.
- **JWT 알고리즘**: `config.py`의 `global_args.jwt_algorithm`를 통해 설정합니다.

### 보안 고려사항

- 인증이 구성되지 않은 경우, 게스트 토큰이 생성되어 게스트 액세스가 가능합니다.
- 인증이 구성된 경우, 유효한 JWT 토큰 또는 API 키가 필요합니다.
- CORS 원본은 `config.py`의 `global_args.cors_origins`를 통해 구성할 수 있습니다.
- 인증이 비활성화된 경우, `/auth-status` 엔드포인트를 통해 게스트 토큰을 가져올 수 있습니다.

**Section sources**
- [auth.py](file://lightrag/api/auth.py#L0-L108)
- [config.py](file://lightrag/api/config.py#L0-L424)

## 오류 응답 코드

LightRAG API는 다양한 오류 상황에 대해 표준 HTTP 상태 코드를 반환합니다.

### 일반적인 오류 코드

- **4