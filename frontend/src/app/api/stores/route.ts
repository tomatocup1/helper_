import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { verifyAuth } from '@/lib/auth-utils'

export async function GET(request: NextRequest) {
  try {
    // 사용자 인증 확인
    const { user, error: authError } = await verifyAuth(request)
    if (authError || !user) {
      return NextResponse.json({ error: authError || 'Authentication failed' }, { status: 401 })
    }

    const searchParams = request.nextUrl.searchParams
    const platform = searchParams.get('platform') // naver, baemin, yogiyo 등

    const supabase = await createClient()

    let query = supabase
      .from('platform_stores')
      .select(`
        id,
        store_name,
        platform_store_id,
        platform,
        business_type,
        address,
        phone,
        crawling_enabled,
        auto_reply_enabled,
        last_crawled_at,
        created_at,
        updated_at
      `)
      .eq('user_id', user.id)
      .eq('is_active', true)
      .order('created_at', { ascending: false })

    // 플랫폼 필터링
    if (platform) {
      query = query.eq('platform', platform)
    }

    const { data: storesData, error: storesError } = await query

    if (storesError) {
      console.error('Stores query error:', storesError)
      return NextResponse.json({ error: 'Failed to fetch stores' }, { status: 500 })
    }

    return NextResponse.json(storesData || [])

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    // 사용자 인증 확인
    const { user, error: authError } = await verifyAuth(request)
    if (authError || !user) {
      return NextResponse.json({ error: authError || 'Authentication failed' }, { status: 401 })
    }

    const body = await request.json()
    const { 
      store_name,
      platform,
      platform_store_id,
      platform_url,
      business_type,
      address,
      phone,
      naver_email,
      naver_password
    } = body

    if (!store_name || !platform || !platform_store_id) {
      return NextResponse.json({ 
        error: 'store_name, platform, and platform_store_id are required' 
      }, { status: 400 })
    }

    const supabase = await createClient()

    // 중복 매장 확인
    const { data: existingStore } = await supabase
      .from('platform_stores')
      .select('id')
      .eq('user_id', user.id)
      .eq('platform', platform)
      .eq('platform_store_id', platform_store_id)
      .single()

    if (existingStore) {
      return NextResponse.json({ 
        error: 'Store with this platform_store_id already exists' 
      }, { status: 409 })
    }

    // 새 매장 생성
    const insertData = {
      user_id: user.id,
      store_name,
      platform,
      platform_store_id,
      platform_url,
      business_type,
      address,
      phone,
      naver_email: platform === 'naver' ? naver_email : null,
      naver_password: platform === 'naver' ? naver_password : null,
      crawling_enabled: true,
      auto_reply_enabled: false,
      is_active: true
    }

    const { data, error } = await supabase
      .from('platform_stores')
      .insert(insertData)
      .select()
      .single()

    if (error) {
      console.error('Store creation error:', error)
      return NextResponse.json({ error: 'Failed to create store' }, { status: 500 })
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}