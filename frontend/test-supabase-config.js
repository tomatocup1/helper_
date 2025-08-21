/**
 * Supabase 설정 테스트 스크립트
 * 
 * 사용법:
 * node test-supabase-config.js
 */

const fs = require('fs');
const path = require('path');

// .env.local 파일 읽기
function loadEnvFile() {
  const envPath = path.join(__dirname, '.env.local');
  
  if (!fs.existsSync(envPath)) {
    console.error('❌ .env.local 파일을 찾을 수 없습니다.');
    return null;
  }
  
  const envContent = fs.readFileSync(envPath, 'utf-8');
  const env = {};
  
  envContent.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const [key, ...valueParts] = trimmed.split('=');
      if (key && valueParts.length > 0) {
        env[key.trim()] = valueParts.join('=').trim();
      }
    }
  });
  
  return env;
}

// JWT 토큰 디코딩
function decodeJWT(token) {
  try {
    const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64').toString());
    return payload;
  } catch (error) {
    return null;
  }
}

// Supabase 설정 검증
function validateSupabaseConfig() {
  console.log('🔧 Supabase 설정 검증을 시작합니다...\n');
  
  const env = loadEnvFile();
  if (!env) return;
  
  const url = env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  
  let hasErrors = false;
  
  // URL 체크
  console.log('📍 Supabase URL 체크:');
  if (!url) {
    console.error('   ❌ NEXT_PUBLIC_SUPABASE_URL이 설정되지 않았습니다.');
    hasErrors = true;
  } else if (url.includes('your_actual')) {
    console.error('   ❌ NEXT_PUBLIC_SUPABASE_URL이 플레이스홀더 값입니다.');
    console.error('      실제 Supabase 프로젝트 URL로 교체해주세요.');
    hasErrors = true;
  } else {
    console.log('   ✅ URL이 설정되어 있습니다:', url);
    
    // 프로젝트 ID 추출
    const urlMatch = url.match(/https:\/\/([^.]+)\.supabase\.co/);
    if (urlMatch) {
      const projectId = urlMatch[1];
      console.log('   📋 프로젝트 ID:', projectId);
    }
  }
  
  // API Key 체크
  console.log('\n🔑 API Key 체크:');
  if (!anonKey) {
    console.error('   ❌ NEXT_PUBLIC_SUPABASE_ANON_KEY가 설정되지 않았습니다.');
    hasErrors = true;
  } else if (anonKey.includes('your_actual')) {
    console.error('   ❌ NEXT_PUBLIC_SUPABASE_ANON_KEY가 플레이스홀더 값입니다.');
    console.error('      실제 Supabase 프로젝트의 anon key로 교체해주세요.');
    hasErrors = true;
  } else if (!anonKey.startsWith('eyJ')) {
    console.error('   ❌ API Key 형식이 올바르지 않습니다. JWT 토큰이어야 합니다.');
    hasErrors = true;
  } else {
    console.log('   ✅ API Key가 설정되어 있습니다.');
    
    // JWT 토큰 디코딩
    const payload = decodeJWT(anonKey);
    if (payload) {
      console.log('   📋 키 정보:');
      console.log('      - 발급자:', payload.iss);
      console.log('      - 프로젝트 ID:', payload.ref);
      console.log('      - 역할:', payload.role);
      console.log('      - 만료일:', new Date(payload.exp * 1000).toLocaleString());
      
      // URL과 키 프로젝트 ID 일치성 체크
      if (url && payload.ref) {
        const urlMatch = url.match(/https:\/\/([^.]+)\.supabase\.co/);
        if (urlMatch) {
          const urlProjectId = urlMatch[1];
          if (urlProjectId !== payload.ref) {
            console.error('\n❌ URL과 API Key의 프로젝트 ID가 일치하지 않습니다!');
            console.error(`   URL 프로젝트: ${urlProjectId}`);
            console.error(`   키 프로젝트: ${payload.ref}`);
            hasErrors = true;
          } else {
            console.log('\n✅ URL과 API Key의 프로젝트 ID가 일치합니다.');
          }
        }
      }
    }
  }
  
  // 결과 출력
  console.log('\n================================================');
  if (hasErrors) {
    console.log('❌ Supabase 설정에 오류가 있습니다.');
    console.log('\n🔧 수정 방법:');
    console.log('   1. SUPABASE_FIX_GUIDE.md 파일을 참고하세요.');
    console.log('   2. Supabase 대시보드에서 올바른 API 키를 확인하세요.');
    console.log('   3. .env.local 파일을 수정하세요.');
    console.log('   4. 개발 서버를 재시작하세요.');
  } else {
    console.log('✅ Supabase 설정이 올바릅니다!');
    console.log('\n이제 회원가입과 로그인이 정상적으로 작동할 것입니다.');
  }
  console.log('================================================');
}

// 스크립트 실행
validateSupabaseConfig();