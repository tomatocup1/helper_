/**
 * 로컬 개발용 리버스 프록시 서버
 * 모든 서비스를 localhost:4000으로 통합
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const PORT = 4000;

// 프록시 설정
const services = {
  // Frontend (Next.js)
  '/': {
    target: 'http://localhost:3000',
    changeOrigin: true,
    ws: true, // WebSocket 지원 (Hot Module Reload)
  },
  
  // Admin Dashboard (별도 실행 시)
  '/admin': {
    target: 'http://localhost:3001',
    changeOrigin: true,
    ws: true,
  },
  
  // API 서버 (Next.js API Routes)
  '/api': {
    target: 'http://localhost:3000',
    changeOrigin: true,
  },
  
  // Python Backend 서버들 (실행 시)
  '/crawler': {
    target: 'http://localhost:8001',
    changeOrigin: true,
    pathRewrite: { '^/crawler': '' },
  },
  
  '/scheduler': {
    target: 'http://localhost:8002',
    changeOrigin: true,
    pathRewrite: { '^/scheduler': '' },
  },
  
  // Next.js 개발 서버 HMR
  '/_next/webpack-hmr': {
    target: 'http://localhost:3000',
    changeOrigin: true,
    ws: true,
  },
  
  // Next.js static files
  '/_next': {
    target: 'http://localhost:3000',
    changeOrigin: true,
  },
};

// 헬스체크 엔드포인트
app.get('/health', (req, res) => {
  res.status(200).send('Proxy server is healthy\n');
});

// 프록시 상태 확인 엔드포인트
app.get('/proxy-status', (req, res) => {
  const status = {
    proxyServer: 'running',
    port: PORT,
    services: Object.keys(services).map(path => ({
      path,
      target: services[path].target
    }))
  };
  res.json(status);
});

// 프록시 미들웨어 설정
// 순서가 중요: 더 구체적인 경로를 먼저 설정
const sortedPaths = Object.keys(services).sort((a, b) => {
  // 더 구체적인 경로를 먼저 처리
  if (a === '/') return 1;
  if (b === '/') return -1;
  return b.length - a.length;
});

sortedPaths.forEach(path => {
  const config = services[path];
  console.log(`📍 Setting up proxy: ${path} -> ${config.target}`);
  
  app.use(path, createProxyMiddleware({
    ...config,
    onError: (err, req, res) => {
      console.error(`❌ Proxy error for ${path}:`, err.message);
      res.status(502).json({
        error: 'Proxy Error',
        message: `Service at ${config.target} is not available`,
        path: req.path
      });
    },
    onProxyReq: (proxyReq, req, res) => {
      console.log(`🔄 [${new Date().toISOString()}] ${req.method} ${req.path} -> ${config.target}`);
    }
  }));
});

// 서버 시작
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║         🚀 Unified Proxy Server Started                     ║
╠════════════════════════════════════════════════════════════╣
║  Access all services at: http://localhost:${PORT}             ║
╠════════════════════════════════════════════════════════════╣
║  Service Endpoints:                                        ║
║  • Main App:        http://localhost:${PORT}/                 ║
║  • API:             http://localhost:${PORT}/api              ║
║  • Admin:           http://localhost:${PORT}/admin            ║
║  • Crawler:         http://localhost:${PORT}/crawler          ║
║  • Scheduler:       http://localhost:${PORT}/scheduler        ║
║  • Health Check:    http://localhost:${PORT}/health           ║
║  • Proxy Status:    http://localhost:${PORT}/proxy-status     ║
╠════════════════════════════════════════════════════════════╣
║  Backend Services (start separately):                      ║
║  • Frontend:        cd frontend && npm run dev             ║
║  • Python Backend:  cd backend && python main.py           ║
╚════════════════════════════════════════════════════════════╝
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('💤 SIGTERM signal received: closing HTTP server');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('\n💤 SIGINT signal received: closing HTTP server');
  process.exit(0);
});