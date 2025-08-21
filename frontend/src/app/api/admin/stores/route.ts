import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const admin_key = searchParams.get('admin_key')

    // 관리자 키 검증
    const ADMIN_KEY = process.env.ADMIN_DECRYPT_KEY || 'admin-secret-key-2024'
    
    if (admin_key !== ADMIN_KEY) {
      return NextResponse.json(
        { error: 'Unauthorized: Invalid admin key' },
        { status: 401 }
      )
    }

    // 모든 매장 정보 조회 (비밀번호는 암호화된 상태로)
    const { data: stores, error } = await supabase
      .from('platform_stores')
      .select(`
        id,
        store_name,
        platform,
        platform_id,
        platform_store_id,
        platform_url,
        crawling_enabled,
        is_active,
        created_at,
        updated_at,
        user_id,
        users(email, name)
      `)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Database error:', error)
      return NextResponse.json(
        { error: 'Failed to fetch stores' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      stores: stores || [],
      total: stores?.length || 0
    })

  } catch (error) {
    console.error('Admin stores error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}