-- AI Reply Settings Table
-- 사용자별 AI 답글 설정을 저장하는 테이블

CREATE TABLE IF NOT EXISTS public.ai_reply_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    auto_reply_enabled BOOLEAN DEFAULT FALSE,
    reply_tone VARCHAR(20) DEFAULT 'friendly',
    min_reply_length INTEGER DEFAULT 50,
    max_reply_length INTEGER DEFAULT 200,
    brand_voice TEXT DEFAULT '',
    greeting_template TEXT DEFAULT '',
    closing_template TEXT DEFAULT '',
    seo_keywords JSONB DEFAULT '[]'::jsonb,
    auto_approval_delay_hours INTEGER DEFAULT 48,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,

    -- 사용자당 하나의 설정만 허용
    CONSTRAINT unique_user_settings UNIQUE(user_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_ai_reply_settings_user_id ON public.ai_reply_settings(user_id);

-- RLS (Row Level Security) 정책 설정
ALTER TABLE public.ai_reply_settings ENABLE ROW LEVEL SECURITY;

-- 사용자는 자신의 설정만 조회/수정 가능
CREATE POLICY "Users can view own reply settings" ON public.ai_reply_settings
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own reply settings" ON public.ai_reply_settings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own reply settings" ON public.ai_reply_settings
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own reply settings" ON public.ai_reply_settings
    FOR DELETE USING (auth.uid() = user_id);

-- 업데이트 시간 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ai_reply_settings_updated_at
    BEFORE UPDATE ON public.ai_reply_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 기본 설정 삽입 (선택사항)
-- INSERT INTO public.ai_reply_settings (user_id, auto_reply_enabled, reply_tone)
-- VALUES ('test-user-id', false, 'friendly')
-- ON CONFLICT (user_id) DO NOTHING;