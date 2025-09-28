"""
FastAPI 애플리케이션 설정 모듈
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """애플리케이션 설정 클래스"""
    
    # 기본 설정
    app_name: str = "LightRAG Documents API"
    app_version: str = "1.0.0"
    debug: bool = False
    port: int = 9621
    
    # LLM 설정
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1"
    embedding_model: str = "nomic-embed-text"
    
    # 데이터베이스 설정
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # 저장소 설정
    vector_storage: str = "nanodb"
    graph_storage: str = "neo4j"
    data_dir: str = "/app/data"
    
    # 파일 처리 설정
    max_file_size: int = 104857600  # 100MB
    supported_extensions: str = ".pdf,.docx,.pptx,.xlsx,.txt,.md,.json,.xml,.csv"
    chunk_size: int = 1200
    chunk_overlap_size: int = 100
    
    # 성능 설정
    max_workers: int = 4
    processing_timeout: int = 300
    batch_size: int = 10
    
    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "/app/data/logs/app.log"
    
    # 보안 설정
    api_secret_key: str = "your-secret-key-here"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # 캐시 설정
    enable_cache: bool = True
    cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def supported_extensions_list(self) -> List[str]:
        """지원되는 파일 확장자 리스트 반환"""
        return [ext.strip() for ext in self.supported_extensions.split(",")]
    
    @property
    def inputs_dir(self) -> str:
        """입력 파일 디렉터리 경로"""
        return os.path.join(self.data_dir, "inputs")
    
    @property
    def rag_storage_dir(self) -> str:
        """RAG 저장소 디렉터리 경로"""
        return os.path.join(self.data_dir, "rag_storage")
    
    @property
    def vector_storage_dir(self) -> str:
        """벡터 저장소 디렉터리 경로"""
        return os.path.join(self.data_dir, "vector_storage")
    
    @property
    def graph_storage_dir(self) -> str:
        """그래프 저장소 디렉터리 경로"""
        return os.path.join(self.data_dir, "graph_storage")
    
    @property
    def document_status_dir(self) -> str:
        """문서 상태 디렉터리 경로"""
        return os.path.join(self.data_dir, "document_status")
    
    @property
    def cache_dir(self) -> str:
        """캐시 디렉터리 경로"""
        return os.path.join(self.data_dir, "cache")


# 전역 설정 인스턴스
config = AppConfig()