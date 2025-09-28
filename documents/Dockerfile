# LightRAG Documents API Dockerfile
# 3-Tier 아키텍처 기반 FastAPI 애플리케이션

FROM python:3.11-slim

# 작업 디렉터리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    libmagic1 \
    libmagic-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY core/ ./core/
COPY config.ini .

# 데이터 디렉터리 생성
RUN mkdir -p /app/data/inputs \
             /app/data/rag_storage \
             /app/data/vector_storage \
             /app/data/graph_storage \
             /app/data/document_status \
             /app/data/cache \
             /app/data/logs

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=9621

# 포트 노출
EXPOSE 9621

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9621/health || exit 1

# 애플리케이션 실행
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9621"]