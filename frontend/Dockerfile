# =====================================
# 프로덕션용 Next.js Frontend Dockerfile
# 멀티스테이지 빌드로 최적화
# =====================================

# Stage 1: Dependencies
FROM node:18-alpine AS dependencies

LABEL maintainer="storehelper-team"
LABEL version="1.0"

WORKDIR /app

# 패키지 파일 복사 및 종속성 설치
COPY package.json package-lock.json* ./
RUN npm ci --only=production --frozen-lockfile

# Stage 2: Builder
FROM node:18-alpine AS builder

WORKDIR /app

# 종속성 복사
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

# 환경변수 설정 (빌드타임)
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Next.js 빌드
RUN npm run build

# Stage 3: Production Runtime
FROM node:18-alpine AS production

WORKDIR /app

# 보안을 위한 non-root 사용자 생성
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 필요한 파일만 복사
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 사용자 전환
USER nextjs

# 포트 노출
EXPOSE 3000

# 환경변수
ENV PORT=3000
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# 애플리케이션 시작
CMD ["node", "server.js"]