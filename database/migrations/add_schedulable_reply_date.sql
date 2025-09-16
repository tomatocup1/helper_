-- 24시간 답글 지연 시스템을 위한 schedulable_reply_date 컬럼 추가
-- 2025-01-XX: AI 답글 스케줄링 시스템 구현

-- 1. reviews_naver 테이블에 schedulable_reply_date 컬럼 추가
ALTER TABLE reviews_naver 
ADD COLUMN schedulable_reply_date TIMESTAMP NULL;

-- 2. reviews_baemin 테이블에 schedulable_reply_date 컬럼 추가
ALTER TABLE reviews_baemin 
ADD COLUMN schedulable_reply_date TIMESTAMP NULL;

-- 3. reviews_yogiyo 테이블에 schedulable_reply_date 컬럼 추가
ALTER TABLE reviews_yogiyo 
ADD COLUMN schedulable_reply_date TIMESTAMP NULL;

-- 4. reviews_coupangeats 테이블에 schedulable_reply_date 컬럼 추가
ALTER TABLE reviews_coupangeats 
ADD COLUMN schedulable_reply_date TIMESTAMP NULL;

-- 인덱스 생성 (스케줄러에서 효율적인 조회를 위함)
CREATE INDEX idx_reviews_naver_schedulable_reply_date ON reviews_naver(schedulable_reply_date) WHERE schedulable_reply_date IS NOT NULL;
CREATE INDEX idx_reviews_baemin_schedulable_reply_date ON reviews_baemin(schedulable_reply_date) WHERE schedulable_reply_date IS NOT NULL;
CREATE INDEX idx_reviews_yogiyo_schedulable_reply_date ON reviews_yogiyo(schedulable_reply_date) WHERE schedulable_reply_date IS NOT NULL;
CREATE INDEX idx_reviews_coupangeats_schedulable_reply_date ON reviews_coupangeats(schedulable_reply_date) WHERE schedulable_reply_date IS NOT NULL;

-- 스케줄러 조회를 위한 복합 인덱스
CREATE INDEX idx_reviews_naver_scheduler ON reviews_naver(reply_status, schedulable_reply_date) WHERE reply_status = 'approved';
CREATE INDEX idx_reviews_baemin_scheduler ON reviews_baemin(reply_status, schedulable_reply_date) WHERE reply_status = 'approved';
CREATE INDEX idx_reviews_yogiyo_scheduler ON reviews_yogiyo(reply_status, schedulable_reply_date) WHERE reply_status = 'approved';
CREATE INDEX idx_reviews_coupangeats_scheduler ON reviews_coupangeats(reply_status, schedulable_reply_date) WHERE reply_status = 'approved';

-- 컬럼 설명 추가
COMMENT ON COLUMN reviews_naver.schedulable_reply_date IS '답글 게시 가능 날짜/시간 (AUTO: review_date+1일, 나머지: review_date+2일)';
COMMENT ON COLUMN reviews_baemin.schedulable_reply_date IS '답글 게시 가능 날짜/시간 (AUTO: review_date+1일, 나머지: review_date+2일)';
COMMENT ON COLUMN reviews_yogiyo.schedulable_reply_date IS '답글 게시 가능 날짜/시간 (AUTO: review_date+1일, 나머지: review_date+2일)';
COMMENT ON COLUMN reviews_coupangeats.schedulable_reply_date IS '답글 게시 가능 날짜/시간 (AUTO: review_date+1일, 나머지: review_date+2일)';