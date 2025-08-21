# 우리가게 도우미 - 설정 가이드

## 🚀 빠른 시작

### 1. 환경 변수 설정

프론트엔드 `.env.local` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# .env.local 파일
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# 32자리 암호화 키 생성 (중요!)
ENCRYPTION_KEY=your-32-character-secret-key-here!

NODE_ENV=development
```

### 2. Python 환경 설정 (백엔드 크롤러)

```bash
# 1. 백엔드 디렉토리로 이동
cd C:\helper\store-helper-project\backend

# 2. Python 의존성 설치
python setup.py

# 또는 수동 설치:
pip install -r requirements.txt
python -m playwright install
```

### 3. 데이터베이스 마이그레이션

Supabase 대시보드에서 SQL 에디터를 열고 다음 마이그레이션을 실행하세요:

```sql
-- platform_stores 테이블에 크롤링 필드 추가
ALTER TABLE platform_stores 
ADD COLUMN IF NOT EXISTS platform_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS platform_password_encrypted TEXT;

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_platform_stores_platform_id ON platform_stores(platform_id);
CREATE INDEX IF NOT EXISTS idx_platform_stores_platform_user ON platform_stores(platform, user_id);
```

### 4. 프론트엔드 서버 시작

```bash
cd C:\helper\store-helper-project\frontend
npm run dev
```

서버가 http://localhost:3000에서 실행됩니다.

## 🛠️ 매장 관리 시스템 사용법

### 매장 추가 프로세스

1. **로그인** → 대시보드 접속
2. **매장 관리** 메뉴 클릭
3. **매장 추가** 버튼 클릭
4. **3단계 프로세스 진행:**
   - **Step 1:** 플랫폼 선택 (네이버, 배민, 요기요, 쿠팡이츠)
   - **Step 2:** 계정 정보 입력 (암호화되어 안전하게 저장)
   - **Step 3:** 자동 매장 수집 및 등록

### 지원되는 플랫폼

- ✅ **네이버 플레이스** - 완전 구현
- 🚧 **배달의민족** - 테스트 모드
- 🚧 **요기요** - 테스트 모드  
- 🚧 **쿠팡이츠** - 테스트 모드

## 🔧 기술 구조

### API 엔드포인트

- `POST /api/v1/platform/connect` - 플랫폼 계정 연결 및 매장 수집

### 보안 기능

- **계정 정보 암호화**: AES-256-GCM 암호화로 안전한 저장
- **사용자 인증**: Supabase Auth 기반 인증
- **데이터 격리**: RLS(Row Level Security)로 사용자별 데이터 보호

### 크롤링 시스템

- **Playwright 기반**: 안정적인 브라우저 자동화
- **헤드리스 모드**: 서버에서 백그라운드 실행
- **오류 복구**: 로그인 실패, 네트워크 오류 등 자동 처리
- **타임아웃 관리**: 60초 타임아웃으로 무한 대기 방지

## 🚨 문제 해결

### 자주 발생하는 문제

1. **Python 모듈을 찾을 수 없음**
   ```bash
   pip install playwright
   python -m playwright install
   ```

2. **암호화 키 오류**
   - `.env.local`에 32자리 `ENCRYPTION_KEY` 확인

3. **Supabase 연결 오류**
   - Supabase URL과 키가 올바른지 확인
   - 서비스 역할 키 권한 확인

4. **크롤링 실패**
   - 네이버 계정 정보 확인
   - 2단계 인증 비활성화 권장
   - VPN 사용 시 해제

### 로그 확인

- **브라우저 개발자 도구**: 프론트엔드 오류
- **터미널/콘솔**: Next.js 서버 로그
- **Supabase 대시보드**: 데이터베이스 오류

## 📝 개발 참고사항

### 프로젝트 구조
```
store-helper-project/
├── frontend/           # Next.js 애플리케이션
│   ├── src/app/api/    # API 라우트
│   ├── src/components/ # UI 컴포넌트
│   └── src/store/      # 상태 관리
├── backend/            # Python 크롤러
│   ├── scripts/        # 크롤링 스크립트
│   └── requirements.txt
└── database/           # DB 마이그레이션
```

### 추가 개발 포인트

1. **배민/요기요/쿠팡이츠 크롤러 구현**
2. **리뷰 자동 답글 기능**
3. **대시보드 통계 및 분석**
4. **알림 시스템**
5. **모바일 앱 확장**

## 💡 팁

- 네이버 플레이스 관리자 센터에서 매장 등록 상태를 미리 확인하세요
- 크롤링은 적당한 간격으로 실행하여 차단을 방지하세요
- 개발 중에는 테스트 계정을 사용하는 것을 권장합니다

---

문제가 발생하면 GitHub Issues나 개발팀에 문의해주세요! 🚀