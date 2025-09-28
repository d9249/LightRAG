"""
문서 관리 API 라우터
Presentation Tier의 문서 관련 엔드포인트 정의
"""
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.document import (
    DocumentUploadResponse, TextInsertRequest, TextInsertResponse,
    BatchTextInsertRequest, BatchTextInsertResponse, ScanDirectoryRequest, ScanDirectoryResponse,
    DocumentListResponse, DocumentStatusCounts, DocumentDeleteRequest, DocumentDeleteResponse,
    PipelineStatus, TrackingStatus
)
from core.services.document_service import document_service


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    파일 업로드 및 인덱싱 (백그라운드 처리)
    
    - 지원 형식: PDF, DOCX, PPTX, XLSX, TXT, MD, JSON, XML 등
    - 최대 크기: 100MB
    - 비동기 백그라운드 처리로 즉시 응답
    """
    try:
        # 파일 내용 읽기
        file_content = await file.read()
        
        # 문서 서비스를 통해 업로드 처리
        response = await document_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        logger.info(f"파일 업로드 요청 완료: {file.filename}")
        return response
        
    except ValueError as e:
        logger.error(f"파일 업로드 검증 실패: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}")


@router.post("/text", response_model=TextInsertResponse)
async def insert_text(request: TextInsertRequest):
    """
    텍스트 직접 삽입
    
    - 파일 없이 텍스트 컨텐츠 직접 처리
    - 백그라운드에서 LightRAG 처리 수행
    """
    try:
        response = await document_service.insert_text(
            content=request.content,
            source_id=request.source_id,
            metadata=request.metadata
        )
        
        logger.info(f"텍스트 삽입 요청 완료: {len(request.content)} 문자")
        return response
        
    except Exception as e:
        logger.error(f"텍스트 삽입 실패: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 삽입 중 오류가 발생했습니다: {str(e)}")


@router.post("/texts", response_model=BatchTextInsertResponse)
async def batch_insert_texts(request: BatchTextInsertRequest):
    """
    다중 텍스트 배치 삽입
    
    - 여러 텍스트를 한 번에 배치 처리
    - 각 텍스트는 독립적으로 처리됨
    """
    try:
        # 요청 데이터를 딕셔너리 형태로 변환
        texts_data = []
        for text_req in request.texts:
            texts_data.append({
                'content': text_req.content,
                'source_id': text_req.source_id,
                'metadata': text_req.metadata
            })
        
        response = await document_service.batch_insert_texts(texts_data)
        
        logger.info(f"배치 텍스트 삽입 완료: {response.success_count}/{response.total_count}")
        return response
        
    except Exception as e:
        logger.error(f"배치 텍스트 삽입 실패: {e}")
        raise HTTPException(status_code=500, detail=f"배치 텍스트 삽입 중 오류가 발생했습니다: {str(e)}")


@router.post("/scan", response_model=ScanDirectoryResponse)
async def scan_directory(request: ScanDirectoryRequest):
    """
    입력 디렉터리 새 문서 스캔 및 처리 시작
    
    - 지정된 디렉터리를 스캔하여 새로운 문서 자동 발견
    - 지원되는 파일 형식만 처리
    - 재귀적 스캔 지원
    """
    try:
        response = await document_service.scan_directory(
            directory_path=request.directory_path,
            recursive=request.recursive,
            extensions=request.extensions
        )
        
        logger.info(f"디렉터리 스캔 완료: {request.directory_path}")
        return response
        
    except Exception as e:
        logger.error(f"디렉터리 스캔 실패: {e}")
        raise HTTPException(status_code=500, detail=f"디렉터리 스캔 중 오류가 발생했습니다: {str(e)}")


@router.get("", response_model=DocumentListResponse)
async def get_documents():
    """
    모든 문서 상태 조회
    
    - PENDING/PROCESSING/PROCESSED/FAILED별 그룹화
    - 각 문서의 메타데이터 포함
    """
    try:
        response = await document_service.get_documents()
        return response
        
    except Exception as e:
        logger.error(f"문서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/status_counts", response_model=DocumentStatusCounts)
async def get_status_counts():
    """
    문서 상태별 개수 통계
    
    - 각 상태별 문서 수량 반환
    - 대시보드 및 모니터링용
    """
    try:
        response = await document_service.get_status_counts()
        return response
        
    except Exception as e:
        logger.error(f"상태 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"상태 통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.delete("/delete_document", response_model=DocumentDeleteResponse)
async def delete_documents(request: DocumentDeleteRequest):
    """
    지정된 문서 ID들 삭제
    
    - 선택된 문서들의 파일, 벡터, 그래프 데이터 일괄 삭제
    - 원본 파일 삭제 여부 선택 가능
    """
    try:
        response = await document_service.delete_documents(
            document_ids=request.document_ids,
            delete_files=request.delete_files
        )
        
        logger.info(f"문서 삭제 완료: {response.deleted_count}개")
        return response
        
    except Exception as e:
        logger.error(f"문서 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 삭제 중 오류가 발생했습니다: {str(e)}")


@router.delete("/clear", response_model=DocumentDeleteResponse)
async def clear_all_documents():
    """
    모든 문서 및 데이터 삭제
    
    - 전체 시스템 데이터 초기화
    - 파일, 벡터 데이터, 그래프 데이터, 캐시 모두 삭제
    """
    try:
        response = await document_service.clear_all_documents()
        
        logger.info("모든 문서 및 데이터 삭제 완료")
        return response
        
    except Exception as e:
        logger.error(f"전체 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"전체 삭제 중 오류가 발생했습니다: {str(e)}")


@router.get("/pipeline_status", response_model=PipelineStatus)
async def get_pipeline_status():
    """
    문서 처리 파이프라인 현재 상태
    
    - 처리 중인 작업, 큐 상태, 진행률 정보
    - 실시간 모니터링용
    """
    try:
        response = await document_service.get_pipeline_status()
        return response
        
    except Exception as e:
        logger.error(f"파이프라인 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파이프라인 상태 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/track_status/{track_id}", response_model=TrackingStatus)
async def get_track_status(track_id: str):
    """
    특정 추적 ID의 처리 상태
    
    - 개별 작업의 상세 진행 상황
    - 오류 메시지 포함
    """
    try:
        response = await document_service.get_track_status(track_id)
        
        if response is None:
            raise HTTPException(status_code=404, detail=f"추적 ID를 찾을 수 없습니다: {track_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"추적 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"추적 상태 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/clear_cache")
async def clear_cache():
    """
    LLM 캐시 데이터 삭제
    
    - 시스템 성능 최적화를 위한 캐시 정리
    - 메모리 및 디스크 공간 확보
    """
    try:
        await document_service.clear_cache()
        
        logger.info("캐시 정리 완료")
        return {"message": "캐시가 성공적으로 정리되었습니다"}
        
    except Exception as e:
        logger.error(f"캐시 정리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 정리 중 오류가 발생했습니다: {str(e)}")


# 헬스 체크 엔드포인트
@router.get("/health")
async def health_check():
    """문서 서비스 헬스 체크"""
    try:
        # 기본적인 서비스 상태 확인
        status_counts = await document_service.get_status_counts()
        
        return {
            "status": "healthy",
            "service": "document_service",
            "total_documents": status_counts.total,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"문서 서비스 헬스 체크 실패: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "document_service",
                "error": str(e)
            }
        )