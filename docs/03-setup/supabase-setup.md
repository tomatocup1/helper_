# 📚 Supabase 설정 가이드

## 🎯 Supabase 프로젝트 생성 및 설정

### 1. Supabase 프로젝트 생성
1. [Supabase](https://supabase.com) 접속 후 로그인
2. "New Project" 클릭
3. 프로젝트 정보 입력:
   - Project name: `store-helper` (또는 원하는 이름)
   - Database password: 강력한 비밀번호 생성
   - Region: `Northeast Asia (Seoul)` 선택 (한국 서비스용)
4. "Create new project" 클릭

### 2. 환경 변수 설정
프로젝트 생성 후, Settings > API 메뉴에서:

```bash
# .env.local 파일에 복사
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 3. 데이터베이스 스키마 실행
1. Supabase Dashboard > SQL Editor 접속
2. `/database/schema.sql` 파일 내용을 복사
3. SQL Editor에 붙여넣기 후 실행

### 4. Authentication 설정

#### Email 인증 설정
1. Authentication > Providers > Email 활성화
2. Settings:
   - Enable Email Confirmations: ON (프로덕션)
   - Enable Email Confirmations: OFF (개발 중)

#### 이메일 템플릿 커스터마이징 (선택사항)
Authentication > Email Templates에서 한국어로 수정:

**회원가입 확인 이메일:**
```html
<h2>우리가게 도우미 회원가입을 환영합니다!</h2>
<p>안녕하세요 {{ .Email }}님,</p>
<p>아래 버튼을 클릭하여 이메일 인증을 완료해주세요:</p>
<a href="{{ .ConfirmationURL }}">이메일 인증하기</a>
```

**비밀번호 재설정 이메일:**
```html
<h2>비밀번호 재설정</h2>
<p>안녕하세요 {{ .Email }}님,</p>
<p>아래 버튼을 클릭하여 비밀번호를 재설정하세요:</p>
<a href="{{ .ConfirmationURL }}">비밀번호 재설정</a>
```

### 5. Row Level Security (RLS) 확인
데이터베이스의 RLS 정책이 자동으로 적용되었는지 확인:

1. Table Editor > 각 테이블 선택
2. RLS 활성화 여부 확인
3. Policies 탭에서 정책 확인

### 6. Storage 설정 (선택사항)
프로필 이미지 등을 저장할 경우:

1. Storage > New Bucket 생성
   - Name: `avatars`
   - Public: ON
2. Policies 설정:
   ```sql
   -- 사용자가 자신의 아바타를 업로드할 수 있도록
   CREATE POLICY "Users can upload own avatar"
   ON storage.objects FOR INSERT
   WITH CHECK (bucket_id = 'avatars' AND auth.uid()::text = (storage.foldername(name))[1]);
   ```

## 🚀 로컬 개발 환경 실행

### 1. 의존성 설치
```bash
cd frontend
npm install
```

### 2. 환경 변수 설정
`.env.local` 파일에 Supabase 정보 입력:
```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

### 3. 개발 서버 실행
```bash
npm run dev
```

### 4. 테스트 계정 생성
1. http://localhost:3000/register 접속
2. 테스트 계정 정보 입력:
   - 이메일: test@example.com
   - 비밀번호: test123456
   - 이름: 테스트 사장님
   - 전화번호: 010-1234-5678
   - 사업자등록번호: 123-45-67890

## 🔍 문제 해결

### 로그인이 안 되는 경우
1. Supabase Dashboard > Authentication > Users 확인
2. 사용자가 생성되었는지 확인
3. Email 인증이 필요한 경우, 인증 메일 확인

### CORS 에러가 발생하는 경우
1. Supabase Dashboard > Settings > API
2. CORS 설정에 `http://localhost:3000` 추가

### 데이터베이스 연결 오류
1. `.env.local` 파일의 URL과 KEY 확인
2. Supabase 프로젝트가 활성화되어 있는지 확인
3. RLS 정책이 올바르게 설정되었는지 확인

## 📊 데이터베이스 모니터링

### SQL 쿼리 실행
Supabase Dashboard > SQL Editor에서 직접 쿼리 실행:
```sql
-- 사용자 목록 조회
SELECT * FROM users;

-- 매장 목록 조회
SELECT * FROM platform_stores WHERE user_id = 'user-uuid';

-- 리뷰 통계
SELECT 
  COUNT(*) as total_reviews,
  AVG(rating) as average_rating
FROM reviews_naver;
```

### 실시간 로그
Supabase Dashboard > Logs에서 실시간 로그 확인 가능

## 🚨 프로덕션 체크리스트

### 보안
- [ ] 강력한 데이터베이스 비밀번호 설정
- [ ] RLS 정책 모두 활성화
- [ ] API 키 환경 변수로 관리
- [ ] CORS 설정 확인

### 성능
- [ ] 인덱스 최적화
- [ ] 쿼리 성능 모니터링
- [ ] 캐싱 전략 수립

### 백업
- [ ] 자동 백업 설정
- [ ] 복구 계획 수립

## 📚 참고 자료
- [Supabase 공식 문서](https://supabase.com/docs)
- [Next.js + Supabase 가이드](https://supabase.com/docs/guides/getting-started/quickstarts/nextjs)
- [Supabase Auth 문서](https://supabase.com/docs/guides/auth)