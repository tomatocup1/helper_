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
    const storeId = searchParams.get('store_id')
    const period = searchParams.get('period') || '7days'
    const specificDate = searchParams.get('date') // 일일 모드용 특정 날짜

    if (!storeId) {
      return NextResponse.json({ error: 'store_id parameter is required' }, { status: 400 })
    }

    const supabase = await createClient()

    // 매장 소유권 확인
    const { data: storeData, error: storeError } = await supabase
      .from('platform_stores')
      .select('id, store_name, platform_store_id')
      .eq('id', storeId)
      .eq('user_id', user.id)
      .eq('platform', 'naver')
      .single()

    if (storeError || !storeData) {
      return NextResponse.json({ error: 'Store not found or access denied' }, { status: 404 })
    }

    // 기간별 날짜 범위 계산
    let endDate = new Date()
    let startDate = new Date()

    if (period === 'daily' && specificDate) {
      // 일일 모드: 특정 날짜만 조회
      const targetDate = new Date(specificDate)
      startDate = targetDate
      endDate = targetDate
    } else {
      // 기간 모드: 기간별 범위 조회
      switch (period) {
        case '7days':
          startDate.setDate(endDate.getDate() - 7)
          break
        case '30days':
          startDate.setDate(endDate.getDate() - 30)
          break
        case '90days':
          startDate.setDate(endDate.getDate() - 90)
          break
        default:
          startDate.setDate(endDate.getDate() - 7)
      }
    }

    // 네이버 통계 데이터 조회
    const { data: statisticsData, error: statsError } = await supabase
      .from('statistics_naver')
      .select(`
        id,
        platform_store_id,
        date,
        place_inflow,
        place_inflow_change,
        reservation_order,
        reservation_order_change,
        smart_call,
        smart_call_change,
        review_registration,
        review_registration_change,
        inflow_channels,
        inflow_keywords,
        created_at,
        updated_at
      `)
      .eq('platform_store_id', storeId)
      .gte('date', startDate.toISOString().split('T')[0])
      .lte('date', endDate.toISOString().split('T')[0])
      .order('date', { ascending: false })

    if (statsError) {
      console.error('Statistics query error:', statsError)
      return NextResponse.json({ error: 'Failed to fetch statistics data' }, { status: 500 })
    }

    // 데이터 변환 (JSONB 파싱)
    const processedData = statisticsData?.map(item => ({
      ...item,
      inflow_channels: typeof item.inflow_channels === 'string' 
        ? JSON.parse(item.inflow_channels) 
        : item.inflow_channels || [],
      inflow_keywords: typeof item.inflow_keywords === 'string'
        ? JSON.parse(item.inflow_keywords)
        : item.inflow_keywords || []
    })) || []

    return NextResponse.json(processedData)

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
    const { store_id, date, statistics_data } = body

    if (!store_id || !statistics_data) {
      return NextResponse.json({ error: 'Missing required parameters' }, { status: 400 })
    }

    const supabase = await createClient()

    // 매장 소유권 확인
    const { data: storeData, error: storeError } = await supabase
      .from('platform_stores')
      .select('id, store_name')
      .eq('id', store_id)
      .eq('user_id', user.id)
      .eq('platform', 'naver')
      .single()

    if (storeError || !storeData) {
      return NextResponse.json({ error: 'Store not found or access denied' }, { status: 404 })
    }

    // 통계 데이터 저장/업데이트
    const targetDate = date || new Date().toISOString().split('T')[0]
    
    const upsertData = {
      platform_store_id: store_id,
      date: targetDate,
      place_inflow: statistics_data.place_inflow || 0,
      place_inflow_change: statistics_data.place_inflow_change,
      reservation_order: statistics_data.reservation_order || 0,
      reservation_order_change: statistics_data.reservation_order_change,
      smart_call: statistics_data.smart_call || 0,
      smart_call_change: statistics_data.smart_call_change,
      review_registration: statistics_data.review_registration || 0,
      review_registration_change: statistics_data.review_registration_change,
      inflow_channels: JSON.stringify(statistics_data.inflow_channels || []),
      inflow_keywords: JSON.stringify(statistics_data.inflow_keywords || []),
      updated_at: new Date().toISOString()
    }

    const { data, error } = await supabase
      .from('statistics_naver')
      .upsert(upsertData, {
        onConflict: 'platform_store_id,date'
      })
      .select()

    if (error) {
      console.error('Statistics upsert error:', error)
      return NextResponse.json({ error: 'Failed to save statistics data' }, { status: 500 })
    }

    return NextResponse.json({ success: true, data })

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}