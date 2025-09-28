"""
FastAPI 애플리케이션 메인 모듈
LightRAG Documents API 진입점
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import config
from app.routers import document_routes, query_routes, graph_routes


# 로깅 설정
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.log_file) if os.path.exists(os.path.dirname(config.log_file)) else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화
    logger.info("LightRAG Documents API 시작 중...")
    
    # 필요한 디렉터리 생성
    os.makedirs(config.inputs_dir, exist_ok=True)
    os.makedirs(config.rag_storage_dir, exist_ok=True)
    os.makedirs(config.vector_storage_dir, exist_ok=True)
    os.makedirs(config.document_status_dir, exist_ok=True)
    os.makedirs(config.cache_dir, exist_ok=True)
    os.makedirs(os.path.dirname(config.log_file), exist_ok=True)
    
    logger.info("디렉터리 초기화 완료")
    logger.info(f"API 서버가 포트 {config.port}에서 시작되었습니다")
    
    yield
    
    # 종료 시 정리
    logger.info("LightRAG Documents API 종료 중...")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="LightRAG 기반 문서 처리 및 쿼리 시스템",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 예외 처리기
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 처리"""
    logger.error(f"예외 발생: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"내부 서버 오류: {str(exc)}"}
    )


# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": config.app_name,
        "version": config.app_version,
        "debug": config.debug
    }


# 루트 엔드포인트
@app.get("/")
async def root():
    """API 기본 정보"""
    return {
        "message": f"{config.app_name} v{config.app_version}",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "documents": "/documents",
            "query": "/query",
            "graph": "/graph"
        }
    }


# 라우터 등록
app.include_router(
    document_routes.router,
    prefix="/documents",
    tags=["Documents"]
)

app.include_router(
    query_routes.router,
    prefix="/query",
    tags=["Query"]
)

app.include_router(
    graph_routes.router,
    prefix="/graph",
    tags=["Graph"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )