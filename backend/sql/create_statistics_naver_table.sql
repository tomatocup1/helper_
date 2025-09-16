-- 네이버 스마트플레이스 통계 데이터 테이블 생성
-- 방문 전/후 지표, 유입 키워드/채널 데이터 저장

CREATE TABLE IF NOT EXISTS statistics_naver (
    -- 기본 정보
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- 방문 전 지표 (3개)
    place_inflow INTEGER DEFAULT 0 NOT NULL,                    -- 플레이스 유입 횟수
    place_inflow_change DECIMAL(5,2),                          -- 플레이스 유입 전일 대비 증감률 (%)
    
    reservation_order INTEGER DEFAULT 0 NOT NULL,              -- 예약·주문 신청 횟수  
    reservation_order_change DECIMAL(5,2),                     -- 예약·주문 전일 대비 증감률 (%)
    
    smart_call INTEGER DEFAULT 0 NOT NULL,                     -- 스마트콜 통화 횟수
    smart_call_change DECIMAL(5,2),                            -- 스마트콜 전일 대비 증감률 (%)
    
    -- 방문 후 지표 (1개)  
    review_registration INTEGER DEFAULT 0 NOT NULL,            -- 리뷰 등록 횟수
    review_registration_change DECIMAL(5,2),                   -- 리뷰 등록 전일 대비 증감률 (%)
    
    -- 유입 분석 데이터 (JSONB 형태로 순위별 저장)
    inflow_channels JSONB DEFAULT '[]'::jsonb,                 -- 유입 채널 순위 데이터
    inflow_keywords JSONB DEFAULT '[]'::jsonb,                 -- 유입 키워드 순위 데이터
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_statistics_naver_platform_store_id ON statistics_naver(platform_store_id);
CREATE INDEX IF NOT EXISTS idx_statistics_naver_date ON statistics_naver(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_statistics_naver_unique_daily ON statistics_naver(platform_store_id, date);

-- RLS (Row Level Security) 설정
ALTER TABLE statistics_naver ENABLE ROW LEVEL SECURITY;

-- 사용자는 자신의 매장 통계만 조회/수정 가능
CREATE POLICY "Users can view their own store statistics" ON statistics_naver
    FOR SELECT USING (
        platform_store_id IN (
            SELECT id FROM platform_stores 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert their own store statistics" ON statistics_naver
    FOR INSERT WITH CHECK (
        platform_store_id IN (
            SELECT id FROM platform_stores 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own store statistics" ON statistics_naver
    FOR UPDATE USING (
        platform_store_id IN (
            SELECT id FROM platform_stores 
            WHERE user_id = auth.uid()
        )
    );

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_statistics_naver_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_statistics_naver_updated_at
    BEFORE UPDATE ON statistics_naver
    FOR EACH ROW
    EXECUTE FUNCTION update_statistics_naver_updated_at();

-- 테이블 코멘트
COMMENT ON TABLE statistics_naver IS '네이버 스마트플레이스 일간 통계 데이터';

-- 컬럼 코멘트
COMMENT ON COLUMN statistics_naver.place_inflow IS '플레이스 유입 횟수';
COMMENT ON COLUMN statistics_naver.place_inflow_change IS '플레이스 유입 전일 대비 증감률 (%)';
COMMENT ON COLUMN statistics_naver.reservation_order IS '예약·주문 신청 횟수';
COMMENT ON COLUMN statistics_naver.reservation_order_change IS '예약·주문 신청 전일 대비 증감률 (%)';
COMMENT ON COLUMN statistics_naver.smart_call IS '스마트콜 통화 횟수';
COMMENT ON COLUMN statistics_naver.smart_call_change IS '스마트콜 통화 전일 대비 증감률 (%)';
COMMENT ON COLUMN statistics_naver.review_registration IS '리뷰 등록 횟수';
COMMENT ON COLUMN statistics_naver.review_registration_change IS '리뷰 등록 전일 대비 증감률 (%)';
COMMENT ON COLUMN statistics_naver.inflow_channels IS '유입 채널 순위 데이터 [{"rank":1,"channel_name":"네이버검색","count":46}]';
COMMENT ON COLUMN statistics_naver.inflow_keywords IS '유입 키워드 순위 데이터 [{"rank":1,"keyword":"청춘껍데기","count":11}]';

-- 샘플 데이터 (테스트용)
/*
INSERT INTO statistics_naver (
    platform_store_id,
    date,
    place_inflow,
    place_inflow_change,
    reservation_order, 
    reservation_order_change,
    smart_call,
    smart_call_change,
    review_registration,
    review_registration_change,
    inflow_channels,
    inflow_keywords
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000', -- 실제 platform_store_id로 변경 필요
    '2025-08-17',
    111,
    -100.0,
    2,
    -100.0,
    3, 
    -100.0,
    2,
    -100.0,
    '[
        {"rank":1,"channel_name":"네이버검색","count":46},
        {"rank":2,"channel_name":"네이버지도","count":27},
        {"rank":3,"channel_name":"페이스북","count":23},
        {"rank":4,"channel_name":"웹사이트","count":11},
        {"rank":5,"channel_name":"인스타그램","count":3}
    ]'::jsonb,
    '[
        {"rank":1,"keyword":"청춘껍데기","count":11},
        {"rank":2,"keyword":"구미인동삼겹살","count":4},
        {"rank":3,"keyword":"청춘껍데기구미","count":4},
        {"rank":4,"keyword":"구미청춘껍데기","count":3},
        {"rank":5,"keyword":"진평맛집추천","count":3}
    ]'::jsonb
);
*/