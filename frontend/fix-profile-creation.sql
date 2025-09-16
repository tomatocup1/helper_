-- 프로필 생성 오류 해결을 위한 SQL 스크립트
-- Supabase SQL Editor에서 실행하세요

-- 1. 현재 RLS 정책 확인
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check 
FROM pg_policies 
WHERE tablename = 'users';

-- 2. 현재 users 테이블의 RLS 상태 확인
SELECT schemaname, tablename, rowsecurity, forcerowsecurity 
FROM pg_tables 
WHERE tablename = 'users';

-- 3. 기존 정책 삭제 (있다면)
DROP POLICY IF EXISTS "Users can insert own profile" ON public.users;
DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
DROP POLICY IF EXISTS "Users can update own profile" ON public.users;

-- 4. 새로운 정책 생성
-- 사용자가 자신의 프로필을 삽입할 수 있도록
CREATE POLICY "Users can insert own profile" ON public.users
  FOR INSERT 
  WITH CHECK (auth.uid() = id);

-- 사용자가 자신의 프로필을 조회할 수 있도록  
CREATE POLICY "Users can view own profile" ON public.users
  FOR SELECT 
  USING (auth.uid() = id);

-- 사용자가 자신의 프로필을 업데이트할 수 있도록
CREATE POLICY "Users can update own profile" ON public.users
  FOR UPDATE 
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- 5. RLS 활성화 확인
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- 6. 테스트용 쿼리 (실제 사용자 ID로 테스트)
-- SELECT auth.uid(); -- 현재 사용자 ID 확인
-- SELECT * FROM public.users WHERE id = auth.uid(); -- 자신의 프로필 조회

-- 7. 권한 확인
SELECT 
  table_name,
  privilege_type,
  grantee
FROM information_schema.table_privileges 
WHERE table_name = 'users';

-- 8. 현재 세션 정보 확인
SELECT 
  auth.uid() as user_id,
  auth.role() as role,
  current_user as current_user;