
# PostgreSQL 기반 KV 저장소 최적화

<cite>
**이 문서에서 참조한 파일**
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py)
- [docker-compose.yml](file://docker-compose.yml)
</cite>

## 목차
1. [소개](#소개)
2. [테이블 스키마 및 인덱스 설계](#테이블-스키마-및-인덱스-설계)
3. [비동기 쿼리 및 트랜잭션 관리](#비동기-쿼리-및-트랜잭션-관리)
4. [커넥션 풀링 및 리소스 제한](#커넥션-풀링-및-리소스-제한)
5. [고빈도 쓰기 작업 최적화](#고빈도-쓰기-작업-최적화)
6. [클러스터링 및 백업 전략](#클러스터링-및-백업-전략)

## 소개
이 문서는 LightRAG 프로젝트의 `postgres_impl.py` 구현을 기반으로 PostgreSQL 기반 KV 저장소의 성능 최적화 전략을 심층적으로 설명합니다. 코드 분석을 통해 테이블 스키마 설계, 인덱스 활용, 비동기 처리, 커넥션 풀링, 고성능 쓰기 작업 최적화, 클러스터링 및 백업 전략까지 포괄적인 가이드를 제공합니다.

**Section sources**
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py#L51-L1289)

## 테이블 스키마 및 인덱스 설계

### 테이블 스키마 설계
PostgreSQL 기반 KV 저장소는 다양한 목적에 맞는 전문화된 테이블 구조를 사용합니다. 각 테이블은 `workspace`와 `id`를 복합 기본 키로 사용하여 데이터 격리를 보장합니다.

```mermaid
erDiagram
LIGHTRAG_DOC_FULL {
varchar id PK
varchar workspace PK
varchar doc_name
text content
jsonb meta
timestamp create_time
timestamp update_time
}
LIGHTRAG_DOC_CHUNKS {
varchar id PK
varchar workspace PK
varchar full_doc_id
integer chunk_order_index
integer tokens
text content
text file_path
jsonb llm_cache_list
timestamp create_time
timestamp update_time
}
LIGHTRAG_VDB_CHUNKS {
varchar id PK
varchar workspace PK
varchar full_doc_id
integer chunk_order_index
integer tokens
text content
vector content_vector
text file_path
timestamp create_time
timestamp update_time
}
LIGHTRAG_VDB_ENTITY {
varchar id PK
varchar workspace PK
varchar entity_name
text content
vector content_vector
varchar[] chunk_ids
text file_path
timestamp create_time
timestamp update_time
}
LIGHTRAG_VDB_RELATION {
varchar id PK
varchar workspace PK
varchar source_id
varchar target_id
text content
vector content_vector
varchar[] chunk_ids
text file_path
timestamp create_time
timestamp update_time
}
LIGHTRAG_LLM_CACHE {
varchar workspace PK
varchar id PK
text original_prompt
text return_value
varchar chunk_id
varchar cache_type
jsonb queryparam
timestamp create_time
timestamp update_time
}
LIGHTRAG_DOC_STATUS {
varchar workspace PK
varchar id PK
varchar content_summary
int content_length
int chunks_count
varchar status
text file_path
jsonb chunks_list
varchar track_id
jsonb metadata
text error_msg
timestamp created_at
timestamp updated_at
}
LIGHTRAG_FULL_ENTITIES {
varchar id PK
varchar workspace PK
jsonb entity_names
integer count
timestamp create_time
timestamp update_time
}
LIGHTRAG_FULL_RELATIONS {
varchar id PK
varchar workspace PK
jsonb relation_pairs
integer count
timestamp create_time
timestamp update_time
}
LIGHTRAG_DOC_FULL ||--o{ LIGHTRAG_DOC_CHUNKS : contains
LIGHTRAG_DOC_CHUNKS ||--o{ LIGHTRAG_VDB_CHUNKS : "has vector"
LIGHTRAG_VDB_ENTITY ||--o{ LIGHTRAG_FULL_ENTITIES : "aggregates"
LIGHTRAG_VDB_RELATION ||--o{ LIGHTRAG_FULL_RELATIONS : "aggregates"
LIGHTRAG_DOC_STATUS ||--o{ LIGHTRAG_DOC_CHUNKS : tracks
LIGHTRAG_LLM_CACHE ||--o{ LIGHTRAG_DOC_CHUNKS : caches
```

**Diagram sources**
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py#L4320-L4446)

### B-Tree 및 GIN 인덱스 활용
시스템은 다양한 쿼리 패턴을 최적화하기 위해 포괄적인 인덱스 전략을 구현합니다.

```mermaid
graph TD
A[기본 인덱스] --> B["id 컬럼 인덱스"]
A --> C["(workspace, id) 복합 인덱스"]
D[문서 상태 최적화 인덱스] --> E["workspace + status + updated_at"]
D --> F["workspace + status + created_at"]
D --> G["workspace + updated_at"]
D --> H["workspace + created_at"]
D --> I["workspace + id"]
D --> J["workspace + file_path"]
K[벡터 검색 인덱스] --> L["HNSW 인덱스"]
K --> M["IVFFLAT 인덱스"]
N[그래프 인덱스] --> O["vertex_idx_node_id"]
N --> P["edge_sid_idx"]
N --> Q["edge_eid_idx"]
N --> R["entity_idx_node_id"]
N --> S["entity_node_id_gin_idx"]
B --> T[단일 레코드 조회]
C --> T
E --> U[상태별 문서 페이징]
F --> U
G --> V[최근 업데이트 문서]
H --> V
I --> W[워크스페이스 내 정렬]
J --> X[파일 경로 기반 조회]
L --> Y[벡터 유사도 검색]
M --> Y
O --> Z[노드 ID 기반 조회]
P --> AA[소스 기반 관계 조회]
Q --> AB[대상 기반 관계 조회]
R --> AC[엔티티 ID 기반 조회]
S --> AD[속성 기반 GIN 검색]
```

**Diagram sources**
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py#L51-L1289)

**Section sources**
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py#L51-L1289)

## 비동기 쿼리 및 트랜잭션 관리

### 비동기 쿼리 실행
시스템은 `asyncpg` 라이브러리를 사용하여 완전한 비동기 쿼리 실행을 구현합니다. 이 접근 방식은 I/O 대기 시간을 최소화하고 동시 처리 능력을 극대화합니다.

```mermaid
sequenceDiagram
participant 애플리케이션 as 애플리케이션
participant 클라이언트매니저 as ClientManager
participant 풀 as 커넥션 풀
participant DB as PostgreSQL DB
애플리케이션->>클라이언트매니저 : get_client() 호출
클라이언트매니저->>클라이언트매니저 : _lock 획득
alt 첫 번째 호출
클라이언트매니저->>DB : initdb() 실행
DB->>풀 : 커넥션 풀 생성
DB->>클라이언트매니저 : DB 인스턴스 반환
else 재사용
클라이언트매니저->>클라이언트매니저 : 기존 DB 인스턴스 반환
end
클라이언트매니저->>애플리케이션 : DB 클라이언트 반환
애플리케이션->>DB : 비동기 쿼리 실행
DB->>풀 : 커넥션 획득
풀->>DB : 커넥션 제공
DB->>DB : 쿼리 실행 및 결과 처리
DB->>풀 : 커넥션 반환
DB->>애플리케이션 : 결과 반환
애플리케이션->>클라이언트매니저 : release_client() 호출
클라이언트매니저->>클라이언트매니저 : 참조 카운트 감소
alt 참조 카운트 0
클라이언트매니저->>DB : 커넥션 풀 종료
end
```

**Diagram sources**
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py#L51-L1289)

### 트랜잭션 관리 및 오류 재시도
시스템은 견고한 트랜잭션 관리와 오류 재시도 메커니즘을 구현하여 데이터 무결성과 신뢰성을 보장합니다.

```mermaid
flowchart TD
    A[업서트 작업 시작] --> B{작업 유형 확인}
    B -->|노드 업서트| C[upsert_node 메서드 호출]
    B -->|관계 업서트| D[upsert_edge 메서드 호출]
    B -->|일반 데이터| E[upsert 메서드 호출]
    
    C --> F[노드 데이터 유효성 검사]
    F --> G[노드 ID 정규화]
    G --> H[속성 포맷팅]
    H --> I[MERGE Cypher 쿼리 생성]
    I --> J[쿼리 실행]
    J --> K{실패?}
    K -->|예| L[재시도 정책 적용]
    L --> M[지수 백오프: 4s, 8s, 16s]
    M --> N[최대 3회 재시도]
    N --> J
    K -->|아니오| O[성공 로깅]
    O --> P[작업 완료]
    
    D --> Q[소스/대상 ID 정규화]
    Q --> R[관계 속성 포맷팅]
    R --> S[MERGE Cypher 쿼리 생성]
    S --> T[쿼리 실행]
    T --> U{실패?}
    U -->|예| V[재시도 정책 적용]
    V --> W[지수 백오프: 4s, 8s, 16s]
    W --> X[최대 3회 재시도]
    X --> T
    U -->|아니오| Y[성공 로깅]
    Y --> P
    
    E --> Z[데이터 유효성 검사]
    Z --> AA[작업 유형별 처리]
    AA --> AB[문서 청크 업서트]
    AA --> AC[LLM 캐시 업서트]
    AA --> AD[벡터 데이터 업서트]
    AB --> AE[업서트 SQL 실행]
    AE --> AF{실패?}
    AF -->|예| AG[예외 처리 및 로깅]
    AF -->|