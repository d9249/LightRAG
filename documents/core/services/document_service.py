"""
문서 처리 서비스
Business Logic Tier의 문서 관련 비즈니스 로직 처리
"""
import os
import uuid
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from app.models.document import (
    DocumentMetadata, DocumentStatus, DocumentUploadResponse,
    TextInsertResponse, BatchTextInsertResponse, ScanDirectoryResponse,
    DocumentListResponse, DocumentStatusCounts, DocumentDeleteResponse,
    PipelineStatus, TrackingStatus
)
from core.lightrag_wrapper import lightrag_wrapper
from core.utils.file_handler import FileHandler


logger = logging.getLogger(__name__)


class DocumentService:
    """문서 처리 서비스 클래스"""
    
    def __init__(self):
        self.file_handler = FileHandler()
        self.lightrag = lightrag_wrapper
        self.status_file = Path(lightrag_wrapper.config.document_status_dir) / "documents.json"
        self.tracking_file = Path(lightrag_wrapper.config.document_status_dir) / "tracking.json"
        self.processing_queue = asyncio.Queue()
        self.active_tasks = {}
        self._ensure_status_files()
        self._start_background_processor()
    
    def _ensure_status_files(self):
        """상태 파일 초기화"""
        if not self.status_file.exists():
            self._save_documents_status({})
        if not self.tracking_file.exists():
            self._save_tracking_status({})
    
    def _start_background_processor(self):
        """백그라운드 문서 처리기 시작"""
        asyncio.create_task(self._background_processor())
    
    def _load_documents_status(self) -> Dict[str, DocumentMetadata]:
        """문서 상태 로드"""
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {doc_id: DocumentMetadata(**doc_data) for doc_id, doc_data in data.items()}
        except Exception:
            return {}
    
    def _save_documents_status(self, documents: Dict[str, DocumentMetadata]):
        """문서 상태 저장"""
        try:
            data = {doc_id: doc.dict() for doc_id, doc in documents.items()}
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"문서 상태 저장 실패: {e}")
    
    def _load_tracking_status(self) -> Dict[str, TrackingStatus]:
        """추적 상태 로드"""
        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {track_id: TrackingStatus(**track_data) for track_id, track_data in data.items()}
        except Exception:
            return {}
    
    def _save_tracking_status(self, tracking: Dict[str, TrackingStatus]):
        """추적 상태 저장"""
        try:
            data = {track_id: track.dict() for track_id, track in tracking.items()}
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"추적 상태 저장 실패: {e}")
    
    async def upload_file(self, file_content: bytes, filename: str, 
                         content_type: Optional[str] = None) -> DocumentUploadResponse:
        """파일 업로드 및 처리 큐에 추가"""
        try:
            # 파일 검증
            if not self.file_handler.is_supported_file(filename):
                raise ValueError(f"지원되지 않는 파일 형식: {filename}")
            
            if not self.file_handler.is_valid_file_size(len(file_content)):
                raise ValueError(f"파일 크기가 너무 큽니다: {len(file_content)} bytes")
            
            # 파일 저장
            file_path, unique_filename = self.file_handler.save_uploaded_file(file_content, filename)
            
            # 문서 메타데이터 생성
            document_id = str(uuid.uuid4())
            track_id = str(uuid.uuid4())
            
            doc_metadata = DocumentMetadata(
                id=document_id,
                file_path=file_path,
                original_filename=filename,
                file_size=len(file_content),
                mime_type=content_type or self.file_handler.get_mime_type(file_path),
                status=DocumentStatus.PENDING
            )
            
            # 추적 상태 생성
            tracking_status = TrackingStatus(
                track_id=track_id,
                status=DocumentStatus.PENDING,
                current_step="파일 업로드 완료",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 상태 저장
            documents = self._load_documents_status()
            documents[document_id] = doc_metadata
            self._save_documents_status(documents)
            
            tracking = self._load_tracking_status()
            tracking[track_id] = tracking_status
            self._save_tracking_status(tracking)
            
            # 처리 큐에 추가
            await self.processing_queue.put({
                'type': 'file_upload',
                'document_id': document_id,
                'track_id': track_id,
                'file_path': file_path
            })
            
            logger.info(f"파일 업로드 완료: {filename} -> {document_id}")
            
            return DocumentUploadResponse(
                track_id=track_id,
                document_id=document_id,
                message=f"파일 '{filename}'이 성공적으로 업로드되었습니다",
                status=DocumentStatus.PENDING
            )
            
        except Exception as e:
            logger.error(f"파일 업로드 실패: {e}")
            raise
    
    async def insert_text(self, content: str, source_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> TextInsertResponse:
        """텍스트 직접 삽입"""
        try:
            document_id = str(uuid.uuid4())
            track_id = str(uuid.uuid4())
            
            # 문서 메타데이터 생성
            doc_metadata = DocumentMetadata(
                id=document_id,
                file_path=f"text_insert_{document_id}",
                original_filename=source_id or f"text_{document_id}",
                file_size=len(content.encode('utf-8')),
                mime_type="text/plain",
                status=DocumentStatus.PENDING,
                content_length=len(content)
            )
            
            # 추적 상태 생성
            tracking_status = TrackingStatus(
                track_id=track_id,
                status=DocumentStatus.PENDING,
                current_step="텍스트 삽입 준비",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 상태 저장
            documents = self._load_documents_status()
            documents[document_id] = doc_metadata
            self._save_documents_status(documents)
            
            tracking = self._load_tracking_status()
            tracking[track_id] = tracking_status
            self._save_tracking_status(tracking)
            
            # 처리 큐에 추가
            await self.processing_queue.put({
                'type': 'text_insert',
                'document_id': document_id,
                'track_id': track_id,
                'content': content,
                'source_id': source_id,
                'metadata': metadata or {}
            })
            
            logger.info(f"텍스트 삽입 요청: {document_id}")
            
            return TextInsertResponse(
                track_id=track_id,
                document_id=document_id,
                message="텍스트가 성공적으로 삽입 큐에 추가되었습니다"
            )
            
        except Exception as e:
            logger.error(f"텍스트 삽입 실패: {e}")
            raise
    
    async def batch_insert_texts(self, texts: List[Dict[str, Any]]) -> BatchTextInsertResponse:
        """배치 텍스트 삽입"""
        track_ids = []
        document_ids = []
        success_count = 0
        
        for text_data in texts:
            try:
                content = text_data.get('content', '')
                source_id = text_data.get('source_id')
                metadata = text_data.get('metadata', {})
                
                response = await self.insert_text(content, source_id, metadata)
                track_ids.append(response.track_id)
                document_ids.append(response.document_id)
                success_count += 1
                
            except Exception as e:
                logger.error(f"배치 텍스트 삽입 중 오류: {e}")
                track_ids.append(None)
                document_ids.append(None)
        
        return BatchTextInsertResponse(
            track_ids=track_ids,
            document_ids=document_ids,
            success_count=success_count,
            total_count=len(texts)
        )
    
    async def scan_directory(self, directory_path: str, recursive: bool = True,
                           extensions: Optional[List[str]] = None) -> ScanDirectoryResponse:
        """디렉터리 스캔 및 파일 처리"""
        try:
            found_files = self.file_handler.scan_directory(directory_path, recursive, extensions)
            track_id = str(uuid.uuid4())
            
            # 추적 상태 생성
            tracking_status = TrackingStatus(
                track_id=track_id,
                status=DocumentStatus.PENDING,
                current_step=f"디렉터리 스캔 완료: {len(found_files)}개 파일 발견",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            tracking = self._load_tracking_status()
            tracking[track_id] = tracking_status
            self._save_tracking_status(tracking)
            
            # 각 파일을 처리 큐에 추가
            for file_path in found_files:
                await self.processing_queue.put({
                    'type': 'file_scan',
                    'track_id': track_id,
                    'file_path': file_path
                })
            
            logger.info(f"디렉터리 스캔 완료: {directory_path}, {len(found_files)}개 파일")
            
            return ScanDirectoryResponse(
                track_id=track_id,
                found_files=found_files,
                message=f"{len(found_files)}개 파일이 발견되어 처리 큐에 추가되었습니다"
            )
            
        except Exception as e:
            logger.error(f"디렉터리 스캔 실패: {e}")
            raise
    
    async def get_documents(self) -> DocumentListResponse:
        """모든 문서 상태 조회"""
        documents = self._load_documents_status()
        
        # 상태별로 그룹화
        grouped_docs = {
            'PENDING': [],
            'PROCESSING': [],
            'PROCESSED': [],
            'FAILED': []
        }
        
        status_counts = {
            'pending': 0,
            'processing': 0,
            'processed': 0,
            'failed': 0,
            'total': 0
        }
        
        for doc in documents.values():
            grouped_docs[doc.status].append(doc)
            status_counts[doc.status.lower()] += 1
            status_counts['total'] += 1
        
        return DocumentListResponse(
            documents=grouped_docs,
            total_count=len(documents),
            status_counts=status_counts
        )
    
    async def get_status_counts(self) -> DocumentStatusCounts:
        """문서 상태별 개수 통계"""
        documents = self._load_documents_status()
        
        counts = DocumentStatusCounts()
        for doc in documents.values():
            if doc.status == DocumentStatus.PENDING:
                counts.pending += 1
            elif doc.status == DocumentStatus.PROCESSING:
                counts.processing += 1
            elif doc.status == DocumentStatus.PROCESSED:
                counts.processed += 1
            elif doc.status == DocumentStatus.FAILED:
                counts.failed += 1
            counts.total += 1
        
        return counts
    
    async def delete_documents(self, document_ids: List[str], 
                             delete_files: bool = True) -> DocumentDeleteResponse:
        """지정된 문서들 삭제"""
        documents = self._load_documents_status()
        deleted_count = 0
        failed_ids = []
        
        for doc_id in document_ids:
            try:
                if doc_id in documents:
                    doc = documents[doc_id]
                    
                    # 파일 삭제
                    if delete_files and os.path.exists(doc.file_path):
                        self.file_handler.delete_file(doc.file_path)
                    
                    # 문서 상태에서 제거
                    del documents[doc_id]
                    deleted_count += 1
                    
                    logger.info(f"문서 삭제 완료: {doc_id}")
                else:
                    failed_ids.append(doc_id)
                    
            except Exception as e:
                logger.error(f"문서 삭제 실패 ({doc_id}): {e}")
                failed_ids.append(doc_id)
        
        # 상태 저장
        self._save_documents_status(documents)
        
        return DocumentDeleteResponse(
            deleted_count=deleted_count,
            failed_ids=failed_ids,
            message=f"{deleted_count}개 문서가 삭제되었습니다"
        )
    
    async def clear_all_documents(self) -> DocumentDeleteResponse:
        """모든 문서 및 데이터 삭제"""
        try:
            documents = self._load_documents_status()
            
            # 모든 파일 삭제
            deleted_count = 0
            for doc in documents.values():
                try:
                    if os.path.exists(doc.file_path):
                        self.file_handler.delete_file(doc.file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"파일 삭제 실패 ({doc.file_path}): {e}")
            
            # 상태 파일 초기화
            self._save_documents_status({})
            self._save_tracking_status({})
            
            # 캐시 정리
            await self.lightrag.clear_cache()
            
            logger.info("모든 문서 및 데이터 삭제 완료")
            
            return DocumentDeleteResponse(
                deleted_count=deleted_count,
                failed_ids=[],
                message="모든 문서와 데이터가 삭제되었습니다"
            )
            
        except Exception as e:
            logger.error(f"전체 삭제 실패: {e}")
            raise
    
    async def get_pipeline_status(self) -> PipelineStatus:
        """처리 파이프라인 상태"""
        tracking = self._load_tracking_status()
        
        active_tasks = len([t for t in tracking.values() if t.status == DocumentStatus.PROCESSING])
        pending_tasks = len([t for t in tracking.values() if t.status == DocumentStatus.PENDING])
        completed_tasks = len([t for t in tracking.values() if t.status == DocumentStatus.PROCESSED])
        failed_tasks = len([t for t in tracking.values() if t.status == DocumentStatus.FAILED])
        
        documents = self._load_documents_status()
        total_processed = len([d for d in documents.values() if d.status == DocumentStatus.PROCESSED])
        
        return PipelineStatus(
            active_tasks=active_tasks,
            pending_tasks=pending_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            total_processed_documents=total_processed
        )
    
    async def get_track_status(self, track_id: str) -> Optional[TrackingStatus]:
        """특정 추적 ID의 처리 상태"""
        tracking = self._load_tracking_status()
        return tracking.get(track_id)
    
    async def clear_cache(self):
        """LLM 캐시 데이터 삭제"""
        await self.lightrag.clear_cache()
    
    async def _background_processor(self):
        """백그라운드 문서 처리기"""
        while True:
            try:
                # 큐에서 작업 가져오기
                task = await self.processing_queue.get()
                
                # 작업 처리
                if task['type'] == 'file_upload':
                    await self._process_file_upload(task)
                elif task['type'] == 'text_insert':
                    await self._process_text_insert(task)
                elif task['type'] == 'file_scan':
                    await self._process_file_scan(task)
                
                # 작업 완료 표시
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"백그라운드 처리 오류: {e}")
    
    async def _process_file_upload(self, task: Dict[str, Any]):
        """파일 업로드 작업 처리"""
        document_id = task['document_id']
        track_id = task['track_id']
        file_path = task['file_path']
        
        try:
            # 상태 업데이트: 처리 중
            await self._update_processing_status(document_id, track_id, "파일 텍스트 추출 중")
            
            # 텍스트 추출
            content = self.file_handler.extract_text_content(file_path)
            
            # 상태 업데이트: LightRAG 처리 중
            await self._update_processing_status(document_id, track_id, "LightRAG 처리 중")
            
            # LightRAG 처리
            result = await self.lightrag.process_document(content, document_id)
            
            # 상태 업데이트: 완료
            await self._update_processed_status(document_id, track_id, result)
            
        except Exception as e:
            await self._update_failed_status(document_id, track_id, str(e))
    
    async def _process_text_insert(self, task: Dict[str, Any]):
        """텍스트 삽입 작업 처리"""
        document_id = task['document_id']
        track_id = task['track_id']
        content = task['content']
        
        try:
            # 상태 업데이트: 처리 중
            await self._update_processing_status(document_id, track_id, "텍스트 처리 중")
            
            # LightRAG 처리
            result = await self.lightrag.process_document(content, document_id)
            
            # 상태 업데이트: 완료
            await self._update_processed_status(document_id, track_id, result)
            
        except Exception as e:
            await self._update_failed_status(document_id, track_id, str(e))
    
    async def _process_file_scan(self, task: Dict[str, Any]):
        """파일 스캔 작업 처리"""
        # 파일 스캔의 경우 개별 파일을 파일 업로드로 처리
        file_path = task['file_path']
        
        try:
            # 파일 읽기
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            filename = os.path.basename(file_path)
            
            # 파일 업로드로 처리
            await self.upload_file(file_content, filename)
            
        except Exception as e:
            logger.error(f"파일 스캔 처리 실패 ({file_path}): {e}")
    
    async def _update_processing_status(self, document_id: str, track_id: str, step: str):
        """처리 중 상태 업데이트"""
        # 문서 상태 업데이트
        documents = self._load_documents_status()
        if document_id in documents:
            documents[document_id].status = DocumentStatus.PROCESSING
            documents[document_id].updated_at = datetime.now()
            self._save_documents_status(documents)
        
        # 추적 상태 업데이트
        tracking = self._load_tracking_status()
        if track_id in tracking:
            tracking[track_id].status = DocumentStatus.PROCESSING
            tracking[track_id].current_step = step
            tracking[track_id].updated_at = datetime.now()
            self._save_tracking_status(tracking)
    
    async def _update_processed_status(self, document_id: str, track_id: str, result: Dict[str, Any]):
        """처리 완료 상태 업데이트"""
        # 문서 상태 업데이트
        documents = self._load_documents_status()
        if document_id in documents:
            doc = documents[document_id]
            doc.status = DocumentStatus.PROCESSED
            doc.content_length = result.get('content_length')
            doc.chunks_count = result.get('chunks_count')
            doc.entities_count = result.get('entities_count')
            doc.relationships_count = result.get('relationships_count')
            doc.updated_at = datetime.now()
            self._save_documents_status(documents)
        
        # 추적 상태 업데이트
        tracking = self._load_tracking_status()
        if track_id in tracking:
            tracking[track_id].status = DocumentStatus.PROCESSED
            tracking[track_id].current_step = "처리 완료"
            tracking[track_id].progress = 1.0
            tracking[track_id].updated_at = datetime.now()
            self._save_tracking_status(tracking)
    
    async def _update_failed_status(self, document_id: str, track_id: str, error_msg: str):
        """처리 실패 상태 업데이트"""
        # 문서 상태 업데이트
        documents = self._load_documents_status()
        if document_id in documents:
            documents[document_id].status = DocumentStatus.FAILED
            documents[document_id].error_msg = error_msg
            documents[document_id].updated_at = datetime.now()
            self._save_documents_status(documents)
        
        # 추적 상태 업데이트
        tracking = self._load_tracking_status()
        if track_id in tracking:
            tracking[track_id].status = DocumentStatus.FAILED
            tracking[track_id].current_step = "처리 실패"
            tracking[track_id].error_message = error_msg
            tracking[track_id].updated_at = datetime.now()
            self._save_tracking_status(tracking)


# 전역 문서 서비스 인스턴스
document_service = DocumentService()