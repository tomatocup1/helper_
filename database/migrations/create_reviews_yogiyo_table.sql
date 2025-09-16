-- ============================================
-- 요기요 리뷰 테이블 생성
-- reviews_yogiyo 테이블과 관련 인덱스 및 함수 정의
-- DSID (DOM Stable ID) 기반 리뷰 식별 시스템
-- ============================================

-- reviews_yogiyo 테이블 생성
CREATE TABLE IF NOT EXISTS reviews_yogiyo (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 외래키 및 식별자
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    yogiyo_dsid VARCHAR(16) NOT NULL, -- DSID (DOM Stable ID) - 16자리 고유 해시
    yogiyo_review_url TEXT, -- 요기요 리뷰 URL
    
    -- DSID 관련 메타데이터 (재탐색용)
    content_hash VARCHAR(16) NOT NULL, -- 콘텐츠 해시 (축약형)
    rolling_hash VARCHAR(16) NOT NULL, -- 롤링 해시 (축약형)
    neighbor_hash VARCHAR(16) NOT NULL, -- 이웃 윈도우 해시 (축약형)
    page_salt VARCHAR(8) NOT NULL, -- 페이지 솔트
    index_hint INTEGER NOT NULL DEFAULT 0, -- 페이지 내 순서 힌트
    
    -- 리뷰어 정보
    reviewer_name VARCHAR(100) NOT NULL,
    reviewer_id VARCHAR(100), -- 요기요 리뷰어 ID (있는 경우)
    
    -- 리뷰 내용
    overall_rating DECIMAL(2,1) CHECK (overall_rating >= 0.0 AND overall_rating <= 5.0), -- 전체 별점 (소수점 허용)
    taste_rating INTEGER CHECK (taste_rating >= 0 AND taste_rating <= 5), -- 맛 별점
    quantity_rating INTEGER CHECK (quantity_rating >= 0 AND quantity_rating <= 5), -- 양 별점
    review_text TEXT, -- 리뷰 텍스트
    review_date DATE NOT NULL,
    original_review_date VARCHAR(50), -- 원본 날짜 문자열 ("14시간 전" 등)
    
    -- 주문 정보
    order_menu TEXT, -- 주문한 메뉴 (단일 문자열)
    order_menu_items JSONB DEFAULT '[]'::jsonb, -- 주문한 메뉴 목록 (구조화된 데이터)
    
    -- 답글 정보
    reply_text TEXT,
    reply_status VARCHAR(20) DEFAULT 'draft' CHECK (reply_status IN ('draft', 'pending', 'sent', 'failed')),
    reply_posted_at TIMESTAMP WITH TIME ZONE,
    reply_error_message TEXT,
    
    -- 부가 정보
    has_photos BOOLEAN DEFAULT FALSE,
    photo_urls JSONB DEFAULT '[]'::jsonb, -- 리뷰 이미지 URL 목록
    
    -- 별점 추출 메타데이터
    rating_extraction_method VARCHAR(50) DEFAULT 'svg_analysis', -- 별점 추출 방법
    rating_confidence DECIMAL(3,2) DEFAULT 1.0, -- 별점 추출 신뢰도 (0.0-1.0)
    
    -- 요기요 전용 메타데이터
    yogiyo_metadata JSONB DEFAULT '{}'::jsonb, -- DSID 생성 정보, 크롤링 정보 등
    
    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 유니크 제약조건 (중복 방지)
    UNIQUE(platform_store_id, yogiyo_dsid)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_platform_store_id ON reviews_yogiyo(platform_store_id);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_dsid ON reviews_yogiyo(yogiyo_dsid);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_review_date ON reviews_yogiyo(review_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_reply_status ON reviews_yogiyo(reply_status);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_overall_rating ON reviews_yogiyo(overall_rating);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_created_at ON reviews_yogiyo(created_at DESC);

-- DSID 관련 인덱스 (재탐색 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_content_hash ON reviews_yogiyo(content_hash);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_rolling_hash ON reviews_yogiyo(rolling_hash);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_neighbor_hash ON reviews_yogiyo(neighbor_hash);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_page_salt ON reviews_yogiyo(page_salt);

-- 복합 인덱스 (자주 사용되는 조회 패턴 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_store_status ON reviews_yogiyo(platform_store_id, reply_status);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_store_date ON reviews_yogiyo(platform_store_id, review_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_pending_replies ON reviews_yogiyo(platform_store_id, reply_status) 
WHERE reply_status IN ('draft', 'pending');

-- DSID 재탐색용 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_dsid_lookup ON reviews_yogiyo(content_hash, rolling_hash, neighbor_hash);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_page_context ON reviews_yogiyo(page_salt, index_hint);

-- JSONB 인덱스 (메뉴 및 메타데이터 검색 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_menu_items ON reviews_yogiyo USING GIN (order_menu_items);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_metadata ON reviews_yogiyo USING GIN (yogiyo_metadata);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_photo_urls ON reviews_yogiyo USING GIN (photo_urls);

-- 텍스트 검색 인덱스 (리뷰 내용 검색용) - 기본 언어 설정 사용
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_review_text_gin ON reviews_yogiyo USING GIN (to_tsvector('simple', COALESCE(review_text, '')));
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_reviewer_name ON reviews_yogiyo(reviewer_name);

-- 테이블 코멘트
COMMENT ON TABLE reviews_yogiyo IS '요기요 리뷰 데이터 저장 테이블 (DSID 기반)';
COMMENT ON COLUMN reviews_yogiyo.platform_store_id IS '플랫폼 매장 ID (platform_stores 테이블 참조)';
COMMENT ON COLUMN reviews_yogiyo.yogiyo_dsid IS '요기요 DSID (DOM Stable ID) - 16자리 고유 해시';
COMMENT ON COLUMN reviews_yogiyo.content_hash IS '콘텐츠 해시 (DSID 재탐색용)';
COMMENT ON COLUMN reviews_yogiyo.rolling_hash IS '롤링 해시 (DSID 재탐색용)';
COMMENT ON COLUMN reviews_yogiyo.neighbor_hash IS '이웃 윈도우 해시 (DSID 재탐색용)';
COMMENT ON COLUMN reviews_yogiyo.page_salt IS '페이지 솔트 (날짜, URL, 정렬 기반)';
COMMENT ON COLUMN reviews_yogiyo.index_hint IS '페이지 내 순서 힌트 (0부터 시작)';
COMMENT ON COLUMN reviews_yogiyo.reviewer_name IS '리뷰어 이름';
COMMENT ON COLUMN reviews_yogiyo.overall_rating IS '전체 별점 (0.0-5.0, 소수점 허용)';
COMMENT ON COLUMN reviews_yogiyo.taste_rating IS '맛 별점 (0-5)';
COMMENT ON COLUMN reviews_yogiyo.quantity_rating IS '양 별점 (0-5)';
COMMENT ON COLUMN reviews_yogiyo.review_text IS '리뷰 텍스트';
COMMENT ON COLUMN reviews_yogiyo.original_review_date IS '원본 날짜 문자열 ("14시간 전" 등)';
COMMENT ON COLUMN reviews_yogiyo.order_menu IS '주문한 메뉴 (원본 문자열)';
COMMENT ON COLUMN reviews_yogiyo.order_menu_items IS '주문한 메뉴 목록 (구조화된 JSON 배열)';
COMMENT ON COLUMN reviews_yogiyo.reply_status IS '답글 상태 (draft/pending/sent/failed)';
COMMENT ON COLUMN reviews_yogiyo.rating_extraction_method IS '별점 추출 방법 (svg_analysis/javascript/failed)';
COMMENT ON COLUMN reviews_yogiyo.rating_confidence IS '별점 추출 신뢰도 (0.0-1.0)';
COMMENT ON COLUMN reviews_yogiyo.yogiyo_metadata IS '요기요 전용 메타데이터 (DSID 생성 정보, 크롤링 정보 등)';

-- updated_at 자동 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION update_reviews_yogiyo_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- updated_at 트리거 생성
CREATE TRIGGER reviews_yogiyo_updated_at_trigger
    BEFORE UPDATE ON reviews_yogiyo
    FOR EACH ROW
    EXECUTE FUNCTION update_reviews_yogiyo_updated_at();

-- 리뷰 통계 뷰 생성
CREATE OR REPLACE VIEW reviews_yogiyo_stats AS
SELECT 
    ps.id as store_id,
    ps.store_name,
    ps.user_id,
    COUNT(*) as total_reviews,
    COUNT(CASE WHEN ry.overall_rating >= 4.5 THEN 1 END) as excellent_reviews, -- 4.5점 이상
    COUNT(CASE WHEN ry.overall_rating >= 4.0 AND ry.overall_rating < 4.5 THEN 1 END) as good_reviews, -- 4.0-4.4점
    COUNT(CASE WHEN ry.overall_rating >= 3.0 AND ry.overall_rating < 4.0 THEN 1 END) as fair_reviews, -- 3.0-3.9점
    COUNT(CASE WHEN ry.overall_rating >= 2.0 AND ry.overall_rating < 3.0 THEN 1 END) as poor_reviews, -- 2.0-2.9점
    COUNT(CASE WHEN ry.overall_rating < 2.0 THEN 1 END) as bad_reviews, -- 2.0점 미만
    ROUND(AVG(ry.overall_rating::numeric), 2) as average_overall_rating,
    ROUND(AVG(ry.taste_rating::numeric), 2) as average_taste_rating,
    ROUND(AVG(ry.quantity_rating::numeric), 2) as average_quantity_rating,
    COUNT(CASE WHEN ry.reply_status = 'sent' THEN 1 END) as replied_reviews,
    COUNT(CASE WHEN ry.reply_status = 'draft' THEN 1 END) as pending_replies,
    COUNT(CASE WHEN ry.has_photos = TRUE THEN 1 END) as reviews_with_photos,
    COUNT(CASE WHEN ry.review_text IS NOT NULL AND LENGTH(ry.review_text) > 0 THEN 1 END) as reviews_with_text,
    MAX(ry.review_date) as latest_review_date,
    MIN(ry.review_date) as earliest_review_date,
    AVG(ry.rating_confidence) as average_rating_confidence
FROM platform_stores ps
LEFT JOIN reviews_yogiyo ry ON ps.id = ry.platform_store_id
WHERE ps.platform = 'yogiyo'
GROUP BY ps.id, ps.store_name, ps.user_id;

-- 뷰 코멘트
COMMENT ON VIEW reviews_yogiyo_stats IS '요기요 리뷰 통계 집계 뷰 (DSID 기반)';

-- 답글 대기 리뷰 조회 함수
CREATE OR REPLACE FUNCTION get_yogiyo_pending_replies(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    review_id UUID,
    store_name VARCHAR(200),
    yogiyo_dsid VARCHAR(16),
    reviewer_name VARCHAR(100),
    overall_rating DECIMAL(2,1),
    taste_rating INTEGER,
    quantity_rating INTEGER,
    review_text TEXT,
    review_date DATE,
    order_menu TEXT,
    order_menu_items JSONB,
    has_photos BOOLEAN,
    photo_urls JSONB,
    rating_confidence DECIMAL(3,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ry.id,
        ps.store_name,
        ry.yogiyo_dsid,
        ry.reviewer_name,
        ry.overall_rating,
        ry.taste_rating,
        ry.quantity_rating,
        ry.review_text,
        ry.review_date,
        ry.order_menu,
        ry.order_menu_items,
        ry.has_photos,
        ry.photo_urls,
        ry.rating_confidence
    FROM reviews_yogiyo ry
    JOIN platform_stores ps ON ry.platform_store_id = ps.id
    WHERE ps.user_id = p_user_id
    AND ps.platform = 'yogiyo'
    AND ry.reply_status = 'draft'
    ORDER BY ry.review_date DESC, ry.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION get_yogiyo_pending_replies IS '답글이 필요한 요기요 리뷰 조회 함수 (DSID 기반)';

-- DSID 기반 리뷰 재탐색 함수
CREATE OR REPLACE FUNCTION find_yogiyo_review_by_dsid(
    p_platform_store_id UUID,
    p_yogiyo_dsid VARCHAR(16)
)
RETURNS TABLE (
    review_id UUID,
    yogiyo_dsid VARCHAR(16),
    content_hash VARCHAR(16),
    rolling_hash VARCHAR(16),
    neighbor_hash VARCHAR(16),
    page_salt VARCHAR(8),
    index_hint INTEGER,
    reviewer_name VARCHAR(100),
    review_text TEXT,
    review_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ry.id,
        ry.yogiyo_dsid,
        ry.content_hash,
        ry.rolling_hash,
        ry.neighbor_hash,
        ry.page_salt,
        ry.index_hint,
        ry.reviewer_name,
        ry.review_text,
        ry.review_date
    FROM reviews_yogiyo ry
    WHERE ry.platform_store_id = p_platform_store_id
    AND ry.yogiyo_dsid = p_yogiyo_dsid
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION find_yogiyo_review_by_dsid IS 'DSID로 요기요 리뷰 조회 함수';

-- 리뷰 답글 상태 업데이트 함수
CREATE OR REPLACE FUNCTION update_yogiyo_reply_status(
    p_review_id UUID,
    p_reply_status VARCHAR(20),
    p_reply_text TEXT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE reviews_yogiyo 
    SET 
        reply_status = p_reply_status,
        reply_text = COALESCE(p_reply_text, reply_text),
        reply_posted_at = CASE WHEN p_reply_status = 'sent' THEN NOW() ELSE reply_posted_at END,
        reply_error_message = p_error_message,
        updated_at = NOW()
    WHERE id = p_review_id;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION update_yogiyo_reply_status IS '요기요 리뷰 답글 상태 업데이트 함수';

-- 리뷰 검색 함수 (텍스트 검색)
CREATE OR REPLACE FUNCTION search_yogiyo_reviews(
    p_user_id UUID,
    p_search_text TEXT,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    review_id UUID,
    store_name VARCHAR(200),
    yogiyo_dsid VARCHAR(16),
    reviewer_name VARCHAR(100),
    overall_rating DECIMAL(2,1),
    review_text TEXT,
    review_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ry.id,
        ps.store_name,
        ry.yogiyo_dsid,
        ry.reviewer_name,
        ry.overall_rating,
        ry.review_text,
        ry.review_date
    FROM reviews_yogiyo ry
    JOIN platform_stores ps ON ry.platform_store_id = ps.id
    WHERE ps.user_id = p_user_id
    AND ps.platform = 'yogiyo'
    AND (
        ry.review_text ILIKE '%' || p_search_text || '%'
        OR ry.reviewer_name ILIKE '%' || p_search_text || '%'
        OR ry.order_menu ILIKE '%' || p_search_text || '%'
        OR to_tsvector('simple', COALESCE(ry.review_text, '')) @@ plainto_tsquery('simple', p_search_text)
    )
    ORDER BY ry.review_date DESC, ry.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION search_yogiyo_reviews IS '요기요 리뷰 텍스트 검색 함수';

-- Row Level Security (RLS) 활성화
ALTER TABLE reviews_yogiyo ENABLE ROW LEVEL SECURITY;

-- RLS 정책 생성 (사용자별 데이터 격리)
CREATE POLICY reviews_yogiyo_user_policy ON reviews_yogiyo
    FOR ALL USING (
        platform_store_id IN (
            SELECT id FROM platform_stores 
            WHERE user_id = auth.uid()
            AND platform = 'yogiyo'
        )
    );

-- Service Role은 모든 데이터 접근 가능
CREATE POLICY reviews_yogiyo_service_role_policy ON reviews_yogiyo
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- 요기요 매장 조회용 뷰 생성 (기존 platform_stores 확장) - 선택적
-- CREATE OR REPLACE VIEW yogiyo_stores AS
-- SELECT 
--     id,
--     user_id,
--     store_name,
--     business_type,
--     sub_type,
--     platform_store_id,
--     platform_url,
--     is_active,
--     is_verified,
--     created_at,
--     updated_at
-- FROM platform_stores 
-- WHERE platform = 'yogiyo';

-- 뷰에 대한 코멘트
-- COMMENT ON VIEW yogiyo_stores IS '요기요 매장 정보 조회용 뷰';

-- DSID 중복 확인 함수
CREATE OR REPLACE FUNCTION check_yogiyo_dsid_duplicate(
    p_platform_store_id UUID,
    p_yogiyo_dsid VARCHAR(16)
)
RETURNS BOOLEAN AS $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count
    FROM reviews_yogiyo
    WHERE platform_store_id = p_platform_store_id
    AND yogiyo_dsid = p_yogiyo_dsid;
    
    RETURN duplicate_count > 0;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION check_yogiyo_dsid_duplicate IS 'DSID 중복 확인 함수';

-- 샘플 데이터 (테스트용 - 주석 처리)
/*
-- 테스트용 샘플 데이터 예시
INSERT INTO reviews_yogiyo (
    platform_store_id,
    yogiyo_dsid,
    content_hash,
    rolling_hash,
    neighbor_hash,
    page_salt,
    index_hint,
    reviewer_name,
    overall_rating,
    taste_rating,
    quantity_rating,
    review_text,
    review_date,
    original_review_date,
    order_menu,
    order_menu_items,
    reply_status,
    rating_extraction_method,
    rating_confidence,
    yogiyo_metadata
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000', -- 실제 platform_store_id로 변경 필요
    '4dcd5656d7030edf',
    '8bc9feeb586f81d6',
    'ed3efc94995d331b',
    '9f73662a1b856808',
    'abc12345',
    0,
    'di**',
    5.0,
    5,
    5,
    '배달빠르고 맛있어요. 곱창은 여기서만 먹어요 ㅎㅎ',
    '2025-08-21',
    '14시간 전',
    '[주문율 1위] 세친구 야채곱창',
    '["[주문율 1위] 세친구 야채곱창"]'::jsonb,
    'draft',
    'svg_analysis',
    1.0,
    '{"page_url": "https://ceo.yogiyo.co.kr/reviews", "sort_option": "latest", "filter_option": "unanswered", "crawled_at": "2025-08-22T10:30:00Z"}'::jsonb
) ON CONFLICT (platform_store_id, yogiyo_dsid) DO NOTHING;
*/

-- 마이그레이션 완료 확인
SELECT 'reviews_yogiyo table and related objects created successfully!' as migration_status;