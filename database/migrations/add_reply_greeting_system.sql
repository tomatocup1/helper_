-- ============================================
-- 답글 인사말 시스템 마이그레이션
-- 기존 템플릿 제거 및 유연한 인사말 시스템 추가
-- 2025-08-27: AI 자연스러운 답글 생성 시스템으로 전환
-- ============================================

-- platform_stores 테이블 수정
ALTER TABLE platform_stores 
-- 기존 템플릿 필드 제거 (더 이상 사용하지 않음)
DROP COLUMN IF EXISTS positive_reply_template,
DROP COLUMN IF EXISTS negative_reply_template, 
DROP COLUMN IF EXISTS neutral_reply_template,

-- 새로운 인사말 및 답글 시스템 필드 추가
ADD COLUMN greeting_template VARCHAR(200), -- 첫인사 템플릿 (NULL 허용 - AI가 자연스럽게 생성)
ADD COLUMN closing_template VARCHAR(200),  -- 끝인사 템플릿 (NULL 허용 - AI가 자연스럽게 생성)
ADD COLUMN reply_tone VARCHAR(20) DEFAULT 'friendly', -- 답글 톤 (friendly/formal/casual)
ADD COLUMN min_reply_length INTEGER DEFAULT 50, -- 최소 답글 길이 (글자수)
ADD COLUMN max_reply_length INTEGER DEFAULT 200, -- 최대 답글 길이 (글자수)
ADD COLUMN brand_voice TEXT; -- 매장 고유 목소리/특징 설명

-- 기존 seo_keywords 필드가 없다면 추가 (JSONB → TEXT[] 배열로 변경)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='platform_stores' AND column_name='seo_keywords') THEN
        ALTER TABLE platform_stores ADD COLUMN seo_keywords TEXT[];
    END IF;
    
    -- 기존 JSONB 타입이면 TEXT[] 배열로 변환
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='platform_stores' 
               AND column_name='seo_keywords' 
               AND data_type='jsonb') THEN
        -- JSONB를 TEXT[] 배열로 변환
        ALTER TABLE platform_stores ALTER COLUMN seo_keywords TYPE TEXT[] 
        USING (
            CASE 
                WHEN seo_keywords IS NULL THEN NULL
                WHEN jsonb_typeof(seo_keywords) = 'array' THEN 
                    ARRAY(SELECT jsonb_array_elements_text(seo_keywords))
                ELSE ARRAY[seo_keywords::text]
            END
        );
    END IF;
END $$;

-- 모든 리뷰 테이블에 키워드 추적 및 답글 품질 필드 추가
-- reviews_naver 테이블
ALTER TABLE reviews_naver 
ADD COLUMN IF NOT EXISTS inserted_keywords TEXT[], -- 삽입된 키워드 배열
ADD COLUMN IF NOT EXISTS reply_naturalness_score FLOAT, -- 답글 자연스러움 점수 (0.0-1.0)
ADD COLUMN IF NOT EXISTS scheduled_reply_date TIMESTAMP WITH TIME ZONE, -- 답글 등록 예정일
ADD COLUMN IF NOT EXISTS censorship_reason TEXT; -- 검열 사유

-- reviews_baemin 테이블
ALTER TABLE reviews_baemin 
ADD COLUMN IF NOT EXISTS inserted_keywords TEXT[],
ADD COLUMN IF NOT EXISTS reply_naturalness_score FLOAT,
ADD COLUMN IF NOT EXISTS scheduled_reply_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS censorship_reason TEXT;

-- reviews_yogiyo 테이블
ALTER TABLE reviews_yogiyo 
ADD COLUMN IF NOT EXISTS inserted_keywords TEXT[],
ADD COLUMN IF NOT EXISTS reply_naturalness_score FLOAT,
ADD COLUMN IF NOT EXISTS scheduled_reply_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS censorship_reason TEXT;

-- reviews_coupangeats 테이블
ALTER TABLE reviews_coupangeats 
ADD COLUMN IF NOT EXISTS inserted_keywords TEXT[],
ADD COLUMN IF NOT EXISTS reply_naturalness_score FLOAT,
ADD COLUMN IF NOT EXISTS scheduled_reply_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS censorship_reason TEXT;

-- 성능 최적화를 위한 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_platform_stores_greeting ON platform_stores(greeting_template) WHERE greeting_template IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_platform_stores_closing ON platform_stores(closing_template) WHERE closing_template IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_platform_stores_reply_tone ON platform_stores(reply_tone);

