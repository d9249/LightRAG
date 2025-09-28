"""
그래프 관리 서비스
Business Logic Tier의 그래프 관련 비즈니스 로직 처리
"""
import logging
from typing import List, Dict, Any, Optional, Union

from app.models.graph import (
    Entity, Relationship, GraphData, GraphNode, GraphEdge,
    LabelListResponse, PopularLabelsResponse, LabelSearchRequest, LabelSearchResponse,
    GraphRequest, GraphResponse, EntityExistsRequest, EntityExistsResponse,
    EntityEditRequest, EntityEditResponse, RelationshipEditRequest, RelationshipEditResponse,
    GraphStatsResponse
)
from core.lightrag_wrapper import lightrag_wrapper


logger = logging.getLogger(__name__)


class GraphService:
    """그래프 관리 서비스 클래스"""
    
    def __init__(self):
        self.lightrag = lightrag_wrapper
    
    async def get_all_labels(self) -> LabelListResponse:
        """모든 그래프 레이블 목록 조회"""
        try:
            # 실제 구현은 LightRAG의 그래프 저장소에서 레이블을 조회해야 함
            labels = await self._fetch_all_labels()
            
            return LabelListResponse(
                labels=labels,
                count=len(labels)
            )
            
        except Exception as e:
            logger.error(f"레이블 목록 조회 실패: {e}")
            raise
    
    async def get_popular_labels(self, limit: int = 20) -> PopularLabelsResponse:
        """인기 레이블 조회 (연결도가 높은 엔티티)"""
        try:
            # 실제 구현은 그래프 저장소에서 노드의 연결도를 계산해야 함
            popular_labels = await self._fetch_popular_labels(limit)
            
            return PopularLabelsResponse(
                labels=popular_labels,
                count=len(popular_labels)
            )
            
        except Exception as e:
            logger.error(f"인기 레이블 조회 실패: {e}")
            raise
    
    async def search_labels(self, request: LabelSearchRequest) -> LabelSearchResponse:
        """레이블 퍼지 검색"""
        try:
            # 퍼지 검색 실행
            search_results = await self._perform_label_search(
                request.query, 
                request.limit, 
                request.fuzzy
            )
            
            return LabelSearchResponse(
                labels=search_results,
                query=request.query,
                count=len(search_results)
            )
            
        except Exception as e:
            logger.error(f"레이블 검색 실패: {e}")
            raise
    
    async def get_graph_data(self, request: GraphRequest) -> GraphResponse:
        """특정 레이블의 지식 그래프 서브그래프 조회"""
        try:
            # LightRAG 래퍼를 통해 그래프 데이터 조회
            graph_result = await self.lightrag.get_graph_data(
                entity_names=request.entity_names,
                depth=request.depth
            )
            
            # GraphData 형식으로 변환
            nodes = []
            edges = []
            
            for node_data in graph_result.get('nodes', []):
                node = GraphNode(
                    id=node_data['id'],
                    label=node_data['label'],
                    type=node_data.get('type', 'entity'),
                    properties=node_data.get('properties', {})
                )
                nodes.append(node)
            
            for edge_data in graph_result.get('edges', []):
                edge = GraphEdge(
                    id=f"{edge_data['source']}-{edge_data['target']}",
                    source=edge_data['source'],
                    target=edge_data['target'],
                    label=edge_data.get('label', 'related'),
                    weight=edge_data.get('weight', 1.0),
                    properties=edge_data.get('properties', {})
                )
                edges.append(edge)
            
            # 노드/엣지 수 제한 적용
            if len(nodes) > request.max_nodes:
                nodes = nodes[:request.max_nodes]
            
            if len(edges) > request.max_edges:
                edges = edges[:request.max_edges]
            
            graph_data = GraphData(
                nodes=nodes,
                edges=edges,
                metadata={
                    "query_entities": request.entity_names,
                    "depth": request.depth,
                    "timestamp": "now"
                }
            )
            
            response = GraphResponse(
                graph_data=graph_data,
                query_entities=request.entity_names,
                total_nodes=len(nodes),
                total_edges=len(edges),
                depth=graph_result.get('depth', request.depth)
            )
            
            logger.info(f"그래프 데이터 조회 완료: {len(request.entity_names)}개 엔티티, {len(nodes)}개 노드")
            return response
            
        except Exception as e:
            logger.error(f"그래프 데이터 조회 실패: {e}")
            raise
    
    async def check_entity_exists(self, request: EntityExistsRequest) -> EntityExistsResponse:
        """엔티티 존재 여부 확인"""
        try:
            # 그래프 저장소에서 엔티티 조회
            entity_info = await self._get_entity_info(request.entity_name)
            
            if entity_info:
                return EntityExistsResponse(
                    exists=True,
                    entity_name=request.entity_name,
                    entity_info=entity_info
                )
            else:
                return EntityExistsResponse(
                    exists=False,
                    entity_name=request.entity_name,
                    entity_info=None
                )
                
        except Exception as e:
            logger.error(f"엔티티 존재 확인 실패: {e}")
            raise
    
    async def edit_entity(self, request: EntityEditRequest) -> EntityEditResponse:
        """엔티티 속성 업데이트"""
        try:
            updated_fields = []
            
            # 엔티티 존재 확인
            entity_exists = await self._entity_exists(request.entity_name)
            if not entity_exists:
                raise ValueError(f"엔티티를 찾을 수 없습니다: {request.entity_name}")
            
            # 필드별 업데이트
            if request.new_entity_type is not None:
                await self._update_entity_type(request.entity_name, request.new_entity_type)
                updated_fields.append("entity_type")
            
            if request.new_description is not None:
                await self._update_entity_description(request.entity_name, request.new_description)
                updated_fields.append("description")
            
            if request.additional_properties:
                await self._update_entity_properties(request.entity_name, request.additional_properties)
                updated_fields.append("properties")
            
            return EntityEditResponse(
                success=True,
                entity_name=request.entity_name,
                updated_fields=updated_fields,
                message=f"엔티티 '{request.entity_name}'이 성공적으로 업데이트되었습니다"
            )
            
        except Exception as e:
            logger.error(f"엔티티 편집 실패: {e}")
            return EntityEditResponse(
                success=False,
                entity_name=request.entity_name,
                updated_fields=[],
                message=f"엔티티 편집 실패: {str(e)}"
            )
    
    async def edit_relationship(self, request: RelationshipEditRequest) -> RelationshipEditResponse:
        """관계 속성 업데이트"""
        try:
            updated_fields = []
            
            # 관계 존재 확인
            relationship_exists = await self._relationship_exists(
                request.source_entity, 
                request.target_entity
            )
            if not relationship_exists:
                raise ValueError(
                    f"관계를 찾을 수 없습니다: {request.source_entity} -> {request.target_entity}"
                )
            
            # 필드별 업데이트
            if request.new_description is not None:
                await self._update_relationship_description(
                    request.source_entity,
                    request.target_entity,
                    request.new_description
                )
                updated_fields.append("description")
            
            if request.new_strength is not None:
                await self._update_relationship_strength(
                    request.source_entity,
                    request.target_entity,
                    request.new_strength
                )
                updated_fields.append("strength")
            
            if request.new_keywords is not None:
                await self._update_relationship_keywords(
                    request.source_entity,
                    request.target_entity,
                    request.new_keywords
                )
                updated_fields.append("keywords")
            
            return RelationshipEditResponse(
                success=True,
                source_entity=request.source_entity,
                target_entity=request.target_entity,
                updated_fields=updated_fields,
                message=f"관계 '{request.source_entity} -> {request.target_entity}'이 성공적으로 업데이트되었습니다"
            )
            
        except Exception as e:
            logger.error(f"관계 편집 실패: {e}")
            return RelationshipEditResponse(
                success=False,
                source_entity=request.source_entity,
                target_entity=request.target_entity,
                updated_fields=[],
                message=f"관계 편집 실패: {str(e)}"
            )
    
    async def get_graph_stats(self) -> GraphStatsResponse:
        """그래프 통계 조회"""
        try:
            # 그래프 저장소에서 통계 정보 수집
            total_entities = await self._count_entities()
            total_relationships = await self._count_relationships()
            entity_types = await self._get_entity_type_counts()
            most_connected = await self._get_most_connected_entities()
            graph_density = await self._calculate_graph_density()
            
            return GraphStatsResponse(
                total_entities=total_entities,
                total_relationships=total_relationships,
                entity_types=entity_types,
                most_connected_entities=most_connected,
                graph_density=graph_density,
                clustering_coefficient=None  # 계산이 복잡하므로 선택적 구현
            )
            
        except Exception as e:
            logger.error(f"그래프 통계 조회 실패: {e}")
            raise
    
    # 내부 메서드들 (실제 구현은 LightRAG의 그래프 저장소 API에 의존)
    
    async def _fetch_all_labels(self) -> List[str]:
        """모든 레이블 조회"""
        # 실제 구현 필요
        return []
    
    async def _fetch_popular_labels(self, limit: int) -> List[Dict[str, Union[str, int]]]:
        """인기 레이블 조회"""
        # 실제 구현 필요
        return []
    
    async def _perform_label_search(self, query: str, limit: int, fuzzy: bool) -> List[Dict[str, Union[str, float]]]:
        """레이블 검색"""
        # 실제 구현 필요
        return []
    
    async def _get_entity_info(self, entity_name: str) -> Optional[Entity]:
        """엔티티 정보 조회"""
        # 실제 구현 필요
        return None
    
    async def _entity_exists(self, entity_name: str) -> bool:
        """엔티티 존재 확인"""
        # 실제 구현 필요
        return False
    
    async def _relationship_exists(self, source_entity: str, target_entity: str) -> bool:
        """관계 존재 확인"""
        # 실제 구현 필요
        return False
    
    async def _update_entity_type(self, entity_name: str, new_type: str):
        """엔티티 타입 업데이트"""
        # 실제 구현 필요
        pass
    
    async def _update_entity_description(self, entity_name: str, new_description: str):
        """엔티티 설명 업데이트"""
        # 실제 구현 필요
        pass
    
    async def _update_entity_properties(self, entity_name: str, properties: Dict[str, Any]):
        """엔티티 속성 업데이트"""
        # 실제 구현 필요
        pass
    
    async def _update_relationship_description(self, source: str, target: str, description: str):
        """관계 설명 업데이트"""
        # 실제 구현 필요
        pass
    
    async def _update_relationship_strength(self, source: str, target: str, strength: float):
        """관계 강도 업데이트"""
        # 실제 구현 필요
        pass
    
    async def _update_relationship_keywords(self, source: str, target: str, keywords: str):
        """관계 키워드 업데이트"""
        # 실제 구현 필요
        pass
    
    async def _count_entities(self) -> int:
        """엔티티 총 개수"""
        # 실제 구현 필요
        return 0
    
    async def _count_relationships(self) -> int:
        """관계 총 개수"""
        # 실제 구현 필요
        return 0
    
    async def _get_entity_type_counts(self) -> Dict[str, int]:
        """엔티티 타입별 개수"""
        # 실제 구현 필요
        return {}
    
    async def _get_most_connected_entities(self) -> List[Dict[str, Union[str, int]]]:
        """연결도가 높은 엔티티"""
        # 실제 구현 필요
        return []
    
    async def _calculate_graph_density(self) -> float:
        """그래프 밀도 계산"""
        # 실제 구현 필요
        return 0.0


# 전역 그래프 서비스 인스턴스
graph_service = GraphService()