#!/bin/bash

# 우리가게 도우미 프로젝트 설정 스크립트
# 이 스크립트는 개발 환경을 자동으로 설정합니다.

set -e  # 에러 발생시 스크립트 중단

echo "🚀 우리가게 도우미 프로젝트 설정을 시작합니다..."
echo "=================================================="

# ================================
# 필수 도구 확인
# ================================
echo "📋 필수 도구 확인 중..."

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1이 설치되어 있지 않습니다. 설치 후 다시 실행해주세요."
        exit 1
    else
        echo "✅ $1 확인됨"
    fi
}

check_command "python3"
check_command "node"
check_command "npm"
check_command "docker"
check_command "docker-compose"
check_command "git"

# Python 버전 확인
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
REQUIRED_PYTHON="3.11"

if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then 
    echo "❌ Python 3.11 이상이 필요합니다. 현재 버전: $PYTHON_VERSION"
    exit 1
else
    echo "✅ Python 버전 확인됨: $PYTHON_VERSION"
fi

# Node.js 버전 확인
NODE_VERSION=$(node --version | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 18 이상이 필요합니다. 현재 버전: v$NODE_VERSION"
    exit 1
else
    echo "✅ Node.js 버전 확인됨: v$NODE_VERSION"
fi

# ================================
# 환경 변수 파일 생성
# ================================
echo ""
echo "📝 환경 변수 파일 설정 중..."

if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ .env 파일을 생성했습니다."
    echo "⚠️  .env 파일을 편집하여 필요한 환경 변수를 설정해주세요."
    echo "   특히 다음 항목들을 확인해주세요:"
    echo "   - OPENAI_API_KEY: OpenAI API 키"
    echo "   - SUPABASE_URL: Supabase 프로젝트 URL"
    echo "   - SUPABASE_ANON_KEY: Supabase 익명 키"
    echo "   - SUPABASE_SERVICE_KEY: Supabase 서비스 키"
else
    echo "⚠️  .env 파일이 이미 존재합니다."
fi

# ================================
# Python 가상환경 설정
# ================================
echo ""
echo "🐍 Python 가상환경 설정 중..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Python 가상환경이 생성되었습니다."
else
    echo "ℹ️  Python 가상환경이 이미 존재합니다."
fi

# 가상환경 활성화
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || {
    echo "❌ 가상환경 활성화에 실패했습니다."
    exit 1
}
echo "✅ Python 가상환경이 활성화되었습니다."

# ================================
# 디렉토리 구조 생성
# ================================
echo ""
echo "📁 프로젝트 디렉토리 구조 생성 중..."

# 백엔드 디렉토리
mkdir -p backend/{server-a,server-b,server-c,shared}/{app,tests}
mkdir -p backend/shared/{database,external,utils,schemas}

# 프론트엔드 디렉토리  
mkdir -p frontend/src/{app,components,lib,hooks,stores,types}
mkdir -p admin/src/{app,components,lib,hooks,stores,types}

# 기타 디렉토리
mkdir -p database/{migrations,seeds,schemas}
mkdir -p docs
mkdir -p logs
mkdir -p uploads

echo "✅ 디렉토리 구조가 생성되었습니다."

# ================================
# Docker 환경 준비
# ================================
echo ""
echo "🐳 Docker 환경 준비 중..."

# Docker 네트워크 생성 (이미 존재할 수 있음)
docker network create storehelper-network 2>/dev/null || echo "ℹ️  Docker 네트워크가 이미 존재합니다."

# Docker 이미지 풀
echo "📦 Docker 이미지 다운로드 중..."
docker-compose pull postgres redis

echo "✅ Docker 환경이 준비되었습니다."

# ================================
# 기본 서비스 시작
# ================================
echo ""
echo "🚀 기본 서비스 시작 중..."

# PostgreSQL과 Redis 시작
docker-compose up -d postgres redis

# 서비스가 준비될 때까지 대기
echo "⏳ 데이터베이스 서비스 준비 대기 중..."
sleep 15

# PostgreSQL 연결 확인
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL이 준비되었습니다."
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL 연결 시간 초과"
        exit 1
    fi
    sleep 2
done

# Redis 연결 확인
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis가 준비되었습니다."
else
    echo "❌ Redis 연결 실패"
    exit 1
fi

# ================================
# 프로젝트별 설정 파일 생성
# ================================
echo ""
echo "📄 프로젝트 설정 파일 생성 중..."

# 각 백엔드 서버별 requirements.txt 생성 (기본)
cat > backend/server-a/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
playwright==1.40.0
openai==1.3.0
celery==5.3.4
redis==5.0.1
asyncpg==0.29.0
sqlalchemy==2.0.23
python-decouple==3.8
httpx==0.25.2
pydantic==2.5.0
python-multipart==0.0.6
EOF

cat > backend/server-b/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
supabase==2.0.0
sqlalchemy==2.0.23
asyncpg==0.29.0
redis==5.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic==2.5.0
python-decouple==3.8
httpx==0.25.2
EOF

cat > backend/server-c/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
celery==5.3.4
redis==5.0.1
asyncpg==0.29.0
sqlalchemy==2.0.23
python-decouple==3.8
smtplib
httpx==0.25.2
pydantic==2.5.0
flower==2.0.1
EOF

echo "✅ 기본 requirements.txt 파일들이 생성되었습니다."

# ================================
# 권한 설정
# ================================
echo ""
echo "🔐 스크립트 권한 설정 중..."

chmod +x scripts/*.sh 2>/dev/null || true
echo "✅ 스크립트 실행 권한이 설정되었습니다."

# ================================
# 완료 메시지
# ================================
echo ""
echo "=================================================="
echo "✅ 프로젝트 설정이 완료되었습니다!"
echo "=================================================="
echo ""
echo "다음 단계:"
echo "1. .env 파일을 편집하여 API 키들을 설정하세요"
echo "2. 다음 명령어로 전체 서비스를 시작할 수 있습니다:"
echo "   docker-compose up -d"
echo ""
echo "3. 또는 개별 서비스를 개발 모드로 실행:"
echo "   # 백엔드 개발"
echo "   source venv/bin/activate  # Windows: venv\\Scripts\\activate"
echo "   cd backend/server-b && pip install -r requirements.txt"
echo "   uvicorn app.main:app --reload"
echo ""
echo "   # 프론트엔드 개발"
echo "   cd frontend && npm install && npm run dev"
echo ""
echo "4. 서비스 URL:"
echo "   - 프론트엔드: http://localhost:3000"
echo "   - API 서버: http://localhost:8000"
echo "   - 관리자 대시보드: http://localhost:3001"
echo "   - API 문서: http://localhost:8000/docs"
echo ""
echo "도움이 필요하시면 README.md를 확인하세요!"
echo "=================================================="