-- 리뷰 테이블 인덱스 (스케줄된 답글 조회용)
CREATE INDEX IF NOT EXISTS idx_reviews_naver_scheduled ON reviews_naver(scheduled_reply_date) WHERE scheduled_reply_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_scheduled ON reviews_baemin(scheduled_reply_date) WHERE scheduled_reply_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_scheduled ON reviews_yogiyo(scheduled_reply_date) WHERE scheduled_reply_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_scheduled ON reviews_coupangeats(scheduled_reply_date) WHERE scheduled_reply_date IS NOT NULL;

-- 키워드 검색을 위한 GIN 인덱스
CREATE INDEX IF NOT EXISTS idx_reviews_naver_keywords ON reviews_naver USING GIN(inserted_keywords);
CREATE INDEX IF NOT EXISTS idx_reviews_baemin_keywords ON reviews_baemin USING GIN(inserted_keywords);
CREATE INDEX IF NOT EXISTS idx_reviews_yogiyo_keywords ON reviews_yogiyo USING GIN(inserted_keywords);
CREATE INDEX IF NOT EXISTS idx_reviews_coupangeats_keywords ON reviews_coupangeats USING GIN(inserted_keywords);

-- 기본값 설정 (기존 매장들에 대한)
UPDATE platform_stores 
SET 
    reply_tone = 'friendly',
    min_reply_length = 50,
    max_reply_length = 200
WHERE reply_tone IS NULL OR min_reply_length IS NULL OR max_reply_length IS NULL;

-- 매장별 기본 인사말 설정 (예시 - 실제 환경에서는 매장별로 커스터마이징)
UPDATE platform_stores 
SET 
    greeting_template = CASE 
        WHEN platform = 'naver' THEN '안녕하세요! {store_name}입니다 😊'
        WHEN platform = 'baemin' THEN '안녕하세요 {store_name}예요!'
        WHEN platform = 'yogiyo' THEN '안녕하세요! {store_name}에서 인사드려요'
        WHEN platform = 'coupangeats' THEN '안녕하세요 {store_name}입니다'
        ELSE '안녕하세요! {store_name}입니다'
    END,
    closing_template = CASE
        WHEN platform = 'naver' THEN '감사합니다. 또 방문해주세요! 🙏'
        WHEN platform = 'baemin' THEN '감사해요~ 다음에 또 주문해주세요!'
        WHEN platform = 'yogiyo' THEN '감사합니다! 또 이용해주세요'
        WHEN platform = 'coupangeats' THEN '감사합니다. 또 주문해주시길 바라요!'
        ELSE '감사합니다. 또 이용해주세요!'
    END
WHERE greeting_template IS NULL AND closing_template IS NULL;

-- 코멘트 추가
COMMENT ON COLUMN platform_stores.greeting_template IS '답글 첫인사 템플릿 ({store_name} 치환 가능, NULL시 AI가 자연스럽게 생성)';
COMMENT ON COLUMN platform_stores.closing_template IS '답글 마무리인사 템플릿 (NULL시 AI가 자연스럽게 생성)';
COMMENT ON COLUMN platform_stores.reply_tone IS '답글 톤앤매너 (friendly/formal/casual)';
COMMENT ON COLUMN platform_stores.min_reply_length IS '최소 답글 길이 (글자수, 기본 50)';
COMMENT ON COLUMN platform_stores.max_reply_length IS '최대 답글 길이 (글자수, 기본 200)';
COMMENT ON COLUMN platform_stores.brand_voice IS '매장 고유 목소리/특징 (AI 답글 생성시 참조)';
COMMENT ON COLUMN platform_stores.seo_keywords IS 'SEO 키워드 배열 (답글에 자연스럽게 포함)';

-- 리뷰 테이블 코멘트
COMMENT ON COLUMN reviews_naver.inserted_keywords IS '실제 답글에 삽입된 키워드들';
COMMENT ON COLUMN reviews_naver.reply_naturalness_score IS '답글 자연스러움 점수 (0.0-1.0)';
COMMENT ON COLUMN reviews_naver.scheduled_reply_date IS '답글 등록 예정일 (승인 대기용)';
COMMENT ON COLUMN reviews_naver.censorship_reason IS '검열 사유 (승인 필요한 경우)';