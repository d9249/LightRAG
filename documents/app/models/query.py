"""
쿼리 관련 Pydantic 모델 정의
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class QueryMode(str, Enum):
    """쿼리 모드"""
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    NAIVE = "naive"
    MIX = "mix"
    BYPASS = "bypass"


class QueryRequest(BaseModel):
    """기본 쿼리 요청"""
    query: str = Field(..., description="쿼리 텍스트")
    mode: QueryMode = Field(default=QueryMode.MIX, description="쿼리 모드")
    only_need_context: bool = Field(default=False, description="컨텍스트만 필요한지 여부")
    only_need_prompt: bool = Field(default=False, description="프롬프트만 필요한지 여부")
    param: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 매개변수")


class QueryStreamRequest(QueryRequest):
    """스트리밍 쿼리 요청"""
    stream: bool = Field(default=True, description="스트리밍 모드")


class QueryDataRequest(BaseModel):
    """구조화된 데이터 쿼리 요청"""
    query: str = Field(..., description="쿼리 텍스트")
    mode: QueryMode = Field(default=QueryMode.MIX, description="쿼리 모드")
    include_entities: bool = Field(default=True, description="엔티티 포함 여부")
    include_relationships: bool = Field(default=True, description="관계 포함 여부")
    include_chunks: bool = Field(default=True, description="텍스트 청크 포함 여부")
    max_results: int = Field(default=20, description="최대 결과 수")


class ContextSource(BaseModel):
    """컨텍스트 소스 정보"""
    source_id: str = Field(..., description="소스 문서 ID")
    content: str = Field(..., description="컨텍스트 내용")
    relevance_score: float = Field(..., description="관련성 점수")
    source_type: str = Field(..., description="소스 타입 (chunk, entity, relationship)")


class QueryContext(BaseModel):
    """쿼리 컨텍스트"""
    local_context: List[ContextSource] = Field(default_factory=list, description="로컬 컨텍스트")
    global_context: List[ContextSource] = Field(default_factory=list, description="글로벌 컨텍스트")
    entities: List[str] = Field(default_factory=list, description="관련 엔티티")
    keywords: List[str] = Field(default_factory=list, description="추출된 키워드")


class QueryResponse(BaseModel):
    """기본 쿼리 응답"""
    query: str = Field(..., description="원본 쿼리")
    response: str = Field(..., description="생성된 응답")
    mode: QueryMode = Field(..., description="사용된 쿼리 모드")
    context: Optional[QueryContext] = Field(None, description="사용된 컨텍스트")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")
    processing_time: float = Field(..., description="처리 시간 (초)")


class EntityResult(BaseModel):
    """엔티티 검색 결과"""
    entity_name: str = Field(..., description="엔티티 이름")
    entity_type: str = Field(..., description="엔티티 타입")
    description: str = Field(..., description="엔티티 설명")
    relevance_score: float = Field(..., description="관련성 점수")
    source_documents: List[str] = Field(default_factory=list, description="출처 문서 ID")


class RelationshipResult(BaseModel):
    """관계 검색 결과"""
    source_entity: str = Field(..., description="출발 엔티티")
    target_entity: str = Field(..., description="도착 엔티티")
    description: str = Field(..., description="관계 설명")
    relationship_strength: float = Field(..., description="관계 강도")
    relationship_keywords: str = Field(..., description="관계 키워드")
    relevance_score: float = Field(..., description="관련성 점수")
    source_documents: List[str] = Field(default_factory=list, description="출처 문서 ID")


class ChunkResult(BaseModel):
    """텍스트 청크 검색 결과"""
    chunk_id: str = Field(..., description="청크 ID")
    content: str = Field(..., description="청크 내용")
    relevance_score: float = Field(..., description="관련성 점수")
    source_document: str = Field(..., description="출처 문서 ID")
    chunk_index: int = Field(..., description="문서 내 청크 순서")


class QueryDataResponse(BaseModel):
    """구조화된 데이터 쿼리 응답"""
    query: str = Field(..., description="원본 쿼리")
    mode: QueryMode = Field(..., description="사용된 쿼리 모드")
    entities: List[EntityResult] = Field(default_factory=list, description="관련 엔티티")
    relationships: List[RelationshipResult] = Field(default_factory=list, description="관련 관계")
    chunks: List[ChunkResult] = Field(default_factory=list, description="관련 텍스트 청크")
    total_results: int = Field(..., description="전체 결과 수")
    processing_time: float = Field(..., description="처리 시간 (초)")


class StreamingQueryChunk(BaseModel):
    """스트리밍 쿼리 청크"""
    chunk_type: str = Field(..., description="청크 타입 (text, context, metadata)")
    content: str = Field(..., description="청크 내용")
    is_final: bool = Field(default=False, description="마지막 청크 여부")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")


class QueryStatsResponse(BaseModel):
    """쿼리 통계 응답"""
    total_queries: int = Field(..., description="총 쿼리 수")
    queries_by_mode: Dict[str, int] = Field(..., description="모드별 쿼리 수")
    average_processing_time: float = Field(..., description="평균 처리 시간")
    success_rate: float = Field(..., description="성공률")
    last_24h_queries: int = Field(..., description="최근 24시간 쿼리 수")