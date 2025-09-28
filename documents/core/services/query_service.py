"""
쿼리 처리 서비스
Business Logic Tier의 쿼리 관련 비즈니스 로직 처리
"""
import time
import logging
from typing import Dict, Any, Optional, AsyncGenerator

from app.models.query import (
    QueryRequest, QueryResponse, QueryDataRequest, QueryDataResponse,
    QueryContext, EntityResult, RelationshipResult, ChunkResult,
    StreamingQueryChunk, QueryStatsResponse, ContextSource
)
from core.lightrag_wrapper import lightrag_wrapper


logger = logging.getLogger(__name__)


class QueryService:
    """쿼리 처리 서비스 클래스"""
    
    def __init__(self):
        self.lightrag = lightrag_wrapper
        self.query_stats = {
            'total_queries': 0,
            'queries_by_mode': {},
            'total_processing_time': 0,
            'successful_queries': 0,
            'failed_queries': 0
        }
    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """기본 RAG 쿼리 처리"""
        start_time = time.time()
        
        try:
            # 쿼리 통계 업데이트
            self._update_query_stats(request.mode)
            
            # LightRAG로 쿼리 처리
            result = await self.lightrag.query_knowledge(
                query=request.query,
                mode=request.mode,
                only_need_context=request.only_need_context,
                only_need_prompt=request.only_need_prompt,
                param=request.param
            )
            
            processing_time = time.time() - start_time
            
            # 컨텍스트 정보 구성 (만약 only_need_context가 True인 경우)
            context = None
            if request.only_need_context:
                context = await self._build_query_context(request.query, request.mode)
            
            response = QueryResponse(
                query=request.query,
                response=result['response'],
                mode=request.mode,
                context=context,
                metadata=result.get('metadata', {}),
                processing_time=processing_time
            )
            
            # 성공 통계 업데이트
            self.query_stats['successful_queries'] += 1
            self.query_stats['total_processing_time'] += processing_time
            
            logger.info(f"쿼리 처리 완료: {request.query[:50]}... ({processing_time:.2f}s)")
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.query_stats['failed_queries'] += 1
            
            logger.error(f"쿼리 처리 실패: {e}")
            raise
    
    async def process_streaming_query(self, request: QueryRequest) -> AsyncGenerator[StreamingQueryChunk, None]:
        """스트리밍 RAG 쿼리 처리"""
        try:
            # 쿼리 통계 업데이트
            self._update_query_stats(request.mode)
            
            # 먼저 컨텍스트 정보 스트리밍
            yield StreamingQueryChunk(
                chunk_type="context",
                content="쿼리 처리를 시작합니다...",
                is_final=False,
                metadata={"step": "initialization"}
            )
            
            # LightRAG로 쿼리 처리 (실제로는 스트리밍을 지원해야 함)
            result = await self.lightrag.query_knowledge(
                query=request.query,
                mode=request.mode,
                only_need_context=request.only_need_context,
                only_need_prompt=request.only_need_prompt,
                param=request.param
            )
            
            # 응답을 청크로 나누어 스트리밍
            response_text = result['response']
            chunk_size = 100  # 청크 크기
            
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                is_final = (i + chunk_size) >= len(response_text)
                
                yield StreamingQueryChunk(
                    chunk_type="text",
                    content=chunk,
                    is_final=is_final,
                    metadata={"chunk_index": i // chunk_size}
                )
            
            # 메타데이터 전송
            yield StreamingQueryChunk(
                chunk_type="metadata",
                content="",
                is_final=True,
                metadata={
                    "query": request.query,
                    "mode": request.mode,
                    "total_chunks": len(response_text) // chunk_size + 1
                }
            )
            
            # 성공 통계 업데이트
            self.query_stats['successful_queries'] += 1
            
            logger.info(f"스트리밍 쿼리 처리 완료: {request.query[:50]}...")
            
        except Exception as e:
            self.query_stats['failed_queries'] += 1
            logger.error(f"스트리밍 쿼리 처리 실패: {e}")
            
            yield StreamingQueryChunk(
                chunk_type="error",
                content=f"오류 발생: {str(e)}",
                is_final=True,
                metadata={"error": True}
            )
    
    async def process_data_query(self, request: QueryDataRequest) -> QueryDataResponse:
        """구조화된 데이터 검색 (LLM 생성 없이 원시 검색 결과)"""
        start_time = time.time()
        
        try:
            # 쿼리 통계 업데이트
            self._update_query_stats(request.mode)
            
            # 원시 검색 결과 수집
            entities = []
            relationships = []
            chunks = []
            
            if request.include_entities:
                entities = await self._search_entities(request.query, request.max_results)
            
            if request.include_relationships:
                relationships = await self._search_relationships(request.query, request.max_results)
            
            if request.include_chunks:
                chunks = await self._search_chunks(request.query, request.max_results)
            
            processing_time = time.time() - start_time
            total_results = len(entities) + len(relationships) + len(chunks)
            
            response = QueryDataResponse(
                query=request.query,
                mode=request.mode,
                entities=entities,
                relationships=relationships,
                chunks=chunks,
                total_results=total_results,
                processing_time=processing_time
            )
            
            # 성공 통계 업데이트
            self.query_stats['successful_queries'] += 1
            self.query_stats['total_processing_time'] += processing_time
            
            logger.info(f"데이터 쿼리 처리 완료: {request.query[:50]}... ({total_results}개 결과)")
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.query_stats['failed_queries'] += 1
            
            logger.error(f"데이터 쿼리 처리 실패: {e}")
            raise
    
    async def get_query_stats(self) -> QueryStatsResponse:
        """쿼리 통계 반환"""
        total_queries = self.query_stats['total_queries']
        success_rate = 0.0
        average_processing_time = 0.0
        
        if total_queries > 0:
            success_rate = self.query_stats['successful_queries'] / total_queries
            average_processing_time = (
                self.query_stats['total_processing_time'] / 
                self.query_stats['successful_queries']
            ) if self.query_stats['successful_queries'] > 0 else 0.0
        
        return QueryStatsResponse(
            total_queries=total_queries,
            queries_by_mode=self.query_stats['queries_by_mode'].copy(),
            average_processing_time=average_processing_time,
            success_rate=success_rate,
            last_24h_queries=total_queries  # 실제로는 시간 기반 필터링 필요
        )
    
    def _update_query_stats(self, mode: str):
        """쿼리 통계 업데이트"""
        self.query_stats['total_queries'] += 1
        if mode not in self.query_stats['queries_by_mode']:
            self.query_stats['queries_by_mode'][mode] = 0
        self.query_stats['queries_by_mode'][mode] += 1
    
    async def _build_query_context(self, query: str, mode: str) -> QueryContext:
        """쿼리 컨텍스트 구성"""
        try:
            # 실제 구현은 LightRAG의 내부 API를 사용해야 함
            # 여기서는 기본 구조만 제공
            context = QueryContext(
                local_context=[],
                global_context=[],
                entities=[],
                keywords=query.split()  # 단순한 키워드 추출
            )
            
            return context
            
        except Exception as e:
            logger.error(f"컨텍스트 구성 실패: {e}")
            return QueryContext()
    
    async def _search_entities(self, query: str, max_results: int) -> list[EntityResult]:
        """엔티티 검색"""
        try:
            # 실제 구현은 LightRAG의 그래프 저장소를 사용해야 함
            # 여기서는 빈 결과 반환
            return []
            
        except Exception as e:
            logger.error(f"엔티티 검색 실패: {e}")
            return []
    
    async def _search_relationships(self, query: str, max_results: int) -> list[RelationshipResult]:
        """관계 검색"""
        try:
            # 실제 구현은 LightRAG의 그래프 저장소를 사용해야 함
            # 여기서는 빈 결과 반환
            return []
            
        except Exception as e:
            logger.error(f"관계 검색 실패: {e}")
            return []
    
    async def _search_chunks(self, query: str, max_results: int) -> list[ChunkResult]:
        """텍스트 청크 검색"""
        try:
            # 실제 구현은 LightRAG의 벡터 저장소를 사용해야 함
            # 여기서는 빈 결과 반환
            return []
            
        except Exception as e:
            logger.error(f"청크 검색 실패: {e}")
            return []


# 전역 쿼리 서비스 인스턴스
query_service = QueryService()