"""
문서 관련 Pydantic 모델 정의
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """문서 처리 상태"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class DocumentMetadata(BaseModel):
    """문서 메타데이터"""
    id: str = Field(..., description="문서 고유 식별자")
    file_path: str = Field(..., description="저장된 파일 경로")
    original_filename: str = Field(..., description="원본 파일명")
    file_size: int = Field(..., description="파일 크기 (bytes)")
    mime_type: str = Field(..., description="MIME 타입")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="처리 상태")
    content_length: Optional[int] = Field(None, description="문서 내용 길이")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    updated_at: datetime = Field(default_factory=datetime.now, description="수정 시간")
    chunks_count: Optional[int] = Field(None, description="청크 개수")
    entities_count: Optional[int] = Field(None, description="추출된 엔티티 개수")
    relationships_count: Optional[int] = Field(None, description="추출된 관계 개수")
    error_msg: Optional[str] = Field(None, description="오류 메시지")


class DocumentUploadRequest(BaseModel):
    """문서 업로드 요청"""
    filename: str = Field(..., description="파일명")
    content_type: Optional[str] = Field(None, description="콘텐츠 타입")


class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답"""
    track_id: str = Field(..., description="추적 ID")
    document_id: str = Field(..., description="문서 ID")
    message: str = Field(..., description="응답 메시지")
    status: DocumentStatus = Field(..., description="초기 상태")


class TextInsertRequest(BaseModel):
    """텍스트 직접 삽입 요청"""
    content: str = Field(..., description="텍스트 내용")
    source_id: Optional[str] = Field(None, description="출처 식별자")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 메타데이터")


class TextInsertResponse(BaseModel):
    """텍스트 삽입 응답"""
    track_id: str = Field(..., description="추적 ID")
    document_id: str = Field(..., description="문서 ID")
    message: str = Field(..., description="응답 메시지")


class BatchTextInsertRequest(BaseModel):
    """배치 텍스트 삽입 요청"""
    texts: List[TextInsertRequest] = Field(..., description="텍스트 목록")


class BatchTextInsertResponse(BaseModel):
    """배치 텍스트 삽입 응답"""
    track_ids: List[str] = Field(..., description="추적 ID 목록")
    document_ids: List[str] = Field(..., description="문서 ID 목록")
    success_count: int = Field(..., description="성공한 텍스트 수")
    total_count: int = Field(..., description="전체 텍스트 수")


class ScanDirectoryRequest(BaseModel):
    """디렉터리 스캔 요청"""
    directory_path: str = Field(..., description="스캔할 디렉터리 경로")
    recursive: bool = Field(default=True, description="재귀적 스캔 여부")
    extensions: Optional[List[str]] = Field(None, description="허용할 파일 확장자")


class ScanDirectoryResponse(BaseModel):
    """디렉터리 스캔 응답"""
    track_id: str = Field(..., description="스캔 작업 추적 ID")
    found_files: List[str] = Field(..., description="발견된 파일 목록")
    message: str = Field(..., description="응답 메시지")


class DocumentListResponse(BaseModel):
    """문서 목록 응답"""
    documents: Dict[str, List[DocumentMetadata]] = Field(..., description="상태별 문서 목록")
    total_count: int = Field(..., description="전체 문서 수")
    status_counts: Dict[str, int] = Field(..., description="상태별 문서 수")


class DocumentStatusCounts(BaseModel):
    """문서 상태별 개수"""
    pending: int = Field(default=0, description="대기 중인 문서 수")
    processing: int = Field(default=0, description="처리 중인 문서 수")
    processed: int = Field(default=0, description="처리 완료된 문서 수")
    failed: int = Field(default=0, description="실패한 문서 수")
    total: int = Field(default=0, description="전체 문서 수")


class DocumentDeleteRequest(BaseModel):
    """문서 삭제 요청"""
    document_ids: List[str] = Field(..., description="삭제할 문서 ID 목록")
    delete_files: bool = Field(default=True, description="원본 파일도 삭제할지 여부")


class DocumentDeleteResponse(BaseModel):
    """문서 삭제 응답"""
    deleted_count: int = Field(..., description="삭제된 문서 수")
    failed_ids: List[str] = Field(default_factory=list, description="삭제 실패한 문서 ID")
    message: str = Field(..., description="응답 메시지")


class PipelineStatus(BaseModel):
    """처리 파이프라인 상태"""
    active_tasks: int = Field(..., description="활성 작업 수")
    pending_tasks: int = Field(..., description="대기 중인 작업 수")
    completed_tasks: int = Field(..., description="완료된 작업 수")
    failed_tasks: int = Field(..., description="실패한 작업 수")
    total_processed_documents: int = Field(..., description="총 처리된 문서 수")


class TrackingStatus(BaseModel):
    """추적 상태 정보"""
    track_id: str = Field(..., description="추적 ID")
    status: DocumentStatus = Field(..., description="현재 상태")
    progress: float = Field(default=0.0, description="진행률 (0.0-1.0)")
    current_step: str = Field(..., description="현재 처리 단계")
    estimated_completion: Optional[datetime] = Field(None, description="예상 완료 시간")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    created_at: datetime = Field(..., description="시작 시간")
    updated_at: datetime = Field(..., description="마지막 업데이트 시간")