/**
 * 환경 변수 유효성 검사 유틸리티
 */

interface SupabaseConfig {
  url: string;
  anonKey: string;
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Supabase 환경 변수 유효성 검사
 */
export function validateSupabaseConfig(): SupabaseConfig {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  
  const config: SupabaseConfig = {
    url: url || '',
    anonKey: anonKey || '',
    isValid: true,
    errors: [],
    warnings: []
  }

  // 필수 환경 변수 체크
  if (!url) {
    config.errors.push('NEXT_PUBLIC_SUPABASE_URL is missing')
    config.isValid = false
  }

  if (!anonKey) {
    config.errors.push('NEXT_PUBLIC_SUPABASE_ANON_KEY is missing')
    config.isValid = false
  }

  // URL 형식 검증
  if (url) {
    try {
      const urlObj = new URL(url)
      if (!urlObj.hostname.includes('supabase.co')) {
        config.warnings.push('URL does not appear to be a valid Supabase URL')
      }
    } catch {
      config.errors.push('NEXT_PUBLIC_SUPABASE_URL is not a valid URL')
      config.isValid = false
    }
  }

  // API Key 형식 검증
  if (anonKey) {
    if (!anonKey.startsWith('eyJ')) {
      config.errors.push('NEXT_PUBLIC_SUPABASE_ANON_KEY should be a JWT token starting with "eyJ"')
      config.isValid = false
    } else if (anonKey.includes('your_actual_anon_key_here')) {
      config.errors.push('NEXT_PUBLIC_SUPABASE_ANON_KEY appears to be a placeholder value')
      config.isValid = false
    }
  }

  // URL과 API Key 프로젝트 일치성 검증
  if (url && anonKey && anonKey.startsWith('eyJ')) {
    try {
      const payload = JSON.parse(atob(anonKey.split('.')[1]))
      const keyProject = payload.ref
      const urlProject = url.split('//')[1]?.split('.')[0]
      
      if (keyProject && urlProject && keyProject !== urlProject) {
        config.errors.push(
          `URL project (${urlProject}) does not match API key project (${keyProject})`
        )
        config.isValid = false
      }
    } catch {
      config.warnings.push('Could not validate API key format')
    }
  }

  return config
}

/**
 * 환경 변수 설정 상태를 콘솔에 출력
 */
export function logSupabaseConfigStatus(): void {
  const config = validateSupabaseConfig()
  
  console.log('\n🔧 Supabase Configuration Check')
  console.log('================================')
  
  if (config.isValid) {
    console.log('✅ Supabase configuration is valid')
  } else {
    console.log('❌ Supabase configuration has errors:')
    config.errors.forEach(error => {
      console.error(`   • ${error}`)
    })
  }
  
  if (config.warnings.length > 0) {
    console.log('\n⚠️  Warnings:')
    config.warnings.forEach(warning => {
      console.warn(`   • ${warning}`)
    })
  }
  
  if (!config.isValid) {
    console.log('\n📋 To fix these issues:')
    console.log('   1. Check your .env.local file')
    console.log('   2. Follow SUPABASE_FIX_GUIDE.md')
    console.log('   3. Restart your development server')
  }
  
  console.log('================================\n')
}

/**
 * 개발 환경에서 자동으로 설정 상태 체크
 */
export function initSupabaseConfigCheck(): void {
  if (process.env.NODE_ENV === 'development') {
    // 페이지 로드 시 한 번만 체크
    if (typeof window !== 'undefined' && !window.__supabase_config_checked) {
      window.__supabase_config_checked = true
      logSupabaseConfigStatus()
    }
  }
}

// 전역 타입 확장
declare global {
  interface Window {
    __supabase_config_checked?: boolean
  }
}