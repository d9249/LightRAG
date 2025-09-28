"""
그래프 API 라우터
Presentation Tier의 그래프 관련 엔드포인트 정의
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.graph import (
    LabelListResponse, PopularLabelsResponse, LabelSearchRequest, LabelSearchResponse,
    GraphRequest, GraphResponse, EntityExistsRequest, EntityExistsResponse,
    EntityEditRequest, EntityEditResponse, RelationshipEditRequest, RelationshipEditResponse,
    GraphStatsResponse
)
from core.services.graph_service import graph_service


logger = logging.getLogger(__name__)
router = APIRouter()


# 레이블 관련 엔드포인트

@router.get("/label/list", response_model=LabelListResponse)
async def get_all_labels():
    """
    모든 그래프 레이블 목록
    
    - 그래프에 존재하는 모든 엔티티 레이블 반환
    - 검색 및 필터링에 활용
    """
    try:
        response = await graph_service.get_all_labels()
        return response
        
    except Exception as e:
        logger.error(f"레이블 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"레이블 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/label/popular", response_model=PopularLabelsResponse)
async def get_popular_labels(limit: int = Query(20, ge=1, le=100, description="반환할 레이블 수")):
    """
    인기 레이블 (연결도 높은 엔티티)
    
    - 연결도가 높은 엔티티들의 레이블
    - 중요한 개념이나 핵심 엔티티 식별에 활용
    """
    try:
        response = await graph_service.get_popular_labels(limit=limit)
        return response
        
    except Exception as e:
        logger.error(f"인기 레이블 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"인기 레이블 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/label/search", response_model=LabelSearchResponse)
async def search_labels(request: LabelSearchRequest):
    """
    레이블 퍼지 검색
    
    - 부분 일치 및 유사도 기반 레이블 검색
    - 자동완성 및 검색 제안에 활용
    """
    try:
        response = await graph_service.search_labels(request)
        return response
        
    except Exception as e:
        logger.error(f"레이블 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"레이블 검색 중 오류가 발생했습니다: {str(e)}")


# 그래프 데이터 조회

@router.post("", response_model=GraphResponse)  # POST /graph
async def get_graph_data(request: GraphRequest):
    """
    특정 레이블의 지식 그래프 서브그래프 조회
    
    - 지정된 엔티티들 주변의 그래프 구조 반환
    - 시각화 및 관계 분석에 활용
    - 탐색 깊이 및 노드/엣지 수 제한 가능
    """
    try:
        response = await graph_service.get_graph_data(request)
        
        logger.info(f"그래프 데이터 조회 완료: {len(request.entity_names)}개 엔티티, {response.total_nodes}개 노드")
        return response
        
    except Exception as e:
        logger.error(f"그래프 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"그래프 데이터 조회 중 오류가 발생했습니다: {str(e)}")


# GET 방식의 간단한 그래프 조회 (호환성을 위해)
@router.get("/subgraph", response_model=GraphResponse)
async def get_subgraph(
    entity_names: List[str] = Query(..., description="조회할 엔티티 이름 목록"),
    depth: int = Query(1, ge=1, le=5, description="탐색 깊이"),
    max_nodes: int = Query(100, ge=1, le=1000, description="최대 노드 수"),
    max_edges: int = Query(200, ge=1, le=2000, description="최대 엣지 수")
):
    """
    GET 방식 서브그래프 조회
    
    - URL 파라미터를 통한 간단한 그래프 조회
    - 외부 시스템 연동 및 임베딩에 활용
    """
    try:
        request = GraphRequest(
            entity_names=entity_names,
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges
        )
        
        response = await graph_service.get_graph_data(request)
        return response
        
    except Exception as e:
        logger.error(f"서브그래프 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서브그래프 조회 중 오류가 발생했습니다: {str(e)}")


# 엔티티 관리

@router.get("/entity/exists", response_model=EntityExistsResponse)
async def check_entity_exists(entity_name: str = Query(..., description="확인할 엔티티 이름")):
    """
    엔티티 존재 여부 확인
    
    - 지정된 엔티티가 그래프에 존재하는지 확인
    - 엔티티 정보도 함께 반환 (존재할 경우)
    """
    try:
        request = EntityExistsRequest(entity_name=entity_name)
        response = await graph_service.check_entity_exists(request)
        return response
        
    except Exception as e:
        logger.error(f"엔티티 존재 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=f"엔티티 존재 확인 중 오류가 발생했습니다: {str(e)}")


@router.post("/entity/edit", response_model=EntityEditResponse)
async def edit_entity(request: EntityEditRequest):
    """
    엔티티 속성 업데이트
    
    - 엔티티의 타입, 설명, 추가 속성 수정
    - 그래프 데이터의 품질 개선에 활용
    """
    try:
        response = await graph_service.edit_entity(request)
        
        if response.success:
            logger.info(f"엔티티 편집 완료: {request.entity_name}")
        else:
            logger.warning(f"엔티티 편집 실패: {request.entity_name} - {response.message}")
        
        return response
        
    except Exception as e:
        logger.error(f"엔티티 편집 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"엔티티 편집 중 오류가 발생했습니다: {str(e)}")


# 관계 관리

@router.post("/relation/edit", response_model=RelationshipEditResponse)
async def edit_relationship(request: RelationshipEditRequest):
    """
    관계 속성 업데이트
    
    - 관계의 설명, 강도, 키워드 수정
    - 그래프 관계의 품질 개선에 활용
    """
    try:
        response = await graph_service.edit_relationship(request)
        
        if response.success:
            logger.info(f"관계 편집 완료: {request.source_entity} -> {request.target_entity}")
        else:
            logger.warning(f"관계 편집 실패: {request.source_entity} -> {request.target_entity} - {response.message}")
        
        return response
        
    except Exception as e:
        logger.error(f"관계 편집 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"관계 편집 중 오류가 발생했습니다: {str(e)}")


# 그래프 통계

@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats():
    """
    그래프 통계 정보
    
    - 엔티티/관계 총 개수
    - 엔티티 타입별 분포
    - 연결도가 높은 엔티티
    - 그래프 밀도 등 구조적 특성
    """
    try:
        response = await graph_service.get_graph_stats()
        return response
        
    except Exception as e:
        logger.error(f"그래프 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"그래프 통계 조회 중 오류가 발생했습니다: {str(e)}")


# 유틸리티 엔드포인트

@router.get("/entity/{entity_name}/neighbors")
async def get_entity_neighbors(
    entity_name: str,
    depth: int = Query(1, ge=1, le=3, description="이웃 탐색 깊이"),
    limit: int = Query(50, ge=1, le=200, description="반환할 이웃 수 제한")
):
    """
    특정 엔티티의 이웃 노드 조회
    
    - 지정된 엔티티와 직접/간접 연결된 노드들
    - 관련 개념 탐색에 활용
    """
    try:
        request = GraphRequest(
            entity_names=[entity_name],
            depth=depth,
            max_nodes=limit,
            max_edges=limit * 2
        )
        
        graph_data = await graph_service.get_graph_data(request)
        
        # 이웃 노드만 추출 (원본 엔티티 제외)
        neighbors = [
            node for node in graph_data.graph_data.nodes 
            if node.id != entity_name
        ]
        
        return {
            "entity_name": entity_name,
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
            "total_edges": graph_data.total_edges
        }
        
    except Exception as e:
        logger.error(f"이웃 노드 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"이웃 노드 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/entity/{entity_name}/path/{target_entity}")
async def find_shortest_path(
    entity_name: str,
    target_entity: str,
    max_depth: int = Query(5, ge=1, le=10, description="최대 탐색 깊이")
):
    """
    두 엔티티 간의 최단 경로 찾기
    
    - 그래프 상에서 두 엔티티를 연결하는 최단 경로
    - 개념 간의 연관성 분석에 활용
    """
    try:
        # 간단한 구현: 두 엔티티를 포함하는 서브그래프 조회
        request = GraphRequest(
            entity_names=[entity_name, target_entity],
            depth=max_depth,
            max_nodes=100,
            max_edges=200
        )
        
        graph_data = await graph_service.get_graph_data(request)
        
        # 실제로는 그래프 알고리즘을 사용해 최단 경로를 계산해야 함
        # 여기서는 기본 구조만 반환
        return {
            "source_entity": entity_name,
            "target_entity": target_entity,
            "path_found": len(graph_data.graph_data.nodes) >= 2,
            "path_length": 0,  # 실제 계산 필요
            "path_nodes": [],  # 실제 계산 필요
            "graph_data": graph_data.graph_data
        }
        
    except Exception as e:
        logger.error(f"최단 경로 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"최단 경로 조회 중 오류가 발생했습니다: {str(e)}")


# 헬스 체크 엔드포인트
@router.get("/health")
async def health_check():
    """그래프 서비스 헬스 체크"""
    try:
        # 기본적인 서비스 상태 확인
        stats = await graph_service.get_graph_stats()
        
        return {
            "status": "healthy",
            "service": "graph_service",
            "total_entities": stats.total_entities,
            "total_relationships": stats.total_relationships,
            "graph_density": stats.graph_density,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"그래프 서비스 헬스 체크 실패: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "graph_service",
                "error": str(e)
            }
        )