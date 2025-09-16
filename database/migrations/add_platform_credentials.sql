-- 매장 관리 시스템: platform_stores 테이블 확장
-- 범용 플랫폼 계정 정보 필드 추가

-- platform_id와 platform_password_encrypted 컬럼 추가
ALTER TABLE platform_stores 
ADD COLUMN IF NOT EXISTS platform_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS platform_password_encrypted TEXT;

-- 기존 naver_id를 platform_id로 마이그레이션 (데이터가 있는 경우)
UPDATE platform_stores 
SET platform_id = naver_id 
WHERE naver_id IS NOT NULL AND platform_id IS NULL;

-- 기존 naver_password_encrypted를 platform_password_encrypted로 마이그레이션
UPDATE platform_stores 
SET platform_password_encrypted = naver_password_encrypted 
WHERE naver_password_encrypted IS NOT NULL AND platform_password_encrypted IS NULL;

-- 인덱스 추가 (성능 향상)
CREATE INDEX IF NOT EXISTS idx_platform_stores_platform_id ON platform_stores(platform_id);
CREATE INDEX IF NOT EXISTS idx_platform_stores_platform_user ON platform_stores(platform, user_id);

-- 코멘트 추가
COMMENT ON COLUMN platform_stores.platform_id IS '플랫폼별 로그인 아이디 (이메일 또는 아이디)';
COMMENT ON COLUMN platform_stores.platform_password_encrypted IS '암호화된 플랫폼 비밀번호';

-- 향후 네이버 특화 필드들을 범용으로 활용할 수 있도록 준비
-- naver_session_active -> platform_session_active로 활용 가능
-- naver_last_login -> platform_last_login으로 활용 가능