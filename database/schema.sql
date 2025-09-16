-- 우리가게 도우미 데이터베이스 스키마
-- PostgreSQL 15+ / Supabase

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================
-- 1. users 테이블 - 사용자 관리
-- ==============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    
    -- 카카오 OAuth 정보
    kakao_id VARCHAR(100) UNIQUE,
    kakao_nickname VARCHAR(100),
    profile_image_url TEXT,
    
    -- 구독 정보
    subscription_plan VARCHAR(20) DEFAULT 'free' CHECK (subscription_plan IN ('free', 'basic', 'premium', 'enterprise')),
    subscription_start_date TIMESTAMP WITH TIME ZONE,
    subscription_end_date TIMESTAMP WITH TIME ZONE,
    
    -- 사용량 관리
    monthly_store_limit INTEGER DEFAULT 1,
    monthly_ai_reply_limit INTEGER DEFAULT 10,
    monthly_draft_limit INTEGER DEFAULT 30,
    current_month_stores INTEGER DEFAULT 0,
    current_month_ai_replies INTEGER DEFAULT 0,
    current_month_drafts INTEGER DEFAULT 0,
    usage_reset_date DATE,
    
    -- 추가 정보
    business_type VARCHAR(50),
    referral_code VARCHAR(20) UNIQUE,
    referred_by VARCHAR(20),
    
    -- 약관 동의
    terms_agreed BOOLEAN DEFAULT false,
    privacy_agreed BOOLEAN DEFAULT false,
    marketing_agreed BOOLEAN DEFAULT false,
    agreement_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- 메타데이터
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_kakao_id ON users(kakao_id);
CREATE INDEX idx_users_subscription_plan ON users(subscription_plan);

-- ==============================================
-- 2. platform_stores 테이블 - 플랫폼별 매장 관리
-- ==============================================
CREATE TABLE IF NOT EXISTS platform_stores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 매장 기본 정보
    store_name VARCHAR(255) NOT NULL,
    business_type VARCHAR(50),
    address TEXT,
    phone VARCHAR(20),
    business_registration_number VARCHAR(20),
    
    -- 플랫폼 정보
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('naver', 'baemin', 'yogiyo', 'coupangeats')),
    platform_store_id VARCHAR(100) NOT NULL,
    platform_url TEXT,
    
    -- 크롤링 설정
    crawling_enabled BOOLEAN DEFAULT true,
    crawling_interval_minutes INTEGER DEFAULT 360,
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    next_crawl_at TIMESTAMP WITH TIME ZONE,
    
    -- AI 답글 설정
    auto_reply_enabled BOOLEAN DEFAULT false,
    reply_style VARCHAR(20) DEFAULT 'friendly' CHECK (reply_style IN ('friendly', 'formal', 'casual')),
    custom_instructions TEXT,
    positive_reply_template TEXT,
    negative_reply_template TEXT,
    neutral_reply_template TEXT,
    
    -- 자동화 규칙
    negative_review_delay_hours INTEGER DEFAULT 48,
    auto_approve_positive BOOLEAN DEFAULT true,
    require_approval_negative BOOLEAN DEFAULT true,
    
    -- SEO/브랜딩
    branding_keywords JSONB,
    seo_keywords JSONB,
    
    -- 네이버 세션 관리
    naver_id VARCHAR(100),
    naver_password_encrypted TEXT,
    naver_session_active BOOLEAN DEFAULT false,
    naver_last_login TIMESTAMP WITH TIME ZONE,
    naver_device_registered BOOLEAN DEFAULT false,
    naver_login_attempts INTEGER DEFAULT 0,
    naver_profile_path TEXT,
    
    -- 상태 정보
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    verification_date TIMESTAMP WITH TIME ZONE,
    platform_metadata JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(platform, platform_store_id)
);

