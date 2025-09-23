/**
 * 환경 설정 유틸리티
 * Vercel 환경변수를 중앙에서 관리
 */

// 백엔드 URL 가져오기
export const getBackendUrl = () => {
  // 클라이언트 사이드에서 실행되는 경우
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_BACKEND_URL || 'https://helper-backend-4ilp.onrender.com';
  }

  // 서버 사이드에서 실행되는 경우
  return process.env.NEXT_PUBLIC_BACKEND_URL || 'https://helper-backend-4ilp.onrender.com';
};

// API URL 가져오기
export const getApiUrl = () => {
  const backendUrl = getBackendUrl();
  return `${backendUrl}/api`;
};

// 환경 정보 (디버깅용)
export const logEnvironment = () => {
  console.log('Environment Variables Debug:');
  console.log('NEXT_PUBLIC_BACKEND_URL:', process.env.NEXT_PUBLIC_BACKEND_URL);
  console.log('NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL);
  console.log('NODE_ENV:', process.env.NODE_ENV);
  console.log('Computed Backend URL:', getBackendUrl());
  console.log('Computed API URL:', getApiUrl());
};

// 기본 설정 내보내기
export const config = {
  backendUrl: 'https://helper-backend-4ilp.onrender.com',
  apiUrl: 'https://helper-backend-4ilp.onrender.com/api',
};