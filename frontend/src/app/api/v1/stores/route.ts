import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { encrypt } from '@/lib/encryption'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

interface CreateStoreRequest {
  user_id: string
  platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
  platform_store_id: string
  store_name: string
  platform_url?: string
  platform_id: string
  platform_password: string
  business_type?: string
  address?: string
  phone?: string
}

export async function POST(req: NextRequest) {
  try {
    const body: CreateStoreRequest = await req.json()
    const { 
      user_id, 
      platform, 
      platform_store_id, 
      store_name, 
      platform_url,
      platform_id,
      platform_password,
      business_type,
      address,
      phone
    } = body

    // 입력 검증
    if (!user_id || !platform || !platform_store_id || !store_name || !platform_id || !platform_password) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // 사용자 인증 확인
    let { data: user, error: userError } = await supabase
      .from('users')
      .select('id, monthly_store_limit, current_month_stores')
      .eq('id', user_id)
      .single()

    // 개발 모드에서 test-user-id가 없으면 생성
    if (userError && user_id === 'test-user-id') {
      console.log('Creating test user for development...')
      const { data: newUser, error: createError } = await supabase
        .from('users')
        .insert({
          id: 'test-user-id',
          email: 'test@example.com',
          name: '테스트 사용자',
          monthly_store_limit: 100,
          current_month_stores: 0
        })
        .select('id, monthly_store_limit, current_month_stores')
        .single()
      
      if (createError) {
        console.log('Failed to create test user:', createError)
        return NextResponse.json(
          { error: 'Failed to create test user' },
          { status: 500 }
        )
      }
      user = newUser
    } else if (userError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // 매장 한도 확인 (개발 모드에서는 우회)
    const isDevelopment = process.env.NODE_ENV === 'development' || user_id === 'test-user-id'
    if (!isDevelopment && user.current_month_stores >= user.monthly_store_limit) {
      return NextResponse.json(
        { error: 'Monthly store limit exceeded' },
        { status: 403 }
      )
    }

    // 중복 매장 확인
    const { data: existingStore } = await supabase
      .from('platform_stores')
      .select('id')
      .eq('platform', platform)
      .eq('platform_store_id', platform_store_id)
      .eq('user_id', user_id)
      .single()

    if (existingStore) {
      return NextResponse.json(
        { error: 'Store already exists' },
        { status: 409 }
      )
    }

    // 비밀번호 암호화
    const encryptedPassword = await encrypt(platform_password)

    // 매장 정보를 데이터베이스에 저장
    const { data: savedStore, error: saveError } = await supabase
      .from('platform_stores')
      .insert({
        user_id,
        platform,
        platform_store_id,
        store_name,
        platform_url,
        platform_id,
        platform_pw: encryptedPassword,
        business_type,
        address,
        phone,
        crawling_enabled: true,
        is_active: true,
        platform_metadata: {}
      })
      .select()
      .single()

    if (saveError) {
      console.error('Error saving store:', saveError)
      return NextResponse.json(
        { error: 'Failed to save store' },
        { status: 500 }
      )
    }

    // 사용자의 이번 달 매장 수 업데이트
    await supabase
      .from('users')
      .update({ 
        current_month_stores: user.current_month_stores + 1 
      })
      .eq('id', user_id)

    return NextResponse.json({
      success: true,
      store: savedStore,
      message: '매장이 성공적으로 등록되었습니다.'
    })

  } catch (error) {
    console.error('Store creation error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}