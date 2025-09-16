# =====================================
# Terraform 변수 정의
# Store Helper 베타 서비스용
# =====================================

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"  # 서울 리전
}

variable "project_name" {
  description = "프로젝트 이름 (리소스 태그용)"
  type        = string
  default     = "storehelper"
}

variable "environment" {
  description = "환경 구분 (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "도메인 이름 (선택사항)"
  type        = string
  default     = ""
}

# =====================================
# 시크릿 변수 (terraform.tfvars에서 설정)
# =====================================

variable "supabase_url" {
  description = "Supabase 프로젝트 URL"
  type        = string
  sensitive   = true
}

variable "supabase_anon_key" {
  description = "Supabase anon key"
  type        = string
  sensitive   = true
}

variable "supabase_service_key" {
  description = "Supabase service role key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API 키"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT 시크릿 키"
  type        = string
  sensitive   = true
}

variable "kakao_api_key" {
  description = "카카오 알림톡 API 키"
  type        = string
  sensitive   = true
  default     = ""
}

# =====================================
# 네트워킹 변수
# =====================================

variable "vpc_cidr" {
  description = "VPC CIDR 블록"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "사용할 가용 영역 수"
  type        = number
  default     = 2
}

# =====================================
# ECS 설정 변수
# =====================================

variable "frontend_desired_count" {
  description = "Frontend 서비스 원하는 태스크 수"
  type        = number
  default     = 2
}

variable "backend_desired_count" {
  description = "Backend 서비스 원하는 태스크 수"
  type        = number
  default     = 4
}

variable "frontend_cpu" {
  description = "Frontend 태스크 CPU 단위"
  type        = number
  default     = 512
}

variable "frontend_memory" {
  description = "Frontend 태스크 메모리 (MB)"
  type        = number
  default     = 1024
}

variable "backend_cpu" {
  description = "Backend 태스크 CPU 단위"
  type        = number
  default     = 1024
}

variable "backend_memory" {
  description = "Backend 태스크 메모리 (MB)"
  type        = number
  default     = 2048
}

# =====================================
# 데이터베이스 설정 변수
# =====================================

variable "db_instance_class" {
  description = "RDS 인스턴스 클래스"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS 할당된 스토리지 (GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "RDS 최대 할당된 스토리지 (GB)"
  type        = number
  default     = 100
}

variable "redis_node_type" {
  description = "ElastiCache Redis 노드 타입"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_clusters" {
  description = "Redis 캐시 클러스터 수"
  type        = number
  default     = 2
}

# =====================================
# 모니터링 및 로깅 변수
# =====================================

variable "log_retention_days" {
  description = "CloudWatch 로그 보존 일수"
  type        = number
  default     = 30
}

variable "enable_performance_insights" {
  description = "RDS Performance Insights 활성화"
  type        = bool
  default     = true
}

# =====================================
# 보안 설정 변수
# =====================================

variable "enable_deletion_protection" {
  description = "리소스 삭제 보호 활성화"
  type        = bool
  default     = false  # 베타 환경이므로 false
}

variable "backup_retention_period" {
  description = "데이터베이스 백업 보존 기간 (일)"
  type        = number
  default     = 7
}

# =====================================
# 비용 최적화 변수
# =====================================

variable "enable_spot_instances" {
  description = "ECS에서 Spot 인스턴스 사용"
  type        = bool
  default     = false
}

variable "auto_scaling_enabled" {
  description = "ECS 자동 스케일링 활성화"
  type        = bool
  default     = true
}

variable "min_capacity" {
  description = "자동 스케일링 최소 용량"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "자동 스케일링 최대 용량"
  type        = number
  default     = 10
}