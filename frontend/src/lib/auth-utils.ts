import { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export interface AuthUser {
  id: string
  email: string
  name?: string
  access_token?: string
}

export async function verifyAuth(request: NextRequest): Promise<{
  user: AuthUser | null
  error: string | null
}> {
  try {
    const authHeader = request.headers.get('authorization')
    const token = authHeader?.replace('Bearer ', '')

    if (!token) {
      return { user: null, error: 'Authentication token required' }
    }

    const supabase = await createClient()
    
    // 토큰으로 사용자 정보 조회
    const { data: { user }, error } = await supabase.auth.getUser(token)

    if (error || !user) {
      return { user: null, error: 'Invalid or expired token' }
    }

    // 사용자 프로필 정보 추가 조회
    const { data: profile } = await supabase
      .from('users')
      .select('name')
      .eq('id', user.id)
      .single()

    return {
      user: {
        id: user.id,
        email: user.email || '',
        name: profile?.name || user.user_metadata?.name || '',
        access_token: token
      },
      error: null
    }
  } catch (error) {
    console.error('Auth verification error:', error)
    return { user: null, error: 'Authentication failed' }
  }
}