import { NextRequest, NextResponse } from 'next/server'
import { reviewScheduler } from '@/services/review-scheduler'

export async function POST(req: NextRequest) {
  try {
    console.log('Starting review scheduler...')
    
    // 스케줄러 시작
    reviewScheduler.start()
    
    return NextResponse.json({
      success: true,
      message: 'Review scheduler started successfully',
      timestamp: new Date().toISOString()
    })
    
  } catch (error) {
    console.error('Error starting scheduler:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    )
  }
}

export async function GET(req: NextRequest) {
  try {
    // 스케줄러 상태 확인
    return NextResponse.json({
      success: true,
      status: 'running',
      message: 'Review scheduler status',
      timestamp: new Date().toISOString()
    })
    
  } catch (error) {
    console.error('Error checking scheduler status:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    )
  }
}