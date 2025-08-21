import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { decrypt } from '@/lib/encryption'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

interface DecryptRequest {
  store_id: string
  admin_key?: string
}

export async function POST(req: NextRequest) {
  try {
    const body: DecryptRequest = await req.json()
    const { store_id, admin_key } = body

    // 관리자 키 검증 (환경변수에서 설정)
    const ADMIN_KEY = process.env.ADMIN_DECRYPT_KEY || 'admin-secret-key-2024'
    
    if (admin_key !== ADMIN_KEY) {
      return NextResponse.json(
        { error: 'Unauthorized: Invalid admin key' },
        { status: 401 }
      )
    }

    if (!store_id) {
      return NextResponse.json(
        { error: 'store_id is required' },
        { status: 400 }
      )
    }

    // 매장 정보 조회
    const { data: store, error: storeError } = await supabase
      .from('platform_stores')
      .select('id, store_name, platform, platform_id, platform_pw, user_id')
      .eq('id', store_id)
      .single()

    if (storeError || !store) {
      return NextResponse.json(
        { error: 'Store not found' },
        { status: 404 }
      )
    }

    let decryptedPassword = null
    
    // 비밀번호 복호화
    if (store.platform_pw) {
      try {
        decryptedPassword = await decrypt(store.platform_pw)
      } catch (decryptError) {
        console.error('Decryption failed:', decryptError)
        decryptedPassword = 'DECRYPTION_FAILED'
      }
    }

    return NextResponse.json({
      success: true,
      store_info: {
        id: store.id,
        store_name: store.store_name,
        platform: store.platform,
        platform_id: store.platform_id,
        platform_password: decryptedPassword, // 복호화된 비밀번호
        user_id: store.user_id
      }
    })

  } catch (error) {
    console.error('Admin decrypt error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}