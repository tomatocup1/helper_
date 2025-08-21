import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function GET() {
  try {
    console.log('Checking database connection...')
    
    // users 테이블 확인
    const { data: users, error: usersError } = await supabase
      .from('users')
      .select('*')
      .limit(5)
    
    console.log('Users query result:', { users, usersError })
    
    // platform_stores 테이블 확인
    const { data: stores, error: storesError } = await supabase
      .from('platform_stores')
      .select('*')
      .limit(5)
    
    console.log('Stores query result:', { stores, storesError })
    
    return NextResponse.json({
      success: true,
      users: {
        count: users?.length || 0,
        data: users,
        error: usersError?.message
      },
      stores: {
        count: stores?.length || 0,
        data: stores,
        error: storesError?.message
      }
    })
    
  } catch (error) {
    console.error('Database check error:', error)
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    })
  }
}