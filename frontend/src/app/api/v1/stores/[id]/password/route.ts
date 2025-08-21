import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { decrypt } from '@/lib/encryption'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const storeId = params.id

    if (!storeId) {
      return NextResponse.json(
        { error: 'Store ID is required' },
        { status: 400 }
      )
    }

    // 매장 정보 조회 (RLS로 사용자 권한 자동 확인)
    const { data: store, error: storeError } = await supabase
      .from('platform_stores')
      .select('id, platform_pw, user_id')
      .eq('id', storeId)
      .single()

    if (storeError || !store) {
      return NextResponse.json(
        { error: 'Store not found or access denied' },
        { status: 404 }
      )
    }

    let decryptedPassword = ''
    
    // 비밀번호 복호화
    if (store.platform_pw) {
      try {
        decryptedPassword = await decrypt(store.platform_pw)
      } catch (decryptError) {
        console.error('Decryption failed:', decryptError)
        return NextResponse.json(
          { error: 'Failed to decrypt password' },
          { status: 500 }
        )
      }
    }

    return NextResponse.json({
      success: true,
      password: decryptedPassword
    })

  } catch (error) {
    console.error('Password retrieval error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}