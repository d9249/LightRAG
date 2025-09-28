#!/bin/bash

# LightRAG Documents API 실행 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로고 출력
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    LightRAG Documents API                    ║"
echo "║                3-Tier Architecture System                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 함수 정의
print_step() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Docker 및 Docker Compose 확인
check_docker() {
    print_step "Docker 환경 확인 중..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker가 설치되어 있지 않습니다."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose가 설치되어 있지 않습니다."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker 데몬이 실행되고 있지 않습니다."
        exit 1
    fi
    
    print_success "Docker 환경 확인 완료"
}

# 환경 설정 확인
check_environment() {
    print_step "환경 설정 확인 중..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env 파일이 없습니다. 기본 설정을 사용합니다."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success ".env 파일을 생성했습니다."
        fi
    fi
    
    # 필요한 디렉터리 생성
    mkdir -p data/{inputs,rag_storage,vector_storage,graph_storage,document_status,cache,logs}
    print_success "데이터 디렉터리 확인 완료"
}

# 서비스 시작
start_services() {
    print_step "서비스 시작 중..."
    
    # 이전 컨테이너 정리
    docker-compose down 2>/dev/null || true
    
    # 서비스 시작
    docker-compose up -d
    
    print_success "서비스가 시작되었습니다."
}

# 서비스 상태 확인
check_services() {
    print_step "서비스 상태 확인 중..."
    
    # 서비스가 완전히 시작될 때까지 대기
    echo "서비스 시작을 기다리는 중..."
    sleep 10
    
    # 각 서비스 상태 확인
    services=("lightrag-documents-api" "lightrag-neo4j" "lightrag-ollama")
    
    for service in "${services[@]}"; do
        if docker-compose ps | grep -q "$service.*Up"; then
            print_success "$service: 실행 중"
        else
            print_error "$service: 실행되지 않음"
            docker-compose logs "$service"
        fi
    done
}

# API 테스트
test_api() {
    print_step "API 연결 테스트 중..."
    
    # API가 준비될 때까지 대기 (최대 60초)
    timeout=60
    counter=0
    
    while [ $counter -lt $timeout ]; do
        if curl -s http://localhost:9621/health > /dev/null 2>&1; then
            print_success "API 서버가 정상적으로 응답합니다."
            break
        fi
        
        echo -n "."
        sleep 2
        counter=$((counter + 2))
    done
    
    if [ $counter -ge $timeout ]; then
        print_error "API 서버가 응답하지 않습니다."
        print_step "로그를 확인하세요: docker-compose logs lightrag-documents-api"
        return 1
    fi
}

# 사용법 출력
show_usage() {
    echo
    print_step "사용법:"
    echo "  $0 [command]"
    echo
    echo "Commands:"
    echo "  start     - 서비스 시작 (기본)"
    echo "  stop      - 서비스 중지"
    echo "  restart   - 서비스 재시작"
    echo "  status    - 서비스 상태 확인"
    echo "  logs      - 로그 확인"
    echo "  test      - API 테스트"
    echo "  clean     - 모든 데이터 정리"
    echo "  help      - 도움말"
    echo
}

# 메인 함수
main() {
    case "${1:-start}" in
        "start")
            check_docker
            check_environment
            start_services
            check_services
            test_api
            
            echo
            print_success "LightRAG Documents API가 성공적으로 시작되었습니다!"
            echo
            echo "🌐 서비스 URL:"
            echo "  • API 문서: http://localhost:9621/docs"
            echo "  • API 서버: http://localhost:9621"
            echo "  • Neo4j 브라우저: http://localhost:7474"
            echo
            echo "📋 유용한 명령어:"
            echo "  • 로그 확인: docker-compose logs -f"
            echo "  • 서비스 중지: $0 stop"
            echo "  • API 테스트: python test_api.py"
            ;;
            
        "stop")
            print_step "서비스 중지 중..."
            docker-compose down
            print_success "서비스가 중지되었습니다."
            ;;
            
        "restart")
            print_step "서비스 재시작 중..."
            docker-compose down
            sleep 2
            docker-compose up -d
            print_success "서비스가 재시작되었습니다."
            ;;
            
        "status")
            print_step "서비스 상태:"
            docker-compose ps
            ;;
            
        "logs")
            print_step "로그 확인 (Ctrl+C로 종료):"
            docker-compose logs -f
            ;;
            
        "test")
            if command -v python3 &> /dev/null; then
                python3 test_api.py
            elif command -v python &> /dev/null; then
                python test_api.py
            else
                print_error "Python이 설치되어 있지 않습니다."
                exit 1
            fi
            ;;
            
        "clean")
            print_warning "모든 데이터가 삭제됩니다. 계속하시겠습니까? (y/N)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                print_step "데이터 정리 중..."
                docker-compose down -v
                docker system prune -f
                rm -rf data/*
                print_success "모든 데이터가 정리되었습니다."
            else
                print_step "취소되었습니다."
            fi
            ;;
            
        "help"|"-h"|"--help")
            show_usage
            ;;
            
        *)
            print_error "알 수 없는 명령어: $1"
            show_usage
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"