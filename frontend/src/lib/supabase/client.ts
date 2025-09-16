import { createBrowserClient } from '@supabase/ssr'
import type { Database } from '@/types/database'

export function createClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  // 환경 변수 유효성 검사
  if (!supabaseUrl || !supabaseAnonKey) {
    const missingVars = []
    if (!supabaseUrl) missingVars.push('NEXT_PUBLIC_SUPABASE_URL')
    if (!supabaseAnonKey) missingVars.push('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    
    console.error('❌ Missing Supabase environment variables:', missingVars.join(', '))
    console.error('📋 Please check your .env.local file and ensure these variables are set correctly')
    
    // 개발 환경에서는 경고만 출력하고 더미 클라이언트 반환
    if (process.env.NODE_ENV === 'development') {
      console.warn('🚧 Using fallback mode - authentication features will not work')
      console.warn('🔧 Follow SUPABASE_FIX_GUIDE.md to fix this issue')
      
      // 더미 클라이언트 반환 (실제로는 사용하지 않지만 에러 방지)
      return createBrowserClient<Database>(
        'https://dummy.supabase.co',
        'dummy-key'
      )
    }
    
    throw new Error(`Missing required Supabase environment variables: ${missingVars.join(', ')}`)
  }

  // API Key 형식 검증 (JWT 토큰인지 확인)
  if (!supabaseAnonKey.startsWith('eyJ')) {
    console.error('❌ Invalid Supabase API key format')
    console.error('📋 API key should be a JWT token starting with "eyJ"')
    console.error('🔧 Please check SUPABASE_FIX_GUIDE.md for proper key setup')
    
    if (process.env.NODE_ENV === 'development') {
      console.warn('🚧 Using fallback mode due to invalid API key format')
      return createBrowserClient<Database>(
        'https://dummy.supabase.co',
        'dummy-key'
      )
    }
  }

  // URL과 API Key 프로젝트 일치성 검증 (개발 환경에서만)
  if (process.env.NODE_ENV === 'development' && supabaseAnonKey.startsWith('eyJ')) {
    try {
      // JWT 페이로드 디코딩 (간단한 검증용)
      const payload = JSON.parse(atob(supabaseAnonKey.split('.')[1]))
      const keyProject = payload.ref
      const urlProject = supabaseUrl.split('//')[1]?.split('.')[0]
      
      if (keyProject && urlProject && keyProject !== urlProject) {
        console.error('❌ Supabase URL and API key mismatch detected!')
        console.error(`📍 URL project: ${urlProject}`)
        console.error(`🔑 Key project: ${keyProject}`)
        console.error('🔧 Please check SUPABASE_FIX_GUIDE.md to fix this issue')
      } else if (keyProject === urlProject) {
        console.log('✅ Supabase configuration looks correct')
      }
    } catch (error) {
      console.warn('⚠️  Could not validate API key format:', error)
    }
  }

  return createBrowserClient<Database>(
    supabaseUrl,
    supabaseAnonKey
  )
}