-- 인덱스
CREATE INDEX idx_platform_stores_user_id ON platform_stores(user_id);
CREATE INDEX idx_platform_stores_platform ON platform_stores(platform);
CREATE INDEX idx_platform_stores_next_crawl ON platform_stores(next_crawl_at);

-- ==============================================
-- 3. reviews_naver 테이블 - 네이버 리뷰 관리
-- ==============================================
CREATE TABLE IF NOT EXISTS reviews_naver (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    
    -- 리뷰 식별
    naver_review_id VARCHAR(100) UNIQUE NOT NULL,
    naver_review_url TEXT,
    
    -- 리뷰어 정보
    reviewer_name VARCHAR(100),
    reviewer_id VARCHAR(100),
    reviewer_level VARCHAR(50),
    
    -- 리뷰 내용
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    review_date TIMESTAMP WITH TIME ZONE,
    
    -- AI 분석
    sentiment VARCHAR(20) CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    sentiment_score DECIMAL(3,2),
    extracted_keywords JSONB,
    
    -- 답글 관리
    reply_text TEXT,
    reply_status VARCHAR(20) DEFAULT 'draft' CHECK (reply_status IN ('draft', 'pending_approval', 'approved', 'sent', 'failed')),
    ai_generated_reply TEXT,
    ai_model_used VARCHAR(50),
    ai_generation_time_ms INTEGER,
    ai_confidence_score DECIMAL(3,2),
    
    -- 승인 워크플로우
    requires_approval BOOLEAN DEFAULT false,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    
    -- 발송 정보
    reply_sent_at TIMESTAMP WITH TIME ZONE,
    reply_failed_at TIMESTAMP WITH TIME ZONE,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- 네이버 특화
    has_photos BOOLEAN DEFAULT false,
    photo_count INTEGER DEFAULT 0,
    
    -- 메타데이터
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_reviews_naver_store ON reviews_naver(platform_store_id);
CREATE INDEX idx_reviews_naver_sentiment ON reviews_naver(sentiment);
CREATE INDEX idx_reviews_naver_reply_status ON reviews_naver(reply_status);
CREATE INDEX idx_reviews_naver_review_date ON reviews_naver(review_date);

-- ==============================================
-- 4. reviews_baemin 테이블 - 배달의민족 리뷰 관리
-- ==============================================
CREATE TABLE IF NOT EXISTS reviews_baemin (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    
    -- 리뷰 식별
    baemin_review_id VARCHAR(100) UNIQUE NOT NULL,
    baemin_review_url TEXT,
    
    -- 리뷰어 정보
    reviewer_name VARCHAR(100),
    reviewer_id VARCHAR(100),
    reviewer_level VARCHAR(50),
    
    -- 리뷰 내용
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    review_date TIMESTAMP WITH TIME ZONE,
    
    -- 주문 정보
    order_menu_items JSONB,
    order_amount INTEGER,
    delivery_time_minutes INTEGER,
    delivery_rating INTEGER CHECK (delivery_rating >= 1 AND delivery_rating <= 5),
    food_rating INTEGER CHECK (food_rating >= 1 AND food_rating <= 5),
    packaging_rating INTEGER CHECK (packaging_rating >= 1 AND packaging_rating <= 5),
    
    -- AI 분석
    sentiment VARCHAR(20) CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    sentiment_score DECIMAL(3,2),
    extracted_keywords JSONB,
    menu_analysis JSONB,
    
    -- 답글 관리
    reply_text TEXT,
    reply_status VARCHAR(20) DEFAULT 'draft' CHECK (reply_status IN ('draft', 'pending_approval', 'approved', 'sent', 'failed')),
    ai_generated_reply TEXT,
    
    -- 승인 워크플로우
    requires_approval BOOLEAN DEFAULT false,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- 배민 특화
    has_photos BOOLEAN DEFAULT false,
    is_hidden BOOLEAN DEFAULT false,
    baemin_metadata JSONB,
    
    -- 메타데이터
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_reviews_baemin_store ON reviews_baemin(platform_store_id);
CREATE INDEX idx_reviews_baemin_sentiment ON reviews_baemin(sentiment);
CREATE INDEX idx_reviews_baemin_review_date ON reviews_baemin(review_date);

-- ==============================================
-- 5. review_draft_rules 테이블 - 리뷰 초안 생성 규칙
-- ==============================================
CREATE TABLE IF NOT EXISTS review_draft_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    
    -- 규칙 설정
    rule_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1,
    
    -- 생성 조건
    target_rating INTEGER DEFAULT 5 CHECK (target_rating >= 1 AND target_rating <= 5),
    min_text_length INTEGER DEFAULT 50,
    max_text_length INTEGER DEFAULT 300,
    
    -- 키워드 풀
    positive_keywords JSONB,
    menu_keywords JSONB,
    service_keywords JSONB,
    atmosphere_keywords JSONB,
    
    -- 템플릿
    template_patterns JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_review_draft_rules_store ON review_draft_rules(platform_store_id);

-- ==============================================
-- 6. review_drafts 테이블 - 리뷰 초안
-- ==============================================
CREATE TABLE IF NOT EXISTS review_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES review_draft_rules(id),
    
    -- 생성된 초안
    draft_text TEXT NOT NULL,
    suggested_rating INTEGER CHECK (suggested_rating >= 1 AND suggested_rating <= 5),
    used_keywords JSONB,
    
    -- 컨텍스트
    visit_date DATE,
    visit_context VARCHAR(100),
    ordered_menu_items JSONB,
    
    -- 사용 추적
    usage_status VARCHAR(20) DEFAULT 'generated' CHECK (usage_status IN ('generated', 'viewed', 'copied', 'posted', 'ignored')),
    viewed_at TIMESTAMP WITH TIME ZONE,
    copied_at TIMESTAMP WITH TIME ZONE,
    
    -- 실제 리뷰 정보
    actual_posted BOOLEAN DEFAULT false,
    actual_platform VARCHAR(20),
    actual_rating INTEGER,
    actual_review_text TEXT,
    posted_at TIMESTAMP WITH TIME ZONE,
    
    -- 개인정보 동의
    privacy_consent BOOLEAN DEFAULT false,
    marketing_consent BOOLEAN DEFAULT false,
    consent_ip_address INET,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_review_drafts_store ON review_drafts(platform_store_id);
CREATE INDEX idx_review_drafts_usage ON review_drafts(usage_status);

-- ==============================================
-- 7. analytics 테이블 - 통계 데이터
-- ==============================================
CREATE TABLE IF NOT EXISTS analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_store_id UUID NOT NULL REFERENCES platform_stores(id) ON DELETE CASCADE,
    
    -- 기간 정보
    date DATE NOT NULL,
    period_type VARCHAR(20) DEFAULT 'daily' CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    
    -- 리뷰 통계
    total_reviews INTEGER DEFAULT 0,
    new_reviews INTEGER DEFAULT 0,
    average_rating DECIMAL(3,2),
    rating_distribution JSONB,
    
    -- 감정 분석
    positive_reviews INTEGER DEFAULT 0,
    negative_reviews INTEGER DEFAULT 0,
    neutral_reviews INTEGER DEFAULT 0,
    sentiment_trend DECIMAL(3,2),
    
    -- 답글 통계
    total_replies INTEGER DEFAULT 0,
    ai_generated_replies INTEGER DEFAULT 0,
    manual_replies INTEGER DEFAULT 0,
    average_reply_time_hours DECIMAL(5,2),
    reply_rate DECIMAL(3,2),
    
    -- 키워드 분석
    top_positive_keywords JSONB,
    top_negative_keywords JSONB,
    trending_keywords JSONB,
    
    -- SEO 성과
    seo_keyword_coverage DECIMAL(3,2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(platform_store_id, date, period_type)
);

-- 인덱스
CREATE INDEX idx_analytics_store_date ON analytics(platform_store_id, date);
CREATE INDEX idx_analytics_period ON analytics(period_type);

-- ==============================================
-- 8. error_logs 테이블 - 에러 로그
-- ==============================================
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 에러 분류
    error_category VARCHAR(50) CHECK (error_category IN ('crawling', 'ai_generation', 'api', 'database')),
    error_type VARCHAR(100),
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- 에러 정보
    error_message TEXT,
    error_details JSONB,
    
    -- 관련 정보
    user_id UUID REFERENCES users(id),
    platform_store_id UUID REFERENCES platform_stores(id),
    related_table VARCHAR(50),
    related_record_id UUID,
    
    -- 시스템 정보
    server_name VARCHAR(50),
    service_name VARCHAR(50),
    function_name VARCHAR(100),
    
    -- 해결 정보
    is_resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_error_logs_category ON error_logs(error_category);
CREATE INDEX idx_error_logs_severity ON error_logs(severity);
CREATE INDEX idx_error_logs_resolved ON error_logs(is_resolved);
CREATE INDEX idx_error_logs_created ON error_logs(created_at);

-- ==============================================
-- 9. browser_profiles 테이블 - 브라우저 프로필 관리
-- ==============================================
CREATE TABLE IF NOT EXISTS browser_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 프로필 정보
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('naver', 'baemin', 'yogiyo', 'coupangeats')),
    profile_name VARCHAR(255) NOT NULL,
    
    -- 브라우저 설정
    profile_path TEXT,
    session_data TEXT,
    cookies_data TEXT,
    user_agent TEXT,
    
    -- 상태 정보
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP WITH TIME ZONE,
    session_valid_until TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, platform, profile_name)
);

