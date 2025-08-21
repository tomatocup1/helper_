# 🏗️ 시스템 아키텍처 문서

이 폴더는 Helper B 프로젝트의 시스템 설계와 기술 구조 관련 문서를 포함합니다.

## 📄 문서 목록

### 핵심 문서
- **[시스템 아키텍처](SYSTEM_ARCHITECTURE.md)** 
  - 마이크로서비스 구조
  - 기술 스택 선택 이유
  - 서버 간 통신 방식
  - 보안 아키텍처

- **[데이터베이스 설계](DATABASE_DESIGN.md)**
  - ERD (Entity Relationship Diagram)
  - 테이블 스키마 정의
  - 인덱스 전략
  - 데이터 정규화

- **[API 레퍼런스](API_REFERENCE.md)**
  - REST API 엔드포인트
  - 요청/응답 스키마
  - 인증 방식
  - 에러 코드

## 🔍 빠른 참조

### 서버 아키텍처
- **서버 A**: 크롤링 & AI 처리
- **서버 B**: API & 비즈니스 로직
- **서버 C**: 스케줄러 & 배치 작업

### 기술 스택
- **백엔드**: FastAPI, Python 3.11
- **프론트엔드**: Next.js 14, React 18
- **데이터베이스**: PostgreSQL (Supabase)
- **캐시**: Redis
- **큐**: Celery + RabbitMQ

## 🔗 관련 문서
- [개발 가이드](../04-development/DEVELOPMENT_GUIDE.md)
- [설치 가이드](../03-setup/SETUP.md)
- [프로젝트 개요](../02-progress/PROJECT_OVERVIEW.md)