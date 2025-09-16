# =====================================
# RDS PostgreSQL 및 ElastiCache Redis
# 베타 서비스용 데이터베이스 구성
# =====================================

# DB 서브넷 그룹
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# DB 비밀번호 생성
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# RDS PostgreSQL 인스턴스
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-database"

  # 엔진 설정
  engine         = "postgres"
  engine_version = "15.7"
  instance_class = "db.t3.micro"

  # 스토리지 설정
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  # 데이터베이스 설정
  db_name  = "storehelper"
  username = "storehelper_admin"
  password = random_password.db_password.result

  # 네트워크 설정
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # 백업 설정
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  # 모니터링
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # 삭제 보호
  deletion_protection = false # 베타 환경이므로 false
  skip_final_snapshot = true

  # 성능 개선
  performance_insights_enabled = true

  tags = {
    Name = "${var.project_name}-database"
  }
}

# =====================================
# ElastiCache Redis
# =====================================

# Redis 서브넷 그룹
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# Redis 복제 그룹
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.project_name}-redis"
  description                = "Redis cluster for Store Helper"

  # 노드 설정
  node_type               = "cache.t3.micro"
  port                    = 6379
  parameter_group_name    = "default.redis7"

  # 복제 설정
  num_cache_clusters      = 2
  automatic_failover_enabled = true
  multi_az_enabled        = true

  # 네트워크 설정
  subnet_group_name       = aws_elasticache_subnet_group.main.name
  security_group_ids      = [aws_security_group.redis.id]

  # 백업 설정
  snapshot_retention_limit = 3
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:07:00"

  # 보안 설정
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result

  tags = {
    Name = "${var.project_name}-redis"
  }
}

# Redis 인증 토큰
resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

# =====================================
# RDS 모니터링 역할
# =====================================

resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# =====================================
# 시크릿 저장 (SSM Parameter Store)
# =====================================

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project_name}/database/password"
  type  = "SecureString"
  value = random_password.db_password.result

  tags = {
    Name = "${var.project_name}-db-password"
  }
}

resource "aws_ssm_parameter" "redis_auth" {
  name  = "/${var.project_name}/redis/auth_token"
  type  = "SecureString"
  value = random_password.redis_auth.result

  tags = {
    Name = "${var.project_name}-redis-auth"
  }
}