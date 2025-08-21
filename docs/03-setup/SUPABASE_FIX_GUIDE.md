# Supabase API Key 오류 수정 가이드

## 🚨 현재 문제
- Supabase URL: `yuotzaoriukytwhdgplh.supabase.co`
- API Key가 다른 프로젝트(`efcdjsrumdrhmpinglp`)의 것을 사용 중
- 결과: "Invalid API key" 오류 발생

## 🔧 해결 방법

### 방법 1: 새 API Key 발급 (권장)

1. **Supabase 대시보드 접속**
   - https://supabase.com/dashboard 접속
   - `yuotzaoriukytwhdgplh` 프로젝트 선택

2. **API Keys 확인**
   - 좌측 메뉴에서 `Settings` → `API` 클릭
   - `Project API keys` 섹션에서 다음 키들 복사:
     - `anon` `public` key
     - `service_role` `secret` key

3. **환경 변수 업데이트**
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://yuotzaoriukytwhdgplh.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=새로_발급받은_anon_key
   SUPABASE_SERVICE_ROLE_KEY=새로_발급받은_service_role_key
   ```

### 방법 2: URL 변경 (대안)

현재 API Key가 유효한 프로젝트로 URL 변경:
```env
NEXT_PUBLIC_SUPABASE_URL=https://efcdjsrumdrhmpinglp.supabase.co
# API Key는 그대로 유지
```

## ✅ 수정 후 확인사항

1. 브라우저 개발자 도구에서 네트워크 탭 확인
2. Supabase 요청이 401 오류 없이 성공하는지 확인
3. 회원가입/로그인 테스트

## 🛡️ 보안 주의사항

- API Key를 GitHub에 커밋하지 마세요
- `.env.local` 파일은 `.gitignore`에 포함되어 있어야 합니다
- `service_role` key는 절대 클라이언트 사이드에서 사용하지 마세요