-- 인덱스
CREATE INDEX idx_browser_profiles_user ON browser_profiles(user_id);
CREATE INDEX idx_browser_profiles_platform ON browser_profiles(platform);

-- ==============================================
-- Supabase Auth 통합을 위한 트리거
-- ==============================================

-- auth.users와 public.users 동기화 함수
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, email, name)
  VALUES (
    new.id,
    new.email,
    COALESCE(new.raw_user_meta_data->>'name', split_part(new.email, '@', 1))
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 트리거 생성
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ==============================================
-- RLS (Row Level Security) 정책
-- ==============================================

-- users 테이블 RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile" ON users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users
  FOR UPDATE USING (auth.uid() = id);

-- platform_stores 테이블 RLS
ALTER TABLE platform_stores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own stores" ON platform_stores
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own stores" ON platform_stores
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own stores" ON platform_stores
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own stores" ON platform_stores
  FOR DELETE USING (auth.uid() = user_id);

-- reviews_naver 테이블 RLS
ALTER TABLE reviews_naver ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own reviews" ON reviews_naver
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM platform_stores
      WHERE platform_stores.id = reviews_naver.platform_store_id
      AND platform_stores.user_id = auth.uid()
    )
  );

-- analytics 테이블 RLS
ALTER TABLE analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analytics" ON analytics
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM platform_stores
      WHERE platform_stores.id = analytics.platform_store_id
      AND platform_stores.user_id = auth.uid()
    )
  );

-- ==============================================
-- 초기 데이터 (선택사항)
-- ==============================================

-- 기본 리뷰 초안 규칙 템플릿
INSERT INTO review_draft_rules (id, platform_store_id, rule_name, positive_keywords, template_patterns)
VALUES (
  uuid_generate_v4(),
  NULL, -- 전역 템플릿
  '기본 템플릿',
  '["맛있어요", "친절해요", "깨끗해요", "분위기 좋아요", "재방문 의사 있어요"]'::jsonb,
  '["{메뉴}가 정말 맛있었어요. {서비스} 분위기도 {분위기}!", "오늘 {메뉴} 먹었는데 {평가}! {재방문}"]'::jsonb
) ON CONFLICT DO NOTHING;