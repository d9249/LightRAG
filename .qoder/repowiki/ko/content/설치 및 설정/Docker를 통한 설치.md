
# Docker를 통한 설치

<cite>
**이 문서에서 참조한 파일**  
- [Dockerfile](file://Dockerfile)
- [docker-compose.yml](file://docker-compose.yml)
- [lightrag/api/lightrag_server.py](file://lightrag/api/lightrag_server.py)
- [lightrag/api/routers/query_routes.py](file://lightrag/api/routers/query_routes.py)
- [lightrag/api/routers/document_routes.py](file://lightrag/api/routers/document_routes.py)
- [env.example](file://env.example)
- [README.md](file://README.md)
</cite>

## 목차
1. [소개](#소개)
2. [Dockerfile 분석](#dockerfile-분석)
3. [docker-compose.yml 구성](#docker-composeyml-구성)
4. [컨테이너 실행 및 상태 점검](#컨테이너-실행-및-상태-점검)
5. 흔한 오류 및 해결 방안
6. 결론

## 소개
LightRAG는 검색 증강 생성(Retrieval-Augmented Generation, RAG) 기능을 제공하는 고성능 시스템으로, Docker를 사용하여 쉽게 설치하고 배포할 수 있습니다. 본 문서는 Docker를 활용한 LightRAG 설치 방법을 상세히 설명하며, Dockerfile의 다단계 빌드 구조, docker-compose.yml 기반의 멀티 컨테이너 구성, 포트 매핑, 볼륨 마운트, 환경 변수 주입 등 핵심 설정 요소를 분석합니다. 또한 컨테이너 실행 후 로그 확인 및 API 엔드포인트를 통한 상태 점검 방법과 흔한 오류에 대한 해결 방안을 제공합니다.

## Dockerfile 분석
LightRAG의 Dockerfile은 다단계 빌드(Multi-stage Build) 구조를 사용하여 최종 이미지의 크기를 최소화하고 보안을 강화합니다. 이 구조는 빌드 단계(builder stage)와 최종 실행 단계(final stage)로 나뉩니다.

### 빌더 단계 (Builder Stage)
```dockerfile
FROM python:3.12-slim AS builder
```
- **기반 이미지**: `python:3.12-slim`을 사용하여 가볍고 최소한의 Python 환경을 제공합니다.
- **작업 디렉터리 설정**: `/app` 디렉터리를 작업 디렉터리로 지정합니다.
- **pip 업그레이드**: `pip`, `setuptools`, `wheel`을 최신 버전으로 업그레이드하여 패키지 설치의 안정성을 보장합니다.
- **Rust 컴파일러 설치**: `curl`, `build-essential`, `pkg-config` 등의 빌드 도구를 설치한 후, 공식 스크립트를 통해 Rust 컴파일러를 설치합니다. 이는 `tiktoken`과 같은 Rust 기반 Python 패키지를 빌드하기 위한 필수 조건입니다.
- **종속성 설치**: `pyproject.toml`, `setup.py`, `lightrag/` 디렉터리를 복사한 후, `pip install --user --no-cache-dir --use-pep517 .[api]` 명령어를 사용하여 API 기능을 포함한 모든 종속성을 설치합니다. `--user` 옵션은 패키지를 사용자 디렉터리에 설치하여 권한 문제를 방지하고, `--no-cache-dir`는 캐시를 생성하지 않아 이미지 크기를 줄입니다. `--use-pep517`은 최신 빌드 시스템을 사용하도록 지정합니다.
- **추가 종속성 설치**: 기본 저장소, LLM, 문서 로더를 위한 추가 종속성(`nano-vectordb`, `networkx`, `openai`, `ollama`, `tiktoken`, `pypdf2`, `python-docx` 등)을 설치합니다.

### 최종 단계 (Final Stage)
```dockerfile
FROM python:3.12-slim
```
- **기반 이미지**: 동일한 `python:3.12-slim` 이미지를 사용하지만, 빌드 도구가 포함되지 않아 훨씬 더 가볍습니다.
- **빌더 단계의 결과 복사**: `COPY --from=builder /root/.local /root/.local` 명령어를 사용하여 빌더 단계에서 설치된 모든 Python 패키지를 최종 이미지로 복사합니다. 이 방식은 최종 이미지에 불필요한 빌드 도구나 소스 코드를 포함하지 않아 보안과 효율성을 극대화합니다.
- **필수 파일 복사**: `lightrag/` 디렉터리와 `setup.py`를 다시 복사합니다.
- **API 종속성 재설치**: `pip install --use-pep517 ".[api]"`를 실행하여 최종 이미지의 Python 환경에 API 종속성을 확보합니다.
- **경로 설정**: `ENV PATH=/root/.local/bin:$PATH`를 통해 사용자 설치 디렉터리의 실행 파일을 시스템 경로에 추가합니다.
- **디렉터리 생성**: `/app/data/rag_storage` 및 `/app/data/inputs` 디렉터리를 생성하여 문서 저장소와 입력 파일을 위한 공간을 마련합니다.
- **환경 변수 설정**: `WORKING_DIR`과 `INPUT_DIR` 환경 변수를 설정하여 애플리케이션의 작업 디렉터리를 지정합니다.
- **포트 노출**: `EXPOSE 9621`을 통해 기본 API 포트를 외부에 노출합니다.
- **엔트리포인트 설정**: `ENTRYPOINT ["python", "-m", "lightrag.api.lightrag_server"]`을 통해 컨테이너 실행 시 LightRAG 서버를 자동으로 시작합니다.

**Section sources**
- [Dockerfile](file://Dockerfile#L1-L63)

## docker-compose.yml 구성
`docker-compose.yml` 파일은 `ollama`와 `lightrag` 두 개의 서비스로 구성된 멀티 컨테이너 환경을 정의합니다. 이는 LightRAG가 Ollama와 통합되어 로컬 LLM을 활용할 수 있도록 합니다.

### ollama 서비스
```yaml
services:
  ollama:
    container_name: ollama
    image: ollama/ollama:latest
    ports:
      - "9622:11434"
    volumes:
      - ./data/ollama:/root/.ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 20s
```
- **이미지**: 최신 버전의 공식 `ollama/ollama` 이미지를 사용합니다.
- **포트 매핑**: 호스트의 `9622` 포트를 컨테이너의 `11434` 포트(기본 Ollama API 포트)에 매핑합니다. 이를 통해 호스트에서 `http://localhost:9622`을 통해 Ollama API에 접근할 수 있습니다.
- **볼륨 마운트**: 로컬의 `./data/ollama` 디렉터리를 컨테이너 내 `~/.ollama` 디렉터리에 마운트하여 모델과 설정을 영구적으로 저장합니다.
- **재시작 정책**: `unless-stopped`로 설정하여 컨테이너가 비정상적으로 종료될 경우 자동으로 재시작되며, 수동으로 중지된 경우를 제외하고는 항상 실행됩니다.
- **헬스체크**: `ollama list` 명령어를 주기적으로 실행하여 서비스의 건강 상태를 모니터링합니다. 이는 `lightrag` 서비스가 `ollama` 서비스가 준비될 때까지 기다리도록 합니다.

### lightrag 서비스
```yaml
  lightrag:
    container_name: lightrag
    image: ghcr.io/hkuds/lightrag:latest
    build:
      context: .
      dockerfile: Dockerfile
      tags:
        - ghcr.io/hkuds/lightrag:latest
    ports:
      - "${PORT:-9621}:9621"
    volumes:
      - ./data/rag_storage:/app/data/rag_storage
      - ./data/inputs:/app/data/inputs
      - ./data/tiktoken:/app/data/tiktoken
      - ./config.ini:/app/config.ini
      - ./.env:/app/.env
    env_file:
      - .env
    environment:
      - TIKTOKEN_CACHE_DIR=/app/data/tiktoken
    restart: unless-stopped
    depends_on:
      - ollama
    extra_hosts:
      - "host.docker.internal:host-gateway"
```
- **이미지 및 빌드**: 기본적으로 `ghcr.io/hkuds/lightrag:latest` 이미지를 사용하되, 로컬에서 `Dockerfile`을 기반으로 빌드하여 `ghcr.io/hkuds/lightrag:latest` 태그를 붙입니다. 이는 최신 변경 사항을 반영할 수 있도록 합니다.
- **포트 매핑**: `${PORT:-9621}` 환경 변수를 사용하여 유연한 포트 설정을 지원합니다. 환경 변수가 설정되지 않으면 기본값인 `9621` 포트를 사용합니다.
- **볼륨 마운트**:
  - `./data/rag_storage`: RAG 관련 데이터(지식 그래프, 벡터 저장소 등)를 저장합니다.
  - `./data/inputs`: 사용자가 업로드한 입력 문서를 저장합니다.
  - `./data/tiktoken`: `tiktoken` 라이브러리의 캐시 파일을 저장하여 오프라인 환경에서도 토크나이저를 사용할 수 있게 합니다.
  - `./config.ini`: 사용자 정의 설정 파일을 마운트합니다.
  - `./.env`: 환경 변수 설정 파일을 마운트합니다.
- **환경 변수 주입**:
  - `env_file`: `.env` 파일의 모든 환경 변수를 컨테이너 내부로 로드합니다. 이 파일은 LLM 설정, API 키, 저장소 구성 등 중요한 설정을 포함합니다.
  - `environment`: `TIKTOKEN_CACHE_DIR` 환경 변수를 직접 설정하여 `tiktoken` 캐시 디렉터리의 위치를 명시적으로 지정합니다.
- **의존성**: `depends_on: ollama`를 통해 `lightrag` 서비스가 `ollama` 서비스가 완전히 시작된 후에 시작되도록 합니다.
- **호스트 설정**: `extra_hosts`를 사용하여 `host.docker.internal` 호스트 이름을 호스트 머신의 게이트웨이로 매핑합니다. 이는 컨테이너 내부에서 호스트 머신의 서비스(예: 로컬로 실행 중인 데이터베이스)에 접근할 수 있게 합니다.

**Section sources**
- [docker-compose.yml](file://docker-compose.yml#L1-L49)

## 컨테이너 실행 및 상태 점검
Docker Compose를 사용하여 컨테이너를 실행하고 상태를 점검하는 방법은 다음과 같습니다.

### 컨테이너 실행
1. `.env` 파일을 설정합니다. `env.example` 파일을 참조하여 LLM 바인딩, API 키, 임베딩 모델 등을 구성합니다.
2. 다음 명령어를 실행하여 컨테이너를 백그라운드에서 시작합니다.
```bash
docker compose up -d
```

### 로그 확인
실행 중인 컨테이너의 로그를 실시간으로 확인하려면 다음 명령어를 사용합니다.
```bash
docker compose logs -f
```
특정 서비스의 로그만 확인하려면 서비스 이름을 지정합니다 (예: `docker compose logs -f lightrag`).

### API 엔드포인트를 통한 상태 점검
LightRAG 서버는 `/health` 엔드포인트를 통해 시스템 상태를 제공합니다. 이 엔드포인트는 다음과 같은 정보를 반환합니다.

- **상태**: `healthy` 또는 `unhealthy`.
- **작업 디렉터리 및 입력 디렉터리**: 현재 설정된 경로.
- **구성 정보**: LLM 바인딩, 임베딩 모델, 쿼리 모드 등 현재 구성.
- **인증 모드**: 인증이 활성화되었는지 여부.
- **파이프라인 상태**: 현재 처리 중인지 여부.

다음 명령어를 사용하여 상태를 확인할 수 있습니다.
```bash
curl http://localhost:9621/health
```
또는 웹 브라우저에서 `http://localhost:9621/health`에 접속합니다.

**Section sources**
- [lightrag/api/lightrag_server.py](file://lightrag/api/lightrag_server.py#L700-L799)
- [lightrag/api/routers/query_routes.py](file://lightrag/api/routers/query_routes.py#L200-L224)

## 흔한 오류 및 해결 방안
Docker를 통한 LightRAG 설치 및 실행 과정에서 발생할 수 있는 흔한 오류와 그 해결 방안은 다음과 같습니다.

### 이미지 풀 실패
- **현상**: `docker compose up` 실행 시 `pull access denied` 또는 `manifest unknown` 오류가 발생합니다.
- **원인**: 지정된 이미지 태그가 존재하지 않거나, Docker Hub에 대한 접근 권한이 없는 경우입니다.
- **해결 방안**:
  1. `docker-compose.yml` 파일에서 `image` 필드의 태그가 올바른지 확인합니다.
  2. `docker pull ghcr.io/hkuds/lightrag:latest` 명령어를 수동으로 실행하여 이미지를 직접 풀링해 봅니다.
  3. 네트워크 연결 문제나 방화벽 설정을 확인합니다.

### 포트 충돌
- **현상**: `docker compose up` 실행 시 `Bind for 0.0.0.0:9621 failed: port is already allocated` 오류가 발생합니다.
- **원인**: 호스트의 `9621` 또는 `9622` 포트가 이미 다른 프로세스에 의해 사용 중입니다.
- **해결 방안**:
  1. `netstat -ano | findstr :9621` (Windows) 또는 `lsof -i :9621` (Linux/macOS) 명령어로 해당 포트를 사용 중인 프로세스를 확인합니다.
  2. 충돌하는 프로세스를 종료하거나, `docker-compose.yml` 파일에서 포트 매핑을 변경합니다 (예: `"9623:9621"`).

### 볼륨 권한 문제
- **현상**: 컨테이너가 시작되지만, 로그에 `Permission denied` 오류가 나타나며 데이터를 저장하거나 읽을 수 없습니다.
- **원인**: 호스트의 볼륨 디렉터리(`./data/rag_storage`, `./data/inputs` 등)에 대한 권한이 부족하거나, SELinux와 같은 보안 모듈이 작동 중일 수 있습니다.
- **해결 방안**:
  1. 호스트에서 해당 디렉터리의 권한을 확인하고, 필요한 경우 `chmod` 또는 `chown` 명령어로 수정합니다.
  2. Docker Desktop 사용 시, 공유 드라이브 설정에서 해당 디렉터리가 공유되어 있는지 확인합니다.
  3. SELinux가 활성화된 시스템에서는 볼륨 마운트에 `:Z` 또는 `:z` 플래그를 추가하여 SELinux 컨텍스트를 처리합니다 (예: `./data/rag_storage:/app/data/rag_storage:Z`).

**Section sources**
- [README.md](file://README.md#L100-L