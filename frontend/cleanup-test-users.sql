-- 테스트 사용자 정리 스크립트
-- ⚠️ 주의: 이 스크립트는 테스트 환경에서만 사용하세요!

-- 1. public.users 테이블에서 테스트 계정 삭제
DELETE FROM public.users 
WHERE email LIKE 'test%@example.com';

-- 2. auth.users 테이블에서 테스트 계정 삭제
DELETE FROM auth.users 
WHERE email LIKE 'test%@example.com';

-- 3. 정리 결과 확인
SELECT 'Remaining auth users:' as info, count(*) as count FROM auth.users
UNION ALL
SELECT 'Remaining public users:' as info, count(*) as count FROM public.users;

-- 4. 특정 사용자 확인 (필요시)
-- SELECT id, email, email_confirmed_at, created_at 
-- FROM auth.users 
-- WHERE email = 'your-email@example.com';