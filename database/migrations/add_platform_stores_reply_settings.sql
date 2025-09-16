-- ============================================
-- 답글 설정 시스템 마이그레이션
-- platform_stores 테이블 기반 답글 설정 구현
-- 2025-08-27: 매장별 AI 답글 설정 시스템 추가
-- ============================================

-- platform_stores 테이블에 새 답글 설정 컬럼 추가 (IF NOT EXISTS로 안전하게)
ALTER TABLE platform_stores 
ADD COLUMN IF NOT EXISTS greeting_template VARCHAR(200),
ADD COLUMN IF NOT EXISTS closing_template VARCHAR(200),
ADD COLUMN IF NOT EXISTS reply_tone VARCHAR(20) DEFAULT 'friendly',
ADD COLUMN IF NOT EXISTS min_reply_length INTEGER DEFAULT 50,
ADD COLUMN IF NOT EXISTS max_reply_length INTEGER DEFAULT 200,
ADD COLUMN IF NOT EXISTS brand_voice TEXT,
ADD COLUMN IF NOT EXISTS auto_approval_delay_hours INTEGER DEFAULT 48;

-- seo_keywords 처리 (이미 JSONB 타입인 경우만 처리)
DO $$ 
BEGIN
    -- seo_keywords 컬럼이 없으면 TEXT 배열로 추가
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='platform_stores' AND column_name='seo_keywords') THEN
        ALTER TABLE platform_stores ADD COLUMN seo_keywords TEXT[];
    END IF;
    
    -- 이미 JSONB 타입이면 TEXT 배열로 변환
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='platform_stores' 
               AND column_name='seo_keywords' 
               AND data_type='jsonb') THEN
        
        -- 임시 컬럼 생성
        ALTER TABLE platform_stores ADD COLUMN IF NOT EXISTS seo_keywords_temp TEXT[];
        
        -- 데이터 복사 (JSONB → TEXT[])
        UPDATE platform_stores 
        SET seo_keywords_temp = 
            CASE 
                WHEN seo_keywords IS NULL THEN NULL
                WHEN jsonb_typeof(seo_keywords) = 'array' THEN 
                    ARRAY(SELECT value::text FROM jsonb_array_elements_text(seo_keywords) AS value)
                ELSE ARRAY[seo_keywords::text]
            END;
        
        -- 기존 컬럼 삭제하고 임시 컬럼 이름 변경
        ALTER TABLE platform_stores DROP COLUMN seo_keywords;
        ALTER TABLE platform_stores RENAME COLUMN seo_keywords_temp TO seo_keywords;
    END IF;
END $$;

-- 리뷰 테이블들에 새 필드 추가 (IF NOT EXISTS로 안전하게)
-- reviews_naver 테이블
ALTER TABLE reviews_naver 
ADD COLUMN IF NOT EXISTS inserted_keywords TEXT[],
ADD COLUMN IF NOT EXISTS reply_naturalness_score FLOAT,
ADD COLUMN IF NOT EXISTS scheduled_reply_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS censorship_reason TEXT;

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

-- 기본값 설정 (기존 매장들을 위한)
UPDATE platform_stores 
SET 
    reply_tone = COALESCE(reply_tone, 'friendly'),
    min_reply_length = COALESCE(min_reply_length, 50),
    max_reply_length = COALESCE(max_reply_length, 200),
    auto_approval_delay_hours = COALESCE(auto_approval_delay_hours, 48)
WHERE reply_tone IS NULL OR min_reply_length IS NULL OR max_reply_length IS NULL OR auto_approval_delay_hours IS NULL;

-- 기본 인사말 설정 (아직 설정이 없는 경우만)
UPDATE platform_stores 
SET 
    greeting_template = CASE 
        WHEN platform = 'naver' AND greeting_template IS NULL THEN '안녕하세요! {store_name}입니다 😊'
        WHEN platform = 'baemin' AND greeting_template IS NULL THEN '안녕하세요 {store_name}예요!'
        WHEN platform = 'yogiyo' AND greeting_template IS NULL THEN '안녕하세요! {store_name}에서 인사드려요'
        WHEN platform = 'coupangeats' AND greeting_template IS NULL THEN '안녕하세요 {store_name}입니다'
        ELSE greeting_template
    END,
    closing_template = CASE
        WHEN platform = 'naver' AND closing_template IS NULL THEN '감사합니다. 또 방문해주세요! 🙏'
        WHEN platform = 'baemin' AND closing_template IS NULL THEN '감사해요~ 다음에 또 주문해주세요!'
        WHEN platform = 'yogiyo' AND closing_template IS NULL THEN '감사합니다! 또 이용해주세요'
        WHEN platform = 'coupangeats' AND closing_template IS NULL THEN '감사합니다. 또 주문해주시길 바라요!'
        ELSE closing_template
    END
WHERE greeting_template IS NULL OR closing_template IS NULL;

-- 성능 최적화를 위한 인덱스 추가 (IF NOT EXISTS로 안전하게)
CREATE INDEX IF NOT EXISTS idx_platform_stores_greeting ON platform_stores(greeting_template) WHERE greeting_template IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_platform_stores_closing ON platform_stores(closing_template) WHERE closing_template IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_platform_stores_reply_tone ON platform_stores(reply_tone);
CREATE INDEX IF NOT EXISTS idx_platform_stores_auto_reply ON platform_stores(auto_reply_enabled);

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

-- SEO 키워드를 위한 GIN 인덱스
CREATE INDEX IF NOT EXISTS idx_platform_stores_seo_keywords ON platform_stores USING GIN(seo_keywords);

-- 컬럼 코멘트 추가
COMMENT ON COLUMN platform_stores.greeting_template IS '답글 첫인사 템플릿 ({store_name} 치환 가능, NULL시 AI가 자연스럽게 생성)';
COMMENT ON COLUMN platform_stores.closing_template IS '답글 마무리인사 템플릿 (NULL시 AI가 자연스럽게 생성)';
COMMENT ON COLUMN platform_stores.reply_tone IS '답글 톤앤매너 (friendly/formal/casual)';
COMMENT ON COLUMN platform_stores.min_reply_length IS '최소 답글 길이 (글자수, 기본 50)';
COMMENT ON COLUMN platform_stores.max_reply_length IS '최대 답글 길이 (글자수, 기본 200)';
COMMENT ON COLUMN platform_stores.brand_voice IS '매장 고유 목소리/특징 (AI 답글 생성시 참조)';
COMMENT ON COLUMN platform_stores.seo_keywords IS 'SEO 키워드 배열 (답글에 자연스럽게 포함)';
COMMENT ON COLUMN platform_stores.auto_approval_delay_hours IS '자동 승인 대기 시간 (시간, 기본 48)';

-- 완료 메시지
DO $$ 
BEGIN
    RAISE NOTICE '답글 설정 시스템 마이그레이션이 성공적으로 완료되었습니다.';
    RAISE NOTICE '매장별 답글 설정 기능이 활성화되었습니다.';
END $$;