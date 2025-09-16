-- ============================================
-- 배달의민족 리뷰 테이블 생성
-- reviews_baemin 테이블과 관련 인덱스 및 함수 정의
-- ============================================

-- reviews_baemin 테이블 생성
CREATE TABLE IF NOT EXISTS reviews_baemin (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 외래키 및 식별자
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    baemin_review_id VARCHAR(100) NOT NULL, -- 배민 리뷰 고유 ID
    baemin_review_url TEXT, -- 배민 리뷰 URL
    
    -- 리뷰어 정보
    reviewer_name VARCHAR(100) NOT NULL,
    reviewer_id VARCHAR(100), -- 배민은 reviewer_id가 명확하지 않을 수 있음
    reviewer_level VARCHAR(50), -- 배민은 reviewer_level이 없을 수 있음
    
    -- 리뷰 내용
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT NOT NULL,
    review_date DATE NOT NULL,
    
    -- 주문 정보
    order_menu_items JSONB DEFAULT '[]'::jsonb, -- 주문한 메뉴 목록
    
    -- 답글 정보
    reply_text TEXT,
    reply_status VARCHAR(20) DEFAULT 'draft' CHECK (reply_status IN ('draft', 'pending', 'sent', 'failed')),
    reply_posted_at TIMESTAMP WITH TIME ZONE,
    reply_error_message TEXT,
    
    -- 부가 정보
    has_photos BOOLEAN DEFAULT FALSE,
    photo_urls JSONB DEFAULT '[]'::jsonb,
    
    -- 배민 전용 메타데이터
    baemin_metadata JSONB DEFAULT '{}'::jsonb, -- 배송 평가, 크롤링 정보 등
    
    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 유니크 제약조건 (중복 방지)
    UNIQUE(platform_store_id, baemin_review_id)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_platform_store_id ON reviews_baemin(platform_store_id);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_review_id ON reviews_baemin(baemin_review_id);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_review_date ON reviews_baemin(review_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_reply_status ON reviews_baemin(reply_status);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_rating ON reviews_baemin(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_created_at ON reviews_baemin(created_at DESC);

-- 복합 인덱스 (자주 사용되는 조회 패턴 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_store_status ON reviews_baemin(platform_store_id, reply_status);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_store_date ON reviews_baemin(platform_store_id, review_date DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_pending_replies ON reviews_baemin(platform_store_id, reply_status) 
WHERE reply_status IN ('draft', 'pending');

-- JSONB 인덱스 (메뉴 검색 최적화)
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_menu_items ON reviews_baemin USING GIN (order_menu_items);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_metadata ON reviews_baemin USING GIN (baemin_metadata);

-- 테이블 코멘트
COMMENT ON TABLE reviews_baemin IS '배달의민족 리뷰 데이터 저장 테이블';
COMMENT ON COLUMN reviews_baemin.platform_store_id IS '플랫폼 매장 ID (platform_stores 테이블 참조)';
COMMENT ON COLUMN reviews_baemin.baemin_review_id IS '배달의민족 리뷰 고유 ID';
COMMENT ON COLUMN reviews_baemin.reviewer_name IS '리뷰어 이름';
COMMENT ON COLUMN reviews_baemin.rating IS '별점 (1-5)';
COMMENT ON COLUMN reviews_baemin.order_menu_items IS '주문한 메뉴 목록 (JSON 배열)';
COMMENT ON COLUMN reviews_baemin.reply_status IS '답글 상태 (draft/pending/sent/failed)';
COMMENT ON COLUMN reviews_baemin.baemin_metadata IS '배민 전용 메타데이터 (배송평가, 크롤링정보 등)';

-- updated_at 자동 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION update_reviews_baemin_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- updated_at 트리거 생성
CREATE TRIGGER reviews_baemin_updated_at_trigger
    BEFORE UPDATE ON reviews_baemin
    FOR EACH ROW
    EXECUTE FUNCTION update_reviews_baemin_updated_at();

-- 리뷰 통계 뷰 생성
CREATE OR REPLACE VIEW reviews_baemin_stats AS
SELECT 
    ps.id as store_id,
    ps.store_name,
    ps.user_id,
    COUNT(*) as total_reviews,
    COUNT(CASE WHEN rb.rating = 5 THEN 1 END) as five_star_reviews,
    COUNT(CASE WHEN rb.rating = 4 THEN 1 END) as four_star_reviews,
    COUNT(CASE WHEN rb.rating = 3 THEN 1 END) as three_star_reviews,
    COUNT(CASE WHEN rb.rating = 2 THEN 1 END) as two_star_reviews,
    COUNT(CASE WHEN rb.rating = 1 THEN 1 END) as one_star_reviews,
    ROUND(AVG(rb.rating::numeric), 2) as average_rating,
    COUNT(CASE WHEN rb.reply_status = 'sent' THEN 1 END) as replied_reviews,
    COUNT(CASE WHEN rb.reply_status = 'draft' THEN 1 END) as pending_replies,
    MAX(rb.review_date) as latest_review_date,
    MIN(rb.review_date) as earliest_review_date
FROM platform_stores ps
LEFT JOIN reviews_baemin rb ON ps.id = rb.platform_store_id
WHERE ps.platform = 'baemin'
GROUP BY ps.id, ps.store_name, ps.user_id;

-- 뷰 코멘트
COMMENT ON VIEW reviews_baemin_stats IS '배달의민족 리뷰 통계 집계 뷰';

-- 답글 대기 리뷰 조회 함수
CREATE OR REPLACE FUNCTION get_baemin_pending_replies(
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
    order_menu_items JSONB,
    baemin_review_id VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rb.id,
        ps.store_name,
        rb.reviewer_name,
        rb.rating,
        rb.review_text,
        rb.review_date,
        rb.order_menu_items,
        rb.baemin_review_id
    FROM reviews_baemin rb
    JOIN platform_stores ps ON rb.platform_store_id = ps.id
    WHERE ps.user_id = p_user_id
    AND ps.platform = 'baemin'
    AND rb.reply_status = 'draft'
    ORDER BY rb.review_date DESC, rb.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 함수 코멘트
COMMENT ON FUNCTION get_baemin_pending_replies IS '답글이 필요한 배달의민족 리뷰 조회 함수';

-- 리뷰 답글 상태 업데이트 함수
CREATE OR REPLACE FUNCTION update_baemin_reply_status(
    p_review_id UUID,
    p_reply_status VARCHAR(20),
    p_reply_text TEXT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE reviews_baemin 
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
COMMENT ON FUNCTION update_baemin_reply_status IS '배달의민족 리뷰 답글 상태 업데이트 함수';

-- Row Level Security (RLS) 활성화
ALTER TABLE reviews_baemin ENABLE ROW LEVEL SECURITY;

-- RLS 정책 생성 (사용자별 데이터 격리)
CREATE POLICY reviews_baemin_user_policy ON reviews_baemin
    FOR ALL USING (
        platform_store_id IN (
            SELECT id FROM platform_stores 
            WHERE user_id = auth.uid()
            AND platform = 'baemin'
        )
    );

-- Service Role은 모든 데이터 접근 가능
CREATE POLICY reviews_baemin_service_role_policy ON reviews_baemin
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- 샘플 데이터 (테스트용 - 주석 처리)
/*
-- 테스트용 샘플 데이터 예시
INSERT INTO reviews_baemin (
    platform_store_id,
    baemin_review_id,
    baemin_review_url,
    reviewer_name,
    rating,
    review_text,
    review_date,
    order_menu_items,
    reply_status,
    baemin_metadata
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000', -- 실제 platform_store_id로 변경 필요
    'bm_test_123',
    'https://self.baemin.com/shops/14522306/reviews',
    '김리뷰',
    5,
    '정말 맛있어요! 빠른 배송도 좋았습니다.',
    '2024-03-15',
    '["치킨", "피자"]'::jsonb,
    'draft',
    '{"delivery_review": "빠른 배송", "crawled_at": "2024-03-15T10:30:00Z"}'::jsonb
) ON CONFLICT (platform_store_id, baemin_review_id) DO NOTHING;
*/

-- 마이그레이션 완료 확인
SELECT 'reviews_baemin table and related objects created successfully!' as migration_status;