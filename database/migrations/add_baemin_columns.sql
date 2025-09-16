-- ============================================
-- 배달의민족 매장 등록 기능을 위한 스키마 확장
-- ============================================

-- platform_stores 테이블에 배민 전용 컬럼 추가
ALTER TABLE platform_stores 
ADD COLUMN IF NOT EXISTS sub_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS baemin_session_active BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS baemin_last_login TIMESTAMP WITH TIME ZONE;

-- 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_platform_stores_sub_type ON platform_stores(sub_type);
CREATE INDEX IF NOT EXISTS idx_platform_stores_baemin_session_active ON platform_stores(baemin_session_active);
CREATE INDEX IF NOT EXISTS idx_platform_stores_baemin_last_login ON platform_stores(baemin_last_login);

-- 복합 인덱스 (배민 관련 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_platform_stores_baemin_platform ON platform_stores(platform, baemin_session_active) 
WHERE platform = 'baemin';

-- 컬럼 코멘트 추가
COMMENT ON COLUMN platform_stores.sub_type IS '플랫폼별 서브 타입 (배민: [음식배달], [포장] 등)';
COMMENT ON COLUMN platform_stores.baemin_session_active IS '배달의민족 세션 활성 상태';
COMMENT ON COLUMN platform_stores.baemin_last_login IS '배달의민족 마지막 로그인 시간';

-- 배민 매장 조회용 뷰 생성
CREATE OR REPLACE VIEW baemin_stores AS
SELECT 
    id,
    user_id,
    store_name,
    business_type,
    sub_type,
    platform_store_id,
    platform_url,
    is_active,
    is_verified,
    baemin_session_active,
    baemin_last_login,
    created_at,
    updated_at
FROM platform_stores 
WHERE platform = 'baemin';

-- 뷰에 대한 코멘트
COMMENT ON VIEW baemin_stores IS '배달의민족 매장 정보 조회용 뷰';

-- 데이터 검증 함수 생성
CREATE OR REPLACE FUNCTION validate_baemin_store_data()
RETURNS TRIGGER AS $
BEGIN
    -- 배민 플랫폼인 경우에만 검증
    IF NEW.platform = 'baemin' THEN
        -- platform_store_id가 숫자인지 확인
        IF NEW.platform_store_id IS NOT NULL AND NEW.platform_store_id !~ '^[0-9]+$' THEN
            RAISE EXCEPTION 'Invalid baemin store ID format: %', NEW.platform_store_id;
        END IF;
        
        -- sub_type이 배민 형식인지 확인
        IF NEW.sub_type IS NOT NULL AND NEW.sub_type !~ '^\[.+\]$' THEN
            RAISE EXCEPTION 'Invalid baemin sub_type format: %', NEW.sub_type;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- 트리거 생성
CREATE TRIGGER validate_baemin_store_data_trigger
    BEFORE INSERT OR UPDATE ON platform_stores
    FOR EACH ROW
    EXECUTE FUNCTION validate_baemin_store_data();

-- 배민 매장 등록 함수 생성
CREATE OR REPLACE FUNCTION register_baemin_store(
    p_user_id UUID,
    p_store_name VARCHAR(200),
    p_business_type VARCHAR(50),
    p_sub_type VARCHAR(50),
    p_platform_store_id VARCHAR(100),
    p_platform_url TEXT DEFAULT NULL
)
RETURNS UUID AS $
DECLARE
    new_store_id UUID;
BEGIN
    INSERT INTO platform_stores (
        user_id,
        store_name,
        business_type,
        sub_type,
        platform,
        platform_store_id,
        platform_url,
        is_active,
        crawling_enabled,
        auto_reply_enabled
    ) VALUES (
        p_user_id,
        p_store_name,
        p_business_type,
        p_sub_type,
        'baemin',
        p_platform_store_id,
        p_platform_url,
        true,
        true,
        false  -- 배민은 기본적으로 자동 답글 비활성화
    )
    ON CONFLICT (user_id, platform, platform_store_id) 
    DO UPDATE SET
        store_name = EXCLUDED.store_name,
        business_type = EXCLUDED.business_type,
        sub_type = EXCLUDED.sub_type,
        platform_url = EXCLUDED.platform_url,
        updated_at = NOW()
    RETURNING id INTO new_store_id;
    
    RETURN new_store_id;
END;
$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION register_baemin_store IS '배달의민족 매장 등록/업데이트 함수 (중복 방지 포함)';

-- 배민 세션 관리 함수
CREATE OR REPLACE FUNCTION update_baemin_session(
    p_user_id UUID,
    p_is_active BOOLEAN DEFAULT TRUE
)
RETURNS INTEGER AS $
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE platform_stores 
    SET 
        baemin_session_active = p_is_active,
        baemin_last_login = CASE WHEN p_is_active THEN NOW() ELSE baemin_last_login END,
        updated_at = NOW()
    WHERE user_id = p_user_id 
    AND platform = 'baemin';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION update_baemin_session IS '배달의민족 세션 상태 업데이트 함수';

-- 샘플 데이터 (테스트용 - 주석 처리)
/*
-- 테스트용 샘플 데이터
INSERT INTO platform_stores (
    user_id,
    store_name,
    business_type,
    sub_type,
    platform,
    platform_store_id,
    platform_url,
    is_active
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000', -- 실제 user_id로 변경 필요
    '더클램스 & 화채꽃이야기',
    '카페·디저트',
    '[음식배달]',
    'baemin',
    '14522306',
    'https://www.baemin.com/shop/info/14522306',
    true
) ON CONFLICT (user_id, platform, platform_store_id) DO NOTHING;
*/

-- 마이그레이션 완료 확인
SELECT 'Baemin columns and functions created successfully!' as migration_status;