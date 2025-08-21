# Supabase 설정 가이드

## 🚨 중요: 인증 문제 해결을 위한 설정

현재 "Invalid login credentials" 오류가 발생하는 이유는 Supabase에서 이메일 확인이 활성화되어 있기 때문입니다.

## 🔧 Supabase 대시보드 설정 변경

### 1. Supabase 대시보드 접속
- URL: https://supabase.com/dashboard
- 프로젝트: `yuotzaoriukytwhdgplh`

### 2. Authentication 설정 변경
1. **왼쪽 메뉴에서 "Authentication" 클릭**
2. **"Settings" 탭 클릭**
3. **"User Signups" 섹션에서 다음 설정:**
   - ✅ `Enable email confirmations` → **OFF로 변경**
   - ✅ `Enable custom SMTP` → OFF 유지
   - ✅ `Confirm Email` → **OFF로 변경**

### 3. Row Level Security (RLS) 정책 확인
1. **왼쪽 메뉴에서 "Database" → "Tables" 클릭**
2. **`users` 테이블 클릭**
3. **RLS 정책 확인:**
   ```sql
   -- 사용자가 자신의 데이터만 읽을 수 있도록
   CREATE POLICY "Users can view own profile" ON users
   FOR SELECT USING (auth.uid() = id);

   -- 사용자가 자신의 데이터를 업데이트할 수 있도록
   CREATE POLICY "Users can update own profile" ON users
   FOR UPDATE USING (auth.uid() = id);

   -- 새 사용자 생성 허용
   CREATE POLICY "Users can insert own profile" ON users
   FOR INSERT WITH CHECK (auth.uid() = id);
   ```

### 4. Auth 스키마 확인
SQL Editor에서 다음 쿼리 실행하여 사용자 테이블 상태 확인:

```sql
-- 모든 사용자 확인
SELECT id, email, email_confirmed_at, created_at FROM auth.users;

-- public.users 테이블 확인
SELECT * FROM public.users;
```

## 🧪 테스트 순서

### 1. 새로운 계정으로 회원가입
```
이메일: test3@example.com
비밀번호: test123456
이름: 테스트사장님3
```

### 2. 즉시 로그인 시도
- 회원가입 후 같은 계정으로 바로 로그인 시도
- 콘솔에서 자세한 로그 확인

### 3. 데이터베이스 확인
```sql
-- 방금 생성한 사용자 확인
SELECT * FROM auth.users WHERE email = 'test3@example.com';
SELECT * FROM public.users WHERE email = 'test3@example.com';
```

## 🔍 디버깅 정보

회원가입/로그인 시 브라우저 개발자 도구의 Console 탭에서 다음 로그들을 확인하세요:

- `Attempting signup with:` - 회원가입 시도 정보
- `Signup result:` - Supabase 응답
- `User created:` - 생성된 사용자 정보
- `Email confirmed:` - 이메일 확인 상태
- `Profile created successfully` - 프로필 생성 성공 여부

## 🚨 문제 해결

### 여전히 "Invalid login credentials" 오류가 발생하는 경우:

1. **이메일 확인 설정이 완전히 비활성화되었는지 확인**
2. **기존 테스트 계정 삭제 후 새 계정으로 재시도**
3. **Supabase 프로젝트가 올바른 환경(Production)에 있는지 확인**

### SQL 쿼리로 기존 테스트 계정 삭제:
```sql
-- 주의: 테스트 환경에서만 사용
DELETE FROM public.users WHERE email LIKE 'test%@example.com';
DELETE FROM auth.users WHERE email LIKE 'test%@example.com';
```

## 📞 추가 지원

문제가 계속 발생하면 다음 정보를 공유해주세요:
1. Supabase 대시보드의 Authentication 설정 스크린샷
2. 브라우저 Console의 전체 오류 로그
3. Network 탭에서 `/auth/` API 요청의 응답 내용