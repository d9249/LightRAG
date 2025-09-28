# LightRAG Documents API

LightRAG 기반의 독립적인 3-tier 아키텍처 문서 처리 및 쿼리 시스템입니다.

## 🏗️ 아키텍처

### 3-Tier 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Tier                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐│
│  │  Document API   │ │   Query API     │ │   Graph API     ││
│  │   Routes        │ │    Routes       │ │    Routes       ││
│  └─────────────────┘ └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Tier                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐│
│  │  Document       │ │   Query         │ │   Graph         ││
│  │  Service        │ │   Service       │ │   Service       ││
│  └─────────────────┘ └─────────────────┘ └─────────────────┘│
│                  ┌─────────────────┐                        │
│                  │  LightRAG       │                        │
│                  │  Wrapper        │                        │
│                  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                      Data Tier                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐│
│  │  File System    │ │  NanoVectorDB   │ │     Neo4j       ││
│  │  (Documents)    │ │  (Embeddings)   │ │   (Graph)       ││
│  └─────────────────┘ └─────────────────┘ └─────────────────┘│
│                  ┌─────────────────┐                        │
│                  │     Ollama      │                        │
│                  │     (LLM)       │                        │
│                  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 빠른 시작

### 1. Docker Compose로 실행

```bash
# 저장소 클론 및 이동
git clone <repository-url>
cd LightRAG/documents

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 2. 수동 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 애플리케이션 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 9621
```

## 📋 필수 요구사항

### 시스템 요구사항
- Python 3.11+
- Docker & Docker Compose
- 최소 8GB RAM
- 10GB 여유 디스크 공간

### 외부 서비스
- **Neo4j**: 그래프 데이터베이스
- **Ollama**: LLM 및 임베딩 서비스

## 🔧 구성

### 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `PORT` | API 서버 포트 | 9621 |
| `OLLAMA_URL` | Ollama 서비스 URL | http://ollama:11434 |
| `NEO4J_URL` | Neo4j 서비스 URL | bolt://neo4j:7687 |
| `NEO4J_USER` | Neo4j 사용자명 | neo4j |
| `NEO4J_PASSWORD` | Neo4j 비밀번호 | password |
| `LLM_MODEL` | 사용할 LLM 모델 | llama3.1 |
| `EMBEDDING_MODEL` | 임베딩 모델 | nomic-embed-text |

### 지원 파일 형식
- PDF (.pdf)
- Microsoft Word (.docx)
- PowerPoint (.pptx)
- Excel (.xlsx)
- 텍스트 (.txt)
- 마크다운 (.md)
- JSON (.json)
- XML (.xml)
- CSV (.csv)

## 📡 API 엔드포인트

### 문서 관리 (`/documents`)

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| POST | `/documents/upload` | 파일 업로드 |
| POST | `/documents/text` | 텍스트 직접 삽입 |
| POST | `/documents/texts` | 배치 텍스트 삽입 |
| POST | `/documents/scan` | 디렉터리 스캔 |
| GET | `/documents` | 문서 목록 조회 |
| GET | `/documents/status_counts` | 상태별 통계 |
| DELETE | `/documents/delete_document` | 문서 삭제 |
| DELETE | `/documents/clear` | 전체 삭제 |

### 쿼리 (`/query`)

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| POST | `/query` | 기본 RAG 쿼리 |
| POST | `/query/stream` | 스트리밍 쿼리 |
| POST | `/query/data` | 구조화된 데이터 검색 |
| POST | `/query/local` | 로컬 모드 쿼리 |
| POST | `/query/global` | 글로벌 모드 쿼리 |
| GET | `/query/stats` | 쿼리 통계 |

### 그래프 (`/graph`)

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| GET | `/graph/label/list` | 모든 레이블 |
| GET | `/graph/label/popular` | 인기 레이블 |
| POST | `/graph/label/search` | 레이블 검색 |
| POST | `/graph` | 그래프 조회 |
| POST | `/graph/entity/edit` | 엔티티 편집 |
| POST | `/graph/relation/edit` | 관계 편집 |

## 💡 사용 예제

### 1. 문서 업로드

```bash
curl -X POST "http://localhost:9621/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### 2. 텍스트 삽입

```bash
curl -X POST "http://localhost:9621/documents/text" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "이것은 테스트 문서입니다.",
    "source_id": "test_doc_1",
    "metadata": {"author": "user1"}
  }'
```

### 3. 쿼리 실행

```bash
curl -X POST "http://localhost:9621/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "문서의 주요 내용이 무엇인가요?",
    "mode": "mix"
  }'
```

### 4. 그래프 데이터 조회

```bash
curl -X POST "http://localhost:9621/graph" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_names": ["엔티티1", "엔티티2"],
    "depth": 2,
    "max_nodes": 100
  }'
```

## 🧪 테스트

### API 테스트 실행

```bash
# 기본 테스트
python test_api.py

# 특정 URL 테스트
python test_api.py --url http://localhost:9621
```

### 수동 테스트

```bash
# 헬스 체크
curl http://localhost:9621/health

# API 문서 확인
open http://localhost:9621/docs
```

## 📊 모니터링

### 로그 확인

```bash
# Docker Compose 로그
docker-compose logs -f lightrag-api

# 개별 서비스 로그
docker-compose logs -f neo4j
docker-compose logs -f ollama
```

### 상태 확인

```bash
# 전체 시스템 상태
curl http://localhost:9621/health

# 문서 처리 파이프라인 상태
curl http://localhost:9621/documents/pipeline_status

# 그래프 통계
curl http://localhost:9621/graph/stats
```

## 🔍 문제 해결

### 일반적인 문제

1. **Ollama 연결 실패**
   ```bash
   # Ollama 서비스 상태 확인
   docker-compose logs ollama
   
   # 모델 다운로드 확인
   docker-compose exec ollama ollama list
   ```

2. **Neo4j 연결 실패**
   ```bash
   # Neo4j 로그 확인
   docker-compose logs neo4j
   
   # 브라우저에서 확인: http://localhost:7474
   ```

3. **메모리 부족**
   ```bash
   # Docker 메모리 설정 확인
   docker stats
   
   # 불필요한 컨테이너 정리
   docker system prune
   ```

### 디버그 모드

```bash
# 디버그 모드로 실행
DEBUG=True docker-compose up

# 자세한 로그 출력
LOG_LEVEL=DEBUG docker-compose up
```

## 🛠️ 개발

### 개발 환경 설정

```bash
# 개발 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Pre-commit 훅 설치
pre-commit install

# 코드 포맷팅
black app/ core/
isort app/ core/

# 타입 체크
mypy app/ core/
```

### 코드 구조

```
documents/
├── app/                    # Presentation Tier
│   ├── main.py            # FastAPI 애플리케이션
│   ├── config.py          # 설정
│   ├── models/            # Pydantic 모델
│   └── routers/           # API 라우터
├── core/                  # Business Logic Tier
│   ├── lightrag_wrapper.py # LightRAG 래퍼
│   ├── services/          # 비즈니스 서비스
│   └── utils/             # 유틸리티
├── data/                  # Data Tier
│   ├── inputs/            # 업로드 파일
│   ├── rag_storage/       # LightRAG 데이터
│   └── graph_storage/     # Neo4j 데이터
├── docker-compose.yml     # 서비스 정의
├── Dockerfile            # 애플리케이션 이미지
└── requirements.txt      # Python 의존성
```

## 📚 추가 자료

- [LightRAG 공식 문서](https://github.com/HKUDS/LightRAG)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Neo4j 문서](https://neo4j.com/docs/)
- [Ollama 문서](https://ollama.ai/docs/)

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원

문제가 발생하거나 질문이 있으시면:

1. [Issues](../../issues)에서 기존 문제를 검색
2. 새로운 이슈 생성
3. 상세한 오류 로그와 재현 단계 포함

---

**Made with ❤️ using LightRAG and FastAPI**