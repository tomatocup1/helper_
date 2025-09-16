-- 배민 sub_type 필드 추가 마이그레이션
-- 2024-08-20: [음식배달], [포장주문] 등의 서비스 타입 저장을 위한 컬럼

ALTER TABLE platform_stores 
ADD COLUMN sub_type VARCHAR(20) DEFAULT NULL;

-- 인덱스 추가 (검색 성능 향상)
CREATE INDEX idx_platform_stores_sub_type ON platform_stores(sub_type);

-- 코멘트 추가
COMMENT ON COLUMN platform_stores.sub_type IS '배민 서비스 타입: 음식배달, 포장주문, B마트 등';