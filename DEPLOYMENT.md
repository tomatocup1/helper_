# 🚀 배포 가이드 - Render + Vercel

우리가게 도우미를 Render(백엔드) + Vercel(프론트엔드)에 배포하는 완전 가이드입니다.

## 📋 배포 아키텍처

```
[Vercel Frontend] ⟷ [Render Backend] ⟷ [Supabase Database]
   (Next.js)           (FastAPI)           (PostgreSQL)
```

## 🏗️ 1. Render 백엔드 배포

### 1.1 GitHub 연결
1. GitHub에 코드 푸시
2. [Render.com](https://render.com) 로그인
3. "New +" → "Web Service" 선택
4. GitHub 저장소 연결

### 1.2 Render 서비스 설정
```yaml
Name: store-helper-backend
Language: Docker
Branch: main (또는 master)
Root Directory: backend
Dockerfile Path: ./Dockerfile
```

### 1.3 환경변수 설정 (Render Dashboard)
```bash
# 필수 환경변수
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_api_key

# 플랫폼별 암호화 키 (32자리 랜덤 문자열)
NAVER_ENCRYPTION_KEY=your_32_char_random_string
BAEMIN_ENCRYPTION_KEY=your_32_char_random_string
COUPANGEATS_ENCRYPTION_KEY=your_32_char_random_string
YOGIYO_ENCRYPTION_KEY=your_32_char_random_string

# 시스템 환경변수
PYTHONPATH=/app
PYTHONIOENCODING=utf-8
PYTHONUTF8=1
```

### 1.4 Render 플랜 선택
- **Starter Plan**: $7/month (권장)
- CPU: 0.1 vCPU, RAM: 512MB
- Playwright 브라우저 실행 가능

## 🌐 2. Vercel 프론트엔드 배포

### 2.1 Vercel 프로젝트 생성
1. [Vercel.com](https://vercel.com) 로그인
2. "Add New..." → "Project" 선택
3. GitHub 저장소 import

### 2.2 Vercel 프로젝트 설정
```yaml
Framework Preset: Next.js
Root Directory: frontend
Build Command: npm run build
Output Directory: .next
Install Command: npm install
```

### 2.3 환경변수 설정 (Vercel Dashboard)
```bash
# Supabase 설정
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# API 백엔드 URL (Render 배포 후 받은 URL)
NEXT_PUBLIC_API_URL=https://store-helper-backend-xxxx.onrender.com/api
```

## 🔐 3. 환경변수 상세 가이드

### 3.1 Supabase 키 확인
1. [Supabase Dashboard](https://supabase.com/dashboard) 접속
2. 프로젝트 → Settings → API
3. **URL**, **anon public**, **service_role secret** 복사

### 3.2 OpenAI API 키
1. [OpenAI Platform](https://platform.openai.com/api-keys) 접속
2. "Create new secret key" 클릭
3. 키 복사 후 안전하게 보관

### 3.3 암호화 키 생성
```python
import secrets
print(secrets.token_urlsafe(24))  # 32자리 랜덤 문자열
```

## 🚀 4. 배포 실행 순서

### 단계별 배포 프로세스

1. **GitHub 푸시**
   ```bash
   git add .
   git commit -m "Deploy: Add Render and Vercel configurations"
   git push origin main
   ```

2. **Render 백엔드 배포**
   - render.yaml 설정으로 자동 배포
   - 빌드 시간: 약 10-15분 (Playwright 설치 포함)
   - 배포 URL 확인: `https://store-helper-backend-xxxx.onrender.com`

3. **Vercel 프론트엔드 배포**
   - vercel.json 설정으로 자동 배포
   - Render URL을 NEXT_PUBLIC_API_URL에 설정
   - 빌드 시간: 약 3-5분

## 🔧 5. 배포 후 확인사항

### 5.1 백엔드 헬스체크
```bash
curl https://store-helper-backend-xxxx.onrender.com/health
# 응답: {"status": "healthy"}
```

### 5.2 프론트엔드 접속 확인
- Vercel URL 접속
- 로그인 페이지 정상 로드 확인
- Supabase 인증 연동 확인

### 5.3 크롤러 동작 확인
- 플랫폼 스토어 등록
- 리뷰 크롤링 테스트
- AI 답글 생성 테스트

## 🐛 6. 트러블슈팅

### 6.1 Render 빌드 실패
```bash
# 로그 확인 포인트
- Dockerfile 경로 정확성
- requirements.txt 의존성
- Playwright 브라우저 설치 완료
```

### 6.2 Vercel 빌드 실패
```bash
# 일반적인 해결법
- Node.js 버전 확인 (18.x 권장)
- package.json 의존성 업데이트
- TypeScript 에러 해결
```

### 6.3 CORS 에러
백엔드에서 프론트엔드 도메인 허용 설정:
```python
# server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-vercel-app.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 💰 7. 예상 비용

### 월간 운영비용
- **Render Starter**: $7/month
- **Vercel Pro**: $20/month (팀 사용시)
- **Vercel Hobby**: $0/month (개인 사용)
- **Supabase Pro**: $25/month (DB 용량에 따라)

**총 비용**: $32-52/month

## 📞 8. 배포 지원

배포 중 문제가 발생하면:
1. 에러 로그 스크린샷 첨부
2. 배포 환경 (Render/Vercel) 명시
3. 구체적인 에러 메시지 공유

---

## 🎯 배포 체크리스트

- [ ] GitHub 저장소 생성 및 코드 푸시
- [ ] Render 서비스 생성 및 환경변수 설정
- [ ] Vercel 프로젝트 생성 및 환경변수 설정
- [ ] 백엔드 헬스체크 통과
- [ ] 프론트엔드 정상 접속
- [ ] 크롤러 동작 테스트
- [ ] AI 답글 생성 테스트
- [ ] 프로덕션 환경 모니터링 설정

**배포 완료 후 실제 사용자 테스트를 진행하세요!** 🎉