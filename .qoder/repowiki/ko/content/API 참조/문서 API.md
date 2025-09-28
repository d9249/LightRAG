# 문서 API

<cite>
**이 문서에서 참조한 파일**
- [document_routes.py](file://lightrag/api/routers/document_routes.py)
- [base.py](file://lightrag/base.py)
- [config.py](file://lightrag/api/config.py)
- [lightrag.py](file://lightrag/lightrag.py)
</cite>

## 목차
1. [소개](#소개)
2. [문서 업로드 엔드포인트](#문서-업로드-엔드포인트)
3. [문서 삭제 엔드포인트](#문서-삭제-엔드포인트)
4. [문서 목록 조회 엔드포인트](#문서-목록-조회-엔드포인트)
5. [성능 최적화 및 초기화](#성능-최적화-및-초기화)
6. [API 호출 예제](#api-호출-예제)

## 소개
이 문서는 LightRAG 시스템의 문서 관리 기능을 위한 API 엔드포인트를 상세히 설명합니다. 문서 업로드, 삭제, 목록 조회 기능을 제공하며, 다양한 파일 형식을 지원하고 배치 처리를 통해 성능을 최적화할 수 있습니다.

**Section sources**
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L0-L50)

## 문서 업로드 엔드포인트

### HTTP 메서드 및 경로
- **메서드**: POST
- **경로**: `/documents/upload`

### 요청 본문 스키마
- **Content-Type**: `multipart/form-data`
- **필드**: `file` (업로드할 파일)

### 지원 파일 형식
다음 파일 형식을 지원합니다:
- `.txt`, `.md`, `.pdf`, `.docx`, `.pptx`, `.xlsx`
- `.rtf`, `.odt`, `.tex`, `.epub`, `.html`, `.htm`, `.csv`
- `.json`, `.xml`, `.yaml`, `.yml`, `.log`, `.conf`, `.ini`
- `.properties`, `.sql`, `.bat`, `.sh`, `.c`, `.cpp`, `.py`
- `.java`, `.js`, `.ts`, `.swift`, `.go`, `.rb`, `.php`, `.css`, `.scss`, `.less`

### 응답 형식
```json
{
  "status": "success",
  "message": "File 'document.pdf' uploaded successfully. Processing will continue in background.",
  "track_id": "upload_20250729_170612_abc123"
}
```

### 오류 코드
- **HTTP 400**: 잘못된 요청 (빈 파일명, 지원하지 않는 확장자 등)
- **HTTP 500**: 서버 내부 오류 (파일 저장 실패 등)

**Section sources**
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L209-L231)
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L869-L904)
- [lightrag_webui/src/lib/constants.ts](file://lightrag_webui/src/lib/constants.ts#L0-L42)

## 문서 삭제 엔드포인트

### HTTP 메서드 및 경로
- **메서드**: DELETE
- **경로**: `/documents/delete_document`

### 요청 본문 스키마
```json
{
  "doc_ids": ["doc_123", "doc_456"],
  "delete_file": true
}
```

- **doc_ids**: 삭제할 문서 ID 목록 (필수)
- **delete_file**: 업로드 디렉터리의 해당 파일도 삭제할지 여부 (기본값: false)

### 응답 형식
```json
{
  "status": "deletion_started",
  "message": "Deletion process started for 2 documents",
  "doc_id": "doc_123"
}
```

### 오류 코드
- **HTTP 400**: 잘못된 요청 (빈 doc_ids 목록, 중복된 ID 등)
- **HTTP 404**: 문서를 찾을 수 없음

**Section sources**
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L305-L328)
- [lightrag_webui/src/api/lightrag.ts](file://lightrag_webui/src/api/lightrag.ts#L574-L576)

## 문서 목록 조회 엔드포인트

### HTTP 메서드 및 경로
- **메서드**: POST
- **경로**: `/documents/list`

### 요청 본문 스키마
```json
{
  "status_filter": "PROCESSED",
  "page": 1,
  "page_size": 50,
  "sort_field": "updated_at",
  "sort_direction": "desc"
}
```

- **status_filter**: 문서 상태로 필터링 (PENDING, PROCESSING, PROCESSED, FAILED)
- **page**: 페이지 번호 (기본값: 1)
- **page_size**: 페이지당 문서 수 (10-200, 기본값: 50)
- **sort_field**: 정렬 기준 필드 (created_at, updated_at, id, file_path)
- **sort_direction**: 정렬 방향 (asc, desc)

### 응답 형식
```json
{
  "documents": [
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
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_count": 150,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  },
  "status_counts": {
    "PENDING": 10,
    "PROCESSING": 5,
    "PROCESSED": 130,
    "FAILED": 5
  }
}
```

### 오류 코드
- **HTTP 400**: 잘못된 요청 (page_size 범위 초과 등)

**Section sources**
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L555-L605)
- [document_routes.py](file://lightrag/api/routers/document_routes.py#L400-L450)

## 성능 최적화 및 초기화

### 대량 문서 삽입을 위한 배치 처리
대량의 문서를 삽입할 때는 다음과 같은 팁을 따르세요:
- `MAX_PARALLEL_INSERT` 환경 변수를 설정하여 병렬 삽입 수를 조정
- `MAX_ASYNC` 환경 변수를 통해 최대 비동기 작업 수를 설정
- 큰 파일은 작은 청크로 나누어 업로드

### 초기화 요구사항
문서 처리를 시작하기 전에 스토리지를 초기화해야 합니다:
```python
from lightrag import LightRAG

rag = LightRAG(working_dir="./rag_storage")
await rag.initialize_storages()
```

`initialize_storages()` 메서드는 모든 스토리지 컴포넌트를 초기화하며, 이는 문서 처리를 시작하기 전에 반드시 호출되어야 합니다.

**Section sources**
- [lightrag.py](file://lightrag/lightrag.py#L562-L582)
- [config.py](file://lightrag/api/config.py#L0-L424)

## API 호출 예제

### Python requests 라이브러리 사용
```python
import requests

# 문서 업로드
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:9621/documents/upload",
        files={"file": f}
    )
print(response.json())

# 문서 삭제
response = requests.delete(
    "http://localhost:9621/documents/delete_document",
    json={"doc_ids": ["doc_123"], "delete_file": True}
)
print(response.json())

# 문서 목록 조회
response = requests.post(
    "http://localhost:9621/documents/list",
    json={"status_filter": "PROCESSED", "page": 1, "page_size": 10}
)
print(response.json())
```

### curl 명령어 사용
```bash
# 문서 업로드
curl -X POST http://localhost:9621/documents/upload \
  -F "file=@document.pdf"

# 문서 삭제
curl -X DELETE http://localhost:9621/documents/delete_document \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": ["doc_123"], "delete_file": true}'

# 문서 목록 조회
curl -X POST http://localhost:9621/documents/list \
  -H "Content-Type: application/json" \
  -d '{"status_filter": "PROCESSED", "page": 1, "page_size": 10}'
```

**Section sources**
- [lightrag_webui/src/api/lightrag.ts](file://lightrag_webui/src/api/lightrag.ts#L533-L574)