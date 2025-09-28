"""
그래프 관련 Pydantic 모델 정의
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """엔티티 모델"""
    entity_name: str = Field(..., description="엔티티 이름")
    entity_type: str = Field(..., description="엔티티 유형")
    description: str = Field(..., description="엔티티 설명")
    source_id: str = Field(..., description="출처 문서 ID")
    created_at: Optional[str] = Field(None, description="생성 시간")
    updated_at: Optional[str] = Field(None, description="수정 시간")


class Relationship(BaseModel):
    """관계 모델"""
    source_entity: str = Field(..., description="출발 엔티티")
    target_entity: str = Field(..., description="도착 엔티티")
    description: str = Field(..., description="관계 설명")
    relationship_strength: float = Field(..., description="관계 강도")
    relationship_keywords: str = Field(..., description="관계 키워드")
    source_id: str = Field(..., description="출처 문서 ID")
    created_at: Optional[str] = Field(None, description="생성 시간")
    updated_at: Optional[str] = Field(None, description="수정 시간")


class GraphNode(BaseModel):
    """그래프 노드 (시각화용)"""
    id: str = Field(..., description="노드 ID")
    label: str = Field(..., description="노드 레이블")
    type: str = Field(..., description="노드 타입")
    properties: Dict[str, Any] = Field(default_factory=dict, description="노드 속성")
    size: Optional[float] = Field(None, description="노드 크기")
    color: Optional[str] = Field(None, description="노드 색상")


class GraphEdge(BaseModel):
    """그래프 엣지 (시각화용)"""
    id: str = Field(..., description="엣지 ID")
    source: str = Field(..., description="출발 노드 ID")
    target: str = Field(..., description="도착 노드 ID")
    label: str = Field(..., description="엣지 레이블")
    weight: float = Field(default=1.0, description="엣지 가중치")
    properties: Dict[str, Any] = Field(default_factory=dict, description="엣지 속성")


class GraphData(BaseModel):
    """그래프 데이터"""
    nodes: List[GraphNode] = Field(default_factory=list, description="노드 목록")
    edges: List[GraphEdge] = Field(default_factory=list, description="엣지 목록")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="그래프 메타데이터")


class LabelListResponse(BaseModel):
    """레이블 목록 응답"""
    labels: List[str] = Field(..., description="모든 레이블 목록")
    count: int = Field(..., description="레이블 개수")


class PopularLabelsResponse(BaseModel):
    """인기 레이블 응답"""
    labels: List[Dict[str, Union[str, int]]] = Field(..., description="인기 레이블 (연결도 포함)")
    count: int = Field(..., description="레이블 개수")


class LabelSearchRequest(BaseModel):
    """레이블 검색 요청"""
    query: str = Field(..., description="검색 쿼리")
    limit: int = Field(default=10, description="결과 제한 수")
    fuzzy: bool = Field(default=True, description="퍼지 검색 여부")


class LabelSearchResponse(BaseModel):
    """레이블 검색 응답"""
    labels: List[Dict[str, Union[str, float]]] = Field(..., description="검색된 레이블 (유사도 포함)")
    query: str = Field(..., description="검색 쿼리")
    count: int = Field(..., description="결과 개수")


class GraphRequest(BaseModel):
    """그래프 조회 요청"""
    entity_names: List[str] = Field(..., description="조회할 엔티티 이름 목록")
    depth: int = Field(default=1, description="탐색 깊이")
    include_relationships: bool = Field(default=True, description="관계 포함 여부")
    max_nodes: int = Field(default=100, description="최대 노드 수")
    max_edges: int = Field(default=200, description="최대 엣지 수")


class GraphResponse(BaseModel):
    """그래프 조회 응답"""
    graph_data: GraphData = Field(..., description="그래프 데이터")
    query_entities: List[str] = Field(..., description="조회된 엔티티")
    total_nodes: int = Field(..., description="전체 노드 수")
    total_edges: int = Field(..., description="전체 엣지 수")
    depth: int = Field(..., description="실제 탐색 깊이")


class EntityExistsRequest(BaseModel):
    """엔티티 존재 확인 요청"""
    entity_name: str = Field(..., description="확인할 엔티티 이름")


class EntityExistsResponse(BaseModel):
    """엔티티 존재 확인 응답"""
    exists: bool = Field(..., description="존재 여부")
    entity_name: str = Field(..., description="엔티티 이름")
    entity_info: Optional[Entity] = Field(None, description="엔티티 정보 (존재할 경우)")


class EntityEditRequest(BaseModel):
    """엔티티 편집 요청"""
    entity_name: str = Field(..., description="편집할 엔티티 이름")
    new_entity_type: Optional[str] = Field(None, description="새 엔티티 타입")
    new_description: Optional[str] = Field(None, description="새 설명")
    additional_properties: Optional[Dict[str, Any]] = Field(None, description="추가 속성")


class EntityEditResponse(BaseModel):
    """엔티티 편집 응답"""
    success: bool = Field(..., description="편집 성공 여부")
    entity_name: str = Field(..., description="편집된 엔티티 이름")
    updated_fields: List[str] = Field(..., description="업데이트된 필드 목록")
    message: str = Field(..., description="응답 메시지")


class RelationshipEditRequest(BaseModel):
    """관계 편집 요청"""
    source_entity: str = Field(..., description="출발 엔티티")
    target_entity: str = Field(..., description="도착 엔티티")
    new_description: Optional[str] = Field(None, description="새 관계 설명")
    new_strength: Optional[float] = Field(None, description="새 관계 강도")
    new_keywords: Optional[str] = Field(None, description="새 관계 키워드")


class RelationshipEditResponse(BaseModel):
    """관계 편집 응답"""
    success: bool = Field(..., description="편집 성공 여부")
    source_entity: str = Field(..., description="출발 엔티티")
    target_entity: str = Field(..., description="도착 엔티티")
    updated_fields: List[str] = Field(..., description="업데이트된 필드 목록")
    message: str = Field(..., description="응답 메시지")


class GraphStatsResponse(BaseModel):
    """그래프 통계 응답"""
    total_entities: int = Field(..., description="전체 엔티티 수")
    total_relationships: int = Field(..., description="전체 관계 수")
    entity_types: Dict[str, int] = Field(..., description="엔티티 타입별 개수")
    most_connected_entities: List[Dict[str, Union[str, int]]] = Field(..., description="연결도가 높은 엔티티")
    graph_density: float = Field(..., description="그래프 밀도")
    clustering_coefficient: Optional[float] = Field(None, description="클러스터링 계수")