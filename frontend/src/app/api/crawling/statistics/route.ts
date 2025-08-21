import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { verifyAuth } from '@/lib/auth-utils'
import { spawn } from 'child_process'
import path from 'path'

export async function POST(request: NextRequest) {
  try {
    // 사용자 인증 확인
    const { user, error: authError } = await verifyAuth(request)
    if (authError || !user) {
      return NextResponse.json({ error: authError || 'Authentication failed' }, { status: 401 })
    }

    const body = await request.json()
    const { store_id, platform_store_id, date } = body

    if (!store_id) {
      return NextResponse.json({ error: 'store_id is required' }, { status: 400 })
    }

    const supabase = await createClient()

    // 매장 정보 및 네이버 계정 정보 조회
    const { data: storeData, error: storeError } = await supabase
      .from('platform_stores')
      .select(`
        id,
        store_name,
        platform_store_id,
        naver_email,
        naver_password,
        user_id
      `)
      .eq('id', store_id)
      .eq('user_id', user.id)
      .eq('platform', 'naver')
      .single()

    if (storeError || !storeData) {
      return NextResponse.json({ error: 'Store not found or access denied' }, { status: 404 })
    }

    if (!storeData.naver_email || !storeData.naver_password) {
      return NextResponse.json({ 
        error: 'Naver account credentials not configured for this store' 
      }, { status: 400 })
    }

    // 크롤링 작업 기록
    const { data: jobData, error: jobError } = await supabase
      .from('crawling_jobs')
      .insert({
        user_id: user.id,
        platform_store_id: store_id,
        job_type: 'statistics',
        platform: 'naver',
        status: 'pending',
        started_at: new Date().toISOString(),
        job_config: {
          target_date: date || new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 기본값: 전날
          store_name: storeData.store_name,
          platform_store_id: storeData.platform_store_id
        }
      })
      .select()
      .single()

    if (jobError) {
      console.error('Job creation error:', jobError)
      return NextResponse.json({ error: 'Failed to create crawling job' }, { status: 500 })
    }

    // 백그라운드에서 크롤링 스크립트 실행
    try {
      const scriptPath = path.join(process.cwd(), '../backend/scripts/naver_statistics_crawler.py')
      const args = [
        '--email', storeData.naver_email,
        '--password', storeData.naver_password,
        '--store-id', storeData.platform_store_id,
        '--user-id', user.id,
        '--headless'
      ]

      if (date) {
        args.push('--date', date)
      }

      // 크롤링 프로세스 시작
      const crawlingProcess = spawn('python', [scriptPath, ...args], {
        detached: false,
        stdio: ['ignore', 'pipe', 'pipe']
      })

      let output = ''
      let errorOutput = ''

      crawlingProcess.stdout?.on('data', (data) => {
        output += data.toString()
      })

      crawlingProcess.stderr?.on('data', (data) => {
        errorOutput += data.toString()
      })

      // 프로세스 완료 처리 (비동기)
      crawlingProcess.on('close', async (code) => {
        try {
          const success = code === 0
          let result = null

          // 결과 파싱 시도
          if (success && output.includes('STATISTICS_RESULT:')) {
            const resultLine = output.split('\n').find(line => line.includes('STATISTICS_RESULT:'))
            if (resultLine) {
              try {
                result = JSON.parse(resultLine.replace('STATISTICS_RESULT:', ''))
              } catch (parseError) {
                console.error('Result parsing error:', parseError)
              }
            }
          }

          // 작업 상태 업데이트
          await supabase
            .from('crawling_jobs')
            .update({
              status: success ? 'completed' : 'failed',
              completed_at: new Date().toISOString(),
              result: result,
              error_message: success ? null : errorOutput || 'Process failed with unknown error',
              logs: output || errorOutput
            })
            .eq('id', jobData.id)

          // 성공한 경우 통계 데이터 저장
          if (success && result?.statistics_collected && result?.data) {
            // statistics_naver 테이블에 데이터 저장은 크롤링 스크립트에서 자동 처리됨
            console.log('Statistics crawling completed successfully:', result)
          }
        } catch (updateError) {
          console.error('Job status update error:', updateError)
        }
      })

      // 즉시 응답 반환 (비동기 작업 진행 중)
      return NextResponse.json({
        success: true,
        job_id: jobData.id,
        message: 'Statistics crawling started',
        estimated_completion: '3-5 minutes'
      })

    } catch (spawnError: any) {
      console.error('Process spawn error:', spawnError)
      
      // 작업 실패로 업데이트
      await supabase
        .from('crawling_jobs')
        .update({
          status: 'failed',
          completed_at: new Date().toISOString(),
          error_message: `Failed to start crawling process: ${spawnError?.message || 'Unknown error'}`
        })
        .eq('id', jobData.id)

      return NextResponse.json({ error: 'Failed to start crawling process' }, { status: 500 })
    }

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    // 사용자 인증 확인
    const { user, error: authError } = await verifyAuth(request)
    if (authError || !user) {
      return NextResponse.json({ error: authError || 'Authentication failed' }, { status: 401 })
    }

    const searchParams = request.nextUrl.searchParams
    const jobId = searchParams.get('job_id')

    if (!jobId) {
      return NextResponse.json({ error: 'job_id parameter is required' }, { status: 400 })
    }

    const supabase = await createClient()

    // 작업 상태 조회
    const { data: jobData, error: jobError } = await supabase
      .from('crawling_jobs')
      .select(`
        id,
        job_type,
        platform,
        status,
        started_at,
        completed_at,
        result,
        error_message,
        logs,
        job_config,
        platform_stores (
          store_name,
          platform_store_id
        )
      `)
      .eq('id', jobId)
      .eq('user_id', user.id)
      .single()

    if (jobError || !jobData) {
      return NextResponse.json({ error: 'Job not found or access denied' }, { status: 404 })
    }

    return NextResponse.json(jobData)

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}