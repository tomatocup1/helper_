-- ============================================
-- 쿠팡잇츠 리뷰 테이블 생성
-- reviews_coupangeats 테이블과 관련 인덱스 및 함수 정의
-- ============================================

-- reviews_coupangeats 테이블 생성
CREATE TABLE IF NOT EXISTS reviews_coupangeats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 외래키 및 식별자
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    coupangeats_review_id VARCHAR(100) NOT NULL, -- 쿠팡잇츠 리뷰 고유 ID (주문번호 기반)
    coupangeats_review_url TEXT, -- 쿠팡잇츠 리뷰 URL
    
    -- 리뷰어 정보
    reviewer_name VARCHAR(100) NOT NULL,
    reviewer_id VARCHAR(100), -- 쿠팡잇츠는 reviewer_id가 명확하지 않을 수 있음
    order_count VARCHAR(50), -- "3회 주문" 형태의 주문 횟수 정보
    
    -- 리뷰 내용
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT, -- 쿠팡잇츠는 별점만 주고 리뷰 텍스트를 안 남기는 경우가 있음
    review_date DATE NOT NULL,
    order_date DATE, -- 주문일 (리뷰일과 다를 수 있음)
    
    -- 주문 정보
    order_menu_items JSONB DEFAULT '[]'::jsonb, -- 주문한 메뉴 목록
    delivery_method VARCHAR(100), -- 수령방식 (배달/포장 등)
    
    -- 답글 정보
    reply_text TEXT,
    reply_status VARCHAR(20) DEFAULT 'draft' CHECK (reply_status IN ('draft', 'pending', 'sent', 'failed')),
    reply_posted_at TIMESTAMP WITH TIME ZONE,
    reply_error_message TEXT,
    
    -- 부가 정보
    has_photos BOOLEAN DEFAULT FALSE,
    photo_urls JSONB DEFAULT '[]'::jsonb, -- 리뷰 이미지 URL 목록
    
    -- 쿠팡잇츠 전용 메타데이터
    coupangeats_metadata JSONB DEFAULT '{}'::jsonb, -- 주문횟수, 수령방식, 크롤링 정보 등
    
    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 유니크 제약조건 (중복 방지)
    UNIQUE(platform_store_id, coupangeats_review_id)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_platform_store_id ON reviews_coupangeats(platform_store_id);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_review_id ON reviews_coupangeats(coupangeats_review_id);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_review_date ON reviews_coupangeats(review_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_order_date ON reviews_coupangeats(order_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_reply_status ON reviews_coupangeats(reply_status);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_rating ON reviews_coupangeats(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_created_at ON reviews_coupangeats(created_at DESC);

-- 복합 인덱스 (자주 사용되는 조회 패턴 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_store_status ON reviews_coupangeats(platform_store_id, reply_status);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_store_date ON reviews_coupangeats(platform_store_id, review_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_store_order_date ON reviews_coupangeats(platform_store_id, order_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_pending_replies ON reviews_coupangeats(platform_store_id, reply_status) 
WHERE reply_status IN ('draft', 'pending');

-- JSONB 인덱스 (메뉴 및 메타데이터 검색 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_menu_items ON reviews_coupangeats USING GIN (order_menu_items);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_metadata ON reviews_coupangeats USING GIN (coupangeats_metadata);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_photo_urls ON reviews_coupangeats USING GIN (photo_urls);

-- 텍스트 검색 인덱스 (리뷰 내용 검색용)
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_review_text_gin ON reviews_coupangeats USING GIN (to_tsvector('korean', COALESCE(review_text, '')));
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_reviewer_name ON reviews_coupangeats(reviewer_name);

-- 테이블 코멘트
COMMENT ON TABLE reviews_coupangeats IS '쿠팡잇츠 리뷰 데이터 저장 테이블';
COMMENT ON COLUMN reviews_coupangeats.platform_store_id IS '플랫폼 매장 ID (platform_stores 테이블 참조)';
COMMENT ON COLUMN reviews_coupangeats.coupangeats_review_id IS '쿠팡잇츠 리뷰 고유 ID (주문번호 기반)';
COMMENT ON COLUMN reviews_coupangeats.reviewer_name IS '리뷰어 이름';
COMMENT ON COLUMN reviews_coupangeats.order_count IS '주문 횟수 (예: "3회 주문")';
COMMENT ON COLUMN reviews_coupangeats.rating IS '별점 (1-5)';
COMMENT ON COLUMN reviews_coupangeats.review_text IS '리뷰 텍스트 (별점만 주고 텍스트를 안 남기는 경우 NULL 가능)';
COMMENT ON COLUMN reviews_coupangeats.order_date IS '실제 주문일 (리뷰 작성일과 다를 수 있음)';
COMMENT ON COLUMN reviews_coupangeats.order_menu_items IS '주문한 메뉴 목록 (JSON 배열)';
COMMENT ON COLUMN reviews_coupangeats.delivery_method IS '수령방식 (배달/포장 등)';
COMMENT ON COLUMN reviews_coupangeats.reply_status IS '답글 상태 (draft/pending/sent/failed)';
COMMENT ON COLUMN reviews_coupangeats.coupangeats_metadata IS '쿠팡잇츠 전용 메타데이터 (주문횟수, 수령방식, 크롤링정보 등)';

-- updated_at 자동 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION update_reviews_coupangeats_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- updated_at 트리거 생성
CREATE TRIGGER reviews_coupangeats_updated_at_trigger
    BEFORE UPDATE ON reviews_coupangeats
    FOR EACH ROW
    EXECUTE FUNCTION update_reviews_coupangeats_updated_at();

-- 리뷰 통계 뷰 생성
CREATE OR REPLACE VIEW reviews_coupangeats_stats AS
SELECT 
    ps.id as store_id,
    ps.store_name,
    ps.user_id,
    COUNT(*) as total_reviews,
    COUNT(CASE WHEN rc.rating = 5 THEN 1 END) as five_star_reviews,
    COUNT(CASE WHEN rc.rating = 4 THEN 1 END) as four_star_reviews,
    COUNT(CASE WHEN rc.rating = 3 THEN 1 END) as three_star_reviews,
    COUNT(CASE WHEN rc.rating = 2 THEN 1 END) as two_star_reviews,
    COUNT(CASE WHEN rc.rating = 1 THEN 1 END) as one_star_reviews,
    ROUND(AVG(rc.rating::numeric), 2) as average_rating,
    COUNT(CASE WHEN rc.reply_status = 'sent' THEN 1 END) as replied_reviews,
    COUNT(CASE WHEN rc.reply_status = 'draft' THEN 1 END) as pending_replies,
    COUNT(CASE WHEN rc.has_photos = TRUE THEN 1 END) as reviews_with_photos,
    COUNT(CASE WHEN rc.review_text IS NOT NULL AND LENGTH(rc.review_text) > 0 THEN 1 END) as reviews_with_text,
    MAX(rc.review_date) as latest_review_date,
    MIN(rc.review_date) as earliest_review_date,
    MAX(rc.order_date) as latest_order_date,
    MIN(rc.order_date) as earliest_order_date
FROM platform_stores ps
LEFT JOIN reviews_coupangeats rc ON ps.id = rc.platform_store_id
WHERE ps.platform = 'coupangeats'
GROUP BY ps.id, ps.store_name, ps.user_id;

-- 뷰 코멘트
COMMENT ON VIEW reviews_coupangeats_stats IS '쿠팡잇츠 리뷰 통계 집계 뷰';

-- 답글 대기 리뷰 조회 함수
CREATE OR REPLACE FUNCTION get_coupangeats_pending_replies(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    review_id UUID,
    store_name VARCHAR(200),
    reviewer_name VARCHAR(100),
    rating INTEGER,
    review_text TEXT,
    review_date DATE,
    order_date DATE,
    order_menu_items JSONB,
    delivery_method VARCHAR(100),
    coupangeats_review_id VARCHAR(100),
    has_photos BOOLEAN,
    photo_urls JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rc.id,
        ps.store_name,
        rc.reviewer_name,
        rc.rating,
        rc.review_text,
        rc.review_date,
        rc.order_date,
        rc.order_menu_items,
        rc.delivery_method,
        rc.coupangeats_review_id,
        rc.has_photos,
        rc.photo_urls
    FROM reviews_coupangeats rc
    JOIN platform_stores ps ON rc.platform_store_id = ps.id
    WHERE ps.user_id = p_user_id
    AND ps.platform = 'coupangeats'
    AND rc.reply_status = 'draft'
    ORDER BY rc.review_date DESC, rc.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION get_coupangeats_pending_replies IS '답글이 필요한 쿠팡잇츠 리뷰 조회 함수';

-- 리뷰 답글 상태 업데이트 함수
CREATE OR REPLACE FUNCTION update_coupangeats_reply_status(
    p_review_id UUID,
    p_reply_status VARCHAR(20),
    p_reply_text TEXT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE reviews_coupangeats 
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
COMMENT ON FUNCTION update_coupangeats_reply_status IS '쿠팡잇츠 리뷰 답글 상태 업데이트 함수';

-- 리뷰 검색 함수 (텍스트 검색)
CREATE OR REPLACE FUNCTION search_coupangeats_reviews(
    p_user_id UUID,
    p_search_text TEXT,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    review_id UUID,
    store_name VARCHAR(200),
    reviewer_name VARCHAR(100),
    rating INTEGER,
    review_text TEXT,
    review_date DATE,
    coupangeats_review_id VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rc.id,
        ps.store_name,
        rc.reviewer_name,
        rc.rating,
        rc.review_text,
        rc.review_date,
        rc.coupangeats_review_id
    FROM reviews_coupangeats rc
    JOIN platform_stores ps ON rc.platform_store_id = ps.id
    WHERE ps.user_id = p_user_id
    AND ps.platform = 'coupangeats'
    AND (
        rc.review_text ILIKE '%' || p_search_text || '%'
        OR rc.reviewer_name ILIKE '%' || p_search_text || '%'
        OR to_tsvector('korean', COALESCE(rc.review_text, '')) @@ plainto_tsquery('korean', p_search_text)
    )
    ORDER BY rc.review_date DESC, rc.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION search_coupangeats_reviews IS '쿠팡잇츠 리뷰 텍스트 검색 함수';

-- Row Level Security (RLS) 활성화
ALTER TABLE reviews_coupangeats ENABLE ROW LEVEL SECURITY;

-- RLS 정책 생성 (사용자별 데이터 격리)
CREATE POLICY reviews_coupangeats_user_policy ON reviews_coupangeats
    FOR ALL USING (
        platform_store_id IN (
            SELECT id FROM platform_stores 
            WHERE user_id = auth.uid()
            AND platform = 'coupangeats'
        )
    );

-- Service Role은 모든 데이터 접근 가능
CREATE POLICY reviews_coupangeats_service_role_policy ON reviews_coupangeats
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- 쿠팡잇츠 매장 조회용 뷰 생성 (기존 platform_stores 확장)
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
    created_at,
    updated_at
FROM platform_stores 
WHERE platform = 'coupangeats';

-- 뷰에 대한 코멘트
COMMENT ON VIEW coupangeats_stores IS '쿠팡잇츠 매장 정보 조회용 뷰';

-- 샘플 데이터 (테스트용 - 주석 처리)
/*
-- 테스트용 샘플 데이터 예시
INSERT INTO reviews_coupangeats (
    platform_store_id,
    coupangeats_review_id,
    reviewer_name,
    rating,
    review_text,
    review_date,
    order_date,
    order_menu_items,
    delivery_method,
    order_count,
    reply_status,
    coupangeats_metadata
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000', -- 실제 platform_store_id로 변경 필요
    '0ELMJG',
    '김**',
    5,
    '맛있게 잘 먹었습니다!',
    '2024-08-19',
    '2024-08-18',
    '["(2~3인세트) 만족 100% 완전닭다리살 닭강정"]'::jsonb,
    '배달',
    '3회 주문',
    'draft',
    '{"order_count": "3회 주문", "delivery_method": "배달", "crawled_at": "2024-08-19T10:30:00Z"}'::jsonb
) ON CONFLICT (platform_store_id, coupangeats_review_id) DO NOTHING;
*/

-- 마이그레이션 완료 확인
SELECT 'reviews_coupangeats table and related objects created successfully!' as migration_status;