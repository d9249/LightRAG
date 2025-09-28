"""
LightRAG 래퍼 클래스
3-tier 아키텍처에 맞게 LightRAG 인스턴스를 추상화
"""
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.config import config

logger = logging.getLogger(__name__)


class LightRAGWrapper:
    """
    LightRAG 인스턴스를 래핑하여 3-tier 아키텍처에 맞게 추상화
    Business Logic Tier에서 Data Tier에 접근하는 인터페이스 제공
    """
    
    def __init__(self):
        self.rag = None
        self.config = config
        self._initialize_directories()
        self._initialize_lightrag()
    
    def _initialize_directories(self):
        """필요한 디렉터리 초기화"""
        directories = [
            self.config.rag_storage_dir,
            self.config.vector_storage_dir,
            self.config.graph_storage_dir,
            self.config.document_status_dir,
            self.config.cache_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"디렉터리 생성: {directory}")
    
    def _initialize_lightrag(self):
        """LightRAG 인스턴스 초기화"""
        try:
            # LightRAG 임포트는 실제 사용 시점에서 수행
            from lightrag import LightRAG
            
            # LightRAG 설정
            self.rag = LightRAG(
                working_dir=self.config.rag_storage_dir,
                llm_model_func=self._get_llm_model_func(),
                embedding_func=self._get_embedding_func(),
                vector_storage=self._get_vector_storage(),
                graph_storage=self._get_graph_storage(),
                chunk_token_size=self.config.chunk_size,
                chunk_overlap_token_size=self.config.chunk_overlap_size
            )
            
            # 저장소 초기화
            import asyncio
            if asyncio.get_event_loop().is_running():
                # 이미 실행 중인 이벤트 루프가 있는 경우
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.rag.initialize_storages())
                    future.result()
            else:
                # 새 이벤트 루프 실행
                asyncio.run(self.rag.initialize_storages())
            
            # 파이프라인 상태 초기화 추가
            try:
                from lightrag.kg.shared_storage import initialize_pipeline_status
                if asyncio.get_event_loop().is_running():
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, initialize_pipeline_status())
                        future.result()
                else:
                    asyncio.run(initialize_pipeline_status())
            except Exception as e:
                logger.warning(f"파이프라인 상태 초기화 실패 (계속 진행): {e}")
            
            logger.info("LightRAG 인스턴스 초기화 완료")
            
        except ImportError as e:
            logger.error(f"LightRAG 임포트 실패: {e}")
            raise Exception("LightRAG를 사용하기 위해 lightrag 패키지가 필요합니다")
        except Exception as e:
            logger.error(f"LightRAG 초기화 실패: {e}")
            raise
    
    def _get_llm_model_func(self):
        """LLM 모델 함수 반환"""
        try:
            from lightrag.llm.ollama import ollama_model_complete
            
            async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
                # hashing_kv를 kwargs에 추가 (LightRAG가 필요로 함)
                if 'hashing_kv' not in kwargs:
                    kwargs['hashing_kv'] = type('MockHashingKV', (), {
                        'global_config': {'llm_model_name': self.config.llm_model}
                    })()
                
                # Ollama 호스트 설정
                kwargs['host'] = self.config.ollama_url
                
                return await ollama_model_complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    **kwargs
                )
            
            return llm_model_func
            
        except ImportError:
            raise Exception("Ollama LLM 함수를 가져올 수 없습니다")
    
    def _get_embedding_func(self):
        """임베딩 함수 반환"""
        try:
            from lightrag.llm.ollama import ollama_embed
            from lightrag.utils import EmbeddingFunc
            
            async def embedding_func(texts, **kwargs):
                kwargs['host'] = self.config.ollama_url
                return await ollama_embed(
                    texts=texts,
                    embed_model=self.config.embedding_model,
                    **kwargs
                )
            
            return EmbeddingFunc(
                embedding_dim=768,  # nomic-embed-text의 차원
                max_token_size=8192,
                func=embedding_func
            )
            
        except ImportError:
            raise Exception("Ollama 임베딩 함수를 가져올 수 없습니다")
    
    def _get_vector_storage(self):
        """벡터 저장소 설정 반환"""
        # LightRAG는 기본적으로 내장 벡터 저장소를 사용
        # vector_storage 매개변수는 특별한 설정이 필요한 경우에만 사용
        return "JsonVectorDBStorage"  # 기본값
    
    def _get_graph_storage(self):
        """그래프 저장소 설정 반환"""
        if self.config.graph_storage.lower() == "neo4j":
            # Neo4j 환경변수 설정
            import os
            os.environ["NEO4J_URI"] = self.config.neo4j_url
            os.environ["NEO4J_USERNAME"] = self.config.neo4j_user
            os.environ["NEO4J_PASSWORD"] = self.config.neo4j_password
            return "Neo4JStorage"
        else:
            return "JsonGraphDBStorage"  # 기본값
    
    async def process_document(self, content: str, source_id: str) -> Dict[str, Any]:
        """
        Business Tier에서 호출하는 문서 처리 메서드
        
        Args:
            content: 문서 텍스트 내용
            source_id: 문서 식별자
            
        Returns:
            처리 결과 정보
        """
        try:
            if not self.rag:
                raise Exception("LightRAG가 초기화되지 않았습니다")
            
            # 문서 삽입
            await self.rag.ainsert(content)
            
            # 처리 결과 정보 수집
            result = {
                "source_id": source_id,
                "content_length": len(content),
                "status": "processed",
                "chunks_count": await self._count_chunks(source_id),
                "entities_count": await self._count_entities(source_id),
                "relationships_count": await self._count_relationships(source_id)
            }
            
            logger.info(f"문서 처리 완료: {source_id}")
            return result
            
        except Exception as e:
            logger.error(f"문서 처리 실패 ({source_id}): {e}")
            raise
    
    async def query_knowledge(self, query: str, mode: str = "mix", 
                            only_need_context: bool = False,
                            only_need_prompt: bool = False,
                            param: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Business Tier에서 호출하는 쿼리 처리 메서드
        
        Args:
            query: 쿼리 텍스트
            mode: 검색 모드 (local, global, hybrid, naive, mix, bypass)
            only_need_context: 컨텍스트만 반환할지 여부
            only_need_prompt: 프롬프트만 반환할지 여부
            param: 추가 매개변수
            
        Returns:
            쿼리 결과
        """
        try:
            if not self.rag:
                raise Exception("LightRAG가 초기화되지 않았습니다")
            
            # QueryParam 사용하여 쿼리 실행
            from lightrag import QueryParam
            query_param = QueryParam(mode=mode)
            
            if only_need_context:
                query_param.only_need_context = only_need_context
            if only_need_prompt:
                query_param.only_need_prompt = only_need_prompt
            
            # 추가 매개변수 설정
            if param:
                for key, value in param.items():
                    setattr(query_param, key, value)
            
            # 쿼리 실행
            response = await self.rag.aquery(query, param=query_param)
            
            result = {
                "query": query,
                "response": response,
                "mode": mode,
                "metadata": {"mode": mode, "only_need_context": only_need_context, "only_need_prompt": only_need_prompt}
            }
            
            logger.info(f"쿼리 처리 완료: {query[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"쿼리 처리 실패: {e}")
            raise
    
    async def get_graph_data(self, entity_names: List[str], depth: int = 1) -> Dict[str, Any]:
        """
        Business Tier에서 호출하는 그래프 데이터 조회
        
        Args:
            entity_names: 조회할 엔티티 이름 목록
            depth: 탐색 깊이
            
        Returns:
            그래프 데이터
        """
        try:
            if not self.rag:
                raise Exception("LightRAG가 초기화되지 않았습니다")
            
            # 그래프 저장소에서 데이터 조회
            graph_storage = self.rag.graph_storage
            
            nodes = []
            edges = []
            
            # 각 엔티티에 대해 그래프 데이터 수집
            for entity_name in entity_names:
                entity_data = await self._get_entity_subgraph(entity_name, depth)
                nodes.extend(entity_data.get("nodes", []))
                edges.extend(entity_data.get("edges", []))
            
            # 중복 제거
            unique_nodes = {node["id"]: node for node in nodes}
            unique_edges = {f"{edge['source']}-{edge['target']}": edge for edge in edges}
            
            result = {
                "nodes": list(unique_nodes.values()),
                "edges": list(unique_edges.values()),
                "query_entities": entity_names,
                "depth": depth,
                "total_nodes": len(unique_nodes),
                "total_edges": len(unique_edges)
            }
            
            logger.info(f"그래프 데이터 조회 완료: {len(entity_names)}개 엔티티")
            return result
            
        except Exception as e:
            logger.error(f"그래프 데이터 조회 실패: {e}")
            raise
    
    async def _count_chunks(self, source_id: str) -> int:
        """문서의 청크 수 계산"""
        try:
            # 실제 구현은 LightRAG의 내부 구조에 따라 달라질 수 있음
            return 0  # 임시값
        except Exception:
            return 0
    
    async def _count_entities(self, source_id: str) -> int:
        """문서에서 추출된 엔티티 수 계산"""
        try:
            # 실제 구현은 LightRAG의 내부 구조에 따라 달라질 수 있음
            return 0  # 임시값
        except Exception:
            return 0
    
    async def _count_relationships(self, source_id: str) -> int:
        """문서에서 추출된 관계 수 계산"""
        try:
            # 실제 구현은 LightRAG의 내부 구조에 따라 달라질 수 있음
            return 0  # 임시값
        except Exception:
            return 0
    
    async def _get_entity_subgraph(self, entity_name: str, depth: int) -> Dict[str, Any]:
        """엔티티 주변의 서브그래프 조회"""
        try:
            # 실제 구현은 LightRAG의 그래프 저장소 API에 따라 달라질 수 있음
            nodes = [{"id": entity_name, "label": entity_name, "type": "entity"}]
            edges = []
            
            return {"nodes": nodes, "edges": edges}
        except Exception:
            return {"nodes": [], "edges": []}
    
    async def clear_cache(self):
        """캐시 데이터 정리"""
        try:
            cache_dir = Path(self.config.cache_dir)
            if cache_dir.exists():
                for file_path in cache_dir.glob("*"):
                    if file_path.is_file():
                        file_path.unlink()
                logger.info("캐시 정리 완료")
        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}")
            raise


# 전역 LightRAG 래퍼 인스턴스
lightrag_wrapper = LightRAGWrapper()