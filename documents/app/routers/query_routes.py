"""
쿼리 API 라우터
Presentation Tier의 쿼리 관련 엔드포인트 정의
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json

from app.models.query import (
    QueryRequest, QueryResponse, QueryStreamRequest,
    QueryDataRequest, QueryDataResponse, QueryStatsResponse
)
from core.services.query_service import query_service


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    기본 RAG 쿼리 (비스트리밍 응답)
    
    지원 모드:
    - local: 특정 엔티티 중심 검색
    - global: 글로벌 패턴 분석
    - hybrid: 하이브리드 검색
    - naive: 단순 벡터 검색
    - mix: 혼합 모드 (기본값)
    - bypass: LightRAG 우회 (직접 LLM 호출)
    """
    try:
        response = await query_service.process_query(request)
        
        logger.info(f"쿼리 처리 완료: {request.query[:50]}... (모드: {request.mode})")
        return response
        
    except Exception as e:
        logger.error(f"쿼리 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"쿼리 처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/stream")
async def process_streaming_query(request: QueryRequest):
    """
    스트리밍 RAG 쿼리 (실시간 응답)
    
    - 실시간으로 응답을 스트리밍
    - 긴 응답에 대한 사용자 경험 개선
    - Server-Sent Events 형태로 전송
    """
    try:
        async def generate_stream():
            """스트리밍 응답 생성기"""
            try:
                async for chunk in query_service.process_streaming_query(request):
                    # SSE 형태로 데이터 전송
                    data = json.dumps(chunk.dict(), ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    
                    if chunk.is_final:
                        break
                
                # 스트림 종료
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"스트리밍 쿼리 처리 중 오류: {e}")
                error_data = {
                    "chunk_type": "error",
                    "content": f"오류 발생: {str(e)}",
                    "is_final": True,
                    "metadata": {"error": True}
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        logger.info(f"스트리밍 쿼리 시작: {request.query[:50]}... (모드: {request.mode})")
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Nginx 버퍼링 비활성화
            }
        )
        
    except Exception as e:
        logger.error(f"스트리밍 쿼리 초기화 실패: {e}")
        raise HTTPException(status_code=500, detail=f"스트리밍 쿼리 초기화 중 오류가 발생했습니다: {str(e)}")


@router.post("/data", response_model=QueryDataResponse)
async def process_data_query(request: QueryDataRequest):
    """
    구조화된 데이터 검색 (LLM 생성 없이 원시 검색 결과)
    
    - 엔티티, 관계, 텍스트 청크 원시 데이터 반환
    - LLM 응답 생성 없이 검색 결과만 제공
    - 데이터 분석 및 시각화용
    """
    try:
        response = await query_service.process_data_query(request)
        
        logger.info(f"데이터 쿼리 처리 완료: {request.query[:50]}... ({response.total_results}개 결과)")
        return response
        
    except Exception as e:
        logger.error(f"데이터 쿼리 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 쿼리 처리 중 오류가 발생했습니다: {str(e)}")


@router.get("/stats", response_model=QueryStatsResponse)
async def get_query_stats():
    """
    쿼리 통계 정보
    
    - 총 쿼리 수, 모드별 사용량
    - 평균 처리 시간, 성공률
    - 모니터링 및 분석용
    """
    try:
        response = await query_service.get_query_stats()
        return response
        
    except Exception as e:
        logger.error(f"쿼리 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"쿼리 통계 조회 중 오류가 발생했습니다: {str(e)}")


# 쿼리 모드별 전용 엔드포인트들

@router.post("/local", response_model=QueryResponse)
async def local_query(query: str):
    """
    로컬 모드 쿼리
    
    - 특정 엔티티 중심의 검색
    - 엔티티 주변의 관련 정보 탐색
    """
    try:
        request = QueryRequest(query=query, mode="local")
        response = await query_service.process_query(request)
        return response
        
    except Exception as e:
        logger.error(f"로컬 쿼리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"로컬 쿼리 처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/global", response_model=QueryResponse)
async def global_query(query: str):
    """
    글로벌 모드 쿼리
    
    - 전체 그래프의 글로벌 패턴 분석
    - 커뮤니티 및 클러스터 기반 검색
    """
    try:
        request = QueryRequest(query=query, mode="global")
        response = await query_service.process_query(request)
        return response
        
    except Exception as e:
        logger.error(f"글로벌 쿼리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"글로벌 쿼리 처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/hybrid", response_model=QueryResponse)
async def hybrid_query(query: str):
    """
    하이브리드 모드 쿼리
    
    - 로컬과 글로벌 검색의 조합
    - 균형잡힌 검색 결과 제공
    """
    try:
        request = QueryRequest(query=query, mode="hybrid")
        response = await query_service.process_query(request)
        return response
        
    except Exception as e:
        logger.error(f"하이브리드 쿼리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"하이브리드 쿼리 처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/naive", response_model=QueryResponse)
async def naive_query(query: str):
    """
    나이브 모드 쿼리
    
    - 단순 벡터 유사도 검색
    - 빠른 검색이 필요한 경우
    """
    try:
        request = QueryRequest(query=query, mode="naive")
        response = await query_service.process_query(request)
        return response
        
    except Exception as e:
        logger.error(f"나이브 쿼리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"나이브 쿼리 처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/context", response_model=QueryResponse)
async def context_only_query(query: str):
    """
    컨텍스트만 반환하는 쿼리
    
    - LLM 응답 생성 없이 관련 컨텍스트만 반환
    - 빠른 정보 탐색용
    """
    try:
        request = QueryRequest(query=query, mode="mix", only_need_context=True)
        response = await query_service.process_query(request)
        return response
        
    except Exception as e:
        logger.error(f"컨텍스트 쿼리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"컨텍스트 쿼리 처리 중 오류가 발생했습니다: {str(e)}")


# 헬스 체크 엔드포인트
@router.get("/health")
async def health_check():
    """쿼리 서비스 헬스 체크"""
    try:
        # 기본적인 서비스 상태 확인
        stats = await query_service.get_query_stats()
        
        return {
            "status": "healthy",
            "service": "query_service",
            "total_queries": stats.total_queries,
            "success_rate": stats.success_rate,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"쿼리 서비스 헬스 체크 실패: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "query_service",
                "error": str(e)
            }
        )