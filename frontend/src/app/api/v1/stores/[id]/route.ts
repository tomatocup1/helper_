import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { encrypt } from '@/lib/encryption'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

interface UpdateStoreRequest {
  business_type?: string
  address?: string
  phone?: string
  platform_id: string
  platform_pw: string
}

// 매장 정보 조회
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
      .select('*')
      .eq('id', storeId)
      .single()

    if (storeError || !store) {
      return NextResponse.json(
        { error: 'Store not found or access denied' },
        { status: 404 }
      )
    }

    // 비밀번호는 보안상 제외하고 반환
    const { platform_pw, ...storeData } = store

    return NextResponse.json({
      success: true,
      store: storeData
    })

  } catch (error) {
    console.error('Store retrieval error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// 매장 정보 업데이트
export async function PUT(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const storeId = params.id
    const body: UpdateStoreRequest = await req.json()

    if (!storeId) {
      return NextResponse.json(
        { error: 'Store ID is required' },
        { status: 400 }
      )
    }

    const { business_type, address, phone, platform_id, platform_pw } = body

    // 필수 필드 검증
    if (!platform_id || !platform_pw) {
      return NextResponse.json(
        { error: 'Platform ID and password are required' },
        { status: 400 }
      )
    }

    // 매장 존재 여부 확인 (RLS로 사용자 권한 자동 확인)
    const { data: existingStore, error: checkError } = await supabase
      .from('platform_stores')
      .select('id, user_id')
      .eq('id', storeId)
      .single()

    if (checkError || !existingStore) {
      return NextResponse.json(
        { error: 'Store not found or access denied' },
        { status: 404 }
      )
    }

    // 비밀번호 암호화
    const encryptedPassword = await encrypt(platform_pw)

    // 매장 정보 업데이트
    const { data: updatedStore, error: updateError } = await supabase
      .from('platform_stores')
      .update({
        business_type: business_type || null,
        address: address || null,
        phone: phone || null,
        platform_id,
        platform_pw: encryptedPassword,
        updated_at: new Date().toISOString()
      })
      .eq('id', storeId)
      .select()
      .single()

    if (updateError) {
      console.error('Error updating store:', updateError)
      return NextResponse.json(
        { error: 'Failed to update store' },
        { status: 500 }
      )
    }

    // 비밀번호는 응답에서 제외
    const { platform_pw: _, ...responseData } = updatedStore

    return NextResponse.json({
      success: true,
      store: responseData,
      message: '매장 정보가 성공적으로 업데이트되었습니다.'
    })

  } catch (error) {
    console.error('Store update error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// 매장 삭제
export async function DELETE(
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

    // 매장 존재 여부 확인 (RLS로 사용자 권한 자동 확인)
    const { data: existingStore, error: checkError } = await supabase
      .from('platform_stores')
      .select('id, user_id, store_name')
      .eq('id', storeId)
      .single()

    if (checkError || !existingStore) {
      return NextResponse.json(
        { error: 'Store not found or access denied' },
        { status: 404 }
      )
    }

    // 매장 삭제 (CASCADE로 관련 데이터도 자동 삭제)
    const { error: deleteError } = await supabase
      .from('platform_stores')
      .delete()
      .eq('id', storeId)

    if (deleteError) {
      console.error('Error deleting store:', deleteError)
      return NextResponse.json(
        { error: 'Failed to delete store' },
        { status: 500 }
      )
    }

    // 사용자의 매장 수 감소
    const { data: user } = await supabase
      .from('users')
      .select('current_month_stores')
      .eq('id', existingStore.user_id)
      .single()

    if (user && user.current_month_stores > 0) {
      await supabase
        .from('users')
        .update({ 
          current_month_stores: user.current_month_stores - 1 
        })
        .eq('id', existingStore.user_id)
    }

    return NextResponse.json({
      success: true,
      message: `${existingStore.store_name} 매장이 성공적으로 삭제되었습니다.`
    })

  } catch (error) {
    console.error('Store deletion error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}