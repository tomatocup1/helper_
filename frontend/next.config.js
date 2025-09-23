/** @type {import('next').NextConfig} */
const nextConfig = {
  // 환경변수 설정
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'https://helper-backend-4ilp.onrender.com',
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://helper-backend-4ilp.onrender.com/api',
  },
  // 런타임 설정
  publicRuntimeConfig: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'https://helper-backend-4ilp.onrender.com',
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://helper-backend-4ilp.onrender.com/api',
  },
};

module.exports = nextConfig;