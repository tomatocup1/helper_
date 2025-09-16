-- ============================================
-- 쿠팡잇츠 매장 등록 기능을 위한 스키마 확장
-- ============================================

-- platform_stores 테이블에 쿠팡잇츠 전용 컬럼 추가
ALTER TABLE platform_stores 
ADD COLUMN IF NOT EXISTS coupangeats_session_active BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS coupangeats_last_login TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS coupangeats_store_names JSONB DEFAULT '[]'::jsonb; -- 복수 매장 지원

-- 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_platform_stores_coupangeats_session_active ON platform_stores(coupangeats_session_active);
CREATE INDEX IF NOT EXISTS idx_platform_stores_coupangeats_last_login ON platform_stores(coupangeats_last_login);

-- 복합 인덱스 (쿠팡잇츠 관련 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_platform_stores_coupangeats_platform ON platform_stores(platform, coupangeats_session_active) 
WHERE platform = 'coupangeats';

-- JSONB 인덱스 (매장명 검색용)
CREATE INDEX IF NOT EXISTS idx_platform_stores_coupangeats_store_names ON platform_stores USING GIN (coupangeats_store_names);

-- 컬럼 코멘트 추가
COMMENT ON COLUMN platform_stores.coupangeats_session_active IS '쿠팡잇츠 세션 활성 상태';
COMMENT ON COLUMN platform_stores.coupangeats_last_login IS '쿠팡잇츠 마지막 로그인 시간';
COMMENT ON COLUMN platform_stores.coupangeats_store_names IS '쿠팡잇츠 복수 매장명 목록 (JSON 배열)';

-- 쿠팡잇츠 매장 조회용 뷰 업데이트
CREATE OR REPLACE VIEW coupangeats_stores AS
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
    coupangeats_session_active,
    coupangeats_last_login,
    coupangeats_store_names,
    created_at,
    updated_at
FROM platform_stores 
WHERE platform = 'coupangeats';

-- 뷰에 대한 코멘트 업데이트
COMMENT ON VIEW coupangeats_stores IS '쿠팡잇츠 매장 정보 조회용 뷰 (복수 매장 지원)';

-- 데이터 검증 함수 생성
CREATE OR REPLACE FUNCTION validate_coupangeats_store_data()
RETURNS TRIGGER AS $$
BEGIN
    -- 쿠팡잇츠 플랫폼인 경우에만 검증
    IF NEW.platform = 'coupangeats' THEN
        -- platform_store_id가 숫자인지 확인
        IF NEW.platform_store_id IS NOT NULL AND NEW.platform_store_id !~ '^[0-9]+$' THEN
            RAISE EXCEPTION 'Invalid coupangeats store ID format: %', NEW.platform_store_id;
        END IF;
        
        -- coupangeats_store_names가 배열 형태인지 확인
        IF NEW.coupangeats_store_names IS NOT NULL THEN
            BEGIN
                -- JSON 배열인지 검증
                IF jsonb_typeof(NEW.coupangeats_store_names) != 'array' THEN
                    RAISE EXCEPTION 'coupangeats_store_names must be a JSON array';
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE EXCEPTION 'Invalid coupangeats_store_names JSON format: %', NEW.coupangeats_store_names;
            END;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 기존 트리거가 있으면 삭제 후 재생성
DROP TRIGGER IF EXISTS validate_coupangeats_store_data_trigger ON platform_stores;

-- 트리거 생성
CREATE TRIGGER validate_coupangeats_store_data_trigger
    BEFORE INSERT OR UPDATE ON platform_stores
    FOR EACH ROW
    EXECUTE FUNCTION validate_coupangeats_store_data();

-- 쿠팡잇츠 매장 등록 함수 생성
CREATE OR REPLACE FUNCTION register_coupangeats_store(
    p_user_id UUID,
    p_store_name VARCHAR(200),
    p_business_type VARCHAR(50),
    p_platform_store_id VARCHAR(100),
    p_platform_url TEXT DEFAULT NULL,
    p_store_names JSONB DEFAULT '[]'::jsonb
)
RETURNS UUID AS $$
DECLARE
    new_store_id UUID;
BEGIN
    INSERT INTO platform_stores (
        user_id,
        store_name,
        business_type,
        platform,
        platform_store_id,
        platform_url,
        coupangeats_store_names,
        is_active,
        crawling_enabled,
        auto_reply_enabled
    ) VALUES (
        p_user_id,
        p_store_name,
        p_business_type,
        'coupangeats',
        p_platform_store_id,
        p_platform_url,
        p_store_names,
        true,
        true,
        false  -- 쿠팡잇츠는 기본적으로 자동 답글 비활성화
    )
    ON CONFLICT (user_id, platform, platform_store_id) 
    DO UPDATE SET
        store_name = EXCLUDED.store_name,
        business_type = EXCLUDED.business_type,
        platform_url = EXCLUDED.platform_url,
        coupangeats_store_names = EXCLUDED.coupangeats_store_names,
        updated_at = NOW()
    RETURNING id INTO new_store_id;
    
    RETURN new_store_id;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION register_coupangeats_store IS '쿠팡잇츠 매장 등록/업데이트 함수 (중복 방지 포함)';

-- 쿠팡잇츠 세션 관리 함수
CREATE OR REPLACE FUNCTION update_coupangeats_session(
    p_user_id UUID,
    p_is_active BOOLEAN DEFAULT TRUE
)
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE platform_stores 
    SET 
        coupangeats_session_active = p_is_active,
        coupangeats_last_login = CASE WHEN p_is_active THEN NOW() ELSE coupangeats_last_login END,
        updated_at = NOW()
    WHERE user_id = p_user_id 
    AND platform = 'coupangeats';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION update_coupangeats_session IS '쿠팡잇츠 세션 상태 업데이트 함수';

-- 쿠팡잇츠 매장별 리뷰 통계 함수
CREATE OR REPLACE FUNCTION get_coupangeats_store_stats(
    p_user_id UUID,
    p_store_id UUID DEFAULT NULL
)
RETURNS TABLE (
    store_id UUID,
    store_name VARCHAR(200),
    platform_store_id VARCHAR(100),
    total_reviews BIGINT,
    avg_rating NUMERIC,
    pending_replies BIGINT,
    latest_review_date DATE,
    reviews_with_photos BIGINT,
    reviews_without_text BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ps.id,
        ps.store_name,
        ps.platform_store_id,
        COALESCE(stats.total_reviews, 0) as total_reviews,
        COALESCE(stats.avg_rating, 0) as avg_rating,
        COALESCE(stats.pending_replies, 0) as pending_replies,
        stats.latest_review_date,
        COALESCE(stats.reviews_with_photos, 0) as reviews_with_photos,
        COALESCE(stats.reviews_without_text, 0) as reviews_without_text
    FROM platform_stores ps
    LEFT JOIN (
        SELECT 
            rc.platform_store_id,
            COUNT(*) as total_reviews,
            ROUND(AVG(rc.rating::numeric), 2) as avg_rating,
            COUNT(CASE WHEN rc.reply_status = 'draft' THEN 1 END) as pending_replies,
            MAX(rc.review_date) as latest_review_date,
            COUNT(CASE WHEN rc.has_photos = TRUE THEN 1 END) as reviews_with_photos,
            COUNT(CASE WHEN rc.review_text IS NULL OR LENGTH(rc.review_text) = 0 THEN 1 END) as reviews_without_text
        FROM reviews_coupangeats rc
        GROUP BY rc.platform_store_id
    ) stats ON ps.id = stats.platform_store_id
    WHERE ps.user_id = p_user_id
    AND ps.platform = 'coupangeats'
    AND (p_store_id IS NULL OR ps.id = p_store_id)
    ORDER BY ps.store_name;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION get_coupangeats_store_stats IS '쿠팡잇츠 매장별 리뷰 통계 조회 함수';

-- 샘플 데이터 (테스트용 - 주석 처리)
/*
-- 테스트용 샘플 데이터
INSERT INTO platform_stores (
    user_id,
    store_name,
    business_type,
    platform,
    platform_store_id,
    platform_url,
    coupangeats_store_names,
    is_active
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000', -- 실제 user_id로 변경 필요
    '큰집닭강정',
    '치킨·호프',
    'coupangeats',
    '708561',
    'https://store.coupangeats.com/merchant/management/reviews',
    '["큰집닭강정(708561)", "100%닭다리살 큰손닭강정(806219)"]'::jsonb,
    true
) ON CONFLICT (user_id, platform, platform_store_id) DO NOTHING;
*/

-- 마이그레이션 완료 확인
SELECT 'Coupangeats columns and functions created successfully!' as migration_status;