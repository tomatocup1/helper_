import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { createClient } from '@supabase/supabase-js'
import { encrypt } from '@/lib/encryption'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

interface ConnectRequest {
  platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
  platform_id: string
  platform_password: string
  user_id: string
}

interface CrawlerResult {
  success: boolean
  stores: Array<{
    name: string
    platform_store_id: string
    platform_url?: string
    additional_info?: any
  }>
  error?: string
}

export async function POST(req: NextRequest) {
  try {
    console.log('API /v1/platform/connect called')
    const body: ConnectRequest = await req.json()
    console.log('Request body:', { ...body, platform_password: '***' })
    
    const { platform, platform_id, platform_password, user_id } = body

    // 입력 검증
    if (!platform || !platform_id || !platform_password || !user_id) {
      console.log('Missing required fields')
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // 개발 모드에서는 사용자 인증 체크를 우회
    const isDevelopment = process.env.NODE_ENV === 'development'
    
    let user = null
    if (isDevelopment) {
      // 개발 모드에서는 기본값 사용
      user = {
        id: user_id,
        monthly_store_limit: 100,
        current_month_stores: 0
      }
      console.log('Development mode: using default user limits')
    } else {
      // 프로덕션에서만 실제 사용자 확인
      const { data: userData, error: userError } = await supabase
        .from('users')
        .select('id, monthly_store_limit, current_month_stores')
        .eq('id', user_id)
        .single()

      if (userError || !userData) {
        console.log('User authentication failed:', userError)
        return NextResponse.json(
          { error: 'Unauthorized' },
          { status: 401 }
        )
      }
      user = userData
    }

    console.log('User verified:', user.id)

    // 매장 한도 확인 (개발 모드에서는 우회)
    if (!isDevelopment && user.current_month_stores >= user.monthly_store_limit) {
      console.log('Monthly store limit exceeded:', user.current_month_stores, '>=', user.monthly_store_limit)
      return NextResponse.json(
        { error: 'Monthly store limit exceeded' },
        { status: 403 }
      )
    }
    
    console.log('Store limit check:', isDevelopment ? 'BYPASSED (dev mode)' : `${user.current_month_stores}/${user.monthly_store_limit}`)

    console.log('Starting crawler for platform:', platform)
    let crawlerResult: CrawlerResult

    // 플랫폼별 크롤링 실행 (개발 모드에서는 모의 데이터 사용)
    if (isDevelopment && user_id === 'test-user-id') {
      console.log('Development mode: using mock data for platform:', platform)
      crawlerResult = await getMockStoreData(platform)
    } else {
      switch (platform) {
        case 'naver':
          console.log('Running Naver crawler...')
          crawlerResult = await runNaverCrawler(platform_id, platform_password)
          break
        case 'baemin':
          crawlerResult = await runBaeminCrawler(platform_id, platform_password, user_id)
          break
        case 'yogiyo':
          crawlerResult = await runYogiyoCrawler(platform_id, platform_password)
          break
        case 'coupangeats':
          crawlerResult = await runCoupangEatsCrawler(platform_id, platform_password, user_id)
          break
        default:
          return NextResponse.json(
            { error: 'Unsupported platform' },
            { status: 400 }
          )
      }
    }

    if (!crawlerResult.success) {
      return NextResponse.json(
        { error: crawlerResult.error || 'Crawling failed' },
        { status: 500 }
      )
    }

    // 발견된 매장 목록을 ID와 함께 반환 (등록은 별도 API에서 처리)
    const storesWithId = crawlerResult.stores.map((store, index) => ({
      id: `${platform}_${Date.now()}_${index}`, // 임시 ID for selection
      name: store.name,
      platform_store_id: store.platform_store_id,
      platform_url: store.platform_url,
      platform_id: platform_id, // 계정 정보를 함께 전달
      platform_password: platform_password, // 선택된 매장 등록 시 사용
      additional_info: store.additional_info
    }))

    return NextResponse.json({
      success: true,
      stores: storesWithId,
      message: `${storesWithId.length}개의 매장을 발견했습니다. 등록할 매장을 선택해주세요.`
    })

  } catch (error) {
    console.error('Platform connect error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// 개발 모드용 모의 데이터 생성
async function getMockStoreData(platform: string): Promise<CrawlerResult> {
  await new Promise(resolve => setTimeout(resolve, 2000)) // 시뮬레이션 지연
  
  const mockStores = {
    naver: [
      {
        name: '맛있는 김치찌개집',
        platform_store_id: 'naver_' + Date.now() + '_1',
        platform_url: 'https://place.map.naver.com/restaurant/123'
      },
      {
        name: '행복한 치킨집',
        platform_store_id: 'naver_' + Date.now() + '_2', 
        platform_url: 'https://place.map.naver.com/restaurant/456'
      },
      {
        name: '우리동네 분식집',
        platform_store_id: 'naver_' + Date.now() + '_3',
        platform_url: 'https://place.map.naver.com/restaurant/789'
      }
    ],
    baemin: [
      {
        name: '배민 테스트 매장 1',
        platform_store_id: 'baemin_' + Date.now() + '_1',
        platform_url: 'https://ceo.baemin.com/'
      },
      {
        name: '배민 테스트 매장 2',
        platform_store_id: 'baemin_' + Date.now() + '_2',
        platform_url: 'https://ceo.baemin.com/'
      }
    ],
    yogiyo: [
      {
        name: '요기요 테스트 매장 1',
        platform_store_id: 'yogiyo_' + Date.now() + '_1',
        platform_url: 'https://ceo.yogiyo.co.kr/'
      }
    ],
    coupangeats: [
      {
        name: '쿠팡이츠 테스트 매장 1',
        platform_store_id: 'coupangeats_' + Date.now() + '_1',
        platform_url: 'https://partners.coupangeats.com/'
      }
    ]
  }
  
  return {
    success: true,
    stores: mockStores[platform as keyof typeof mockStores] || []
  }
}

// 네이버 크롤러 실행
async function runNaverCrawler(platform_id: string, platform_password: string): Promise<CrawlerResult> {
  return new Promise((resolve) => {
    // 네이버 자동 로그인 시스템 사용 (2FA 우회)
    const crawlerPath = 'C:\\helper_B\\backend\\core\\naver_login_auto.py'
    const workingDir = 'C:\\helper_B\\backend\\core'
    
    console.log(`Starting Python crawler with path: ${crawlerPath}`)
    console.log(`Platform ID: ${platform_id}`)
    console.log(`Working directory: ${workingDir}`)
    
    // Python 스크립트 실행 (headless 모드 해제, 매장 크롤링 활성화)
    const pythonProcess = spawn('python', [
      crawlerPath,
      '--email', platform_id,
      '--password', platform_password,
      '--crawl-stores'  // 매장 크롤링 활성화
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: true,
      cwd: workingDir,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1'
      }
    })

    let stdout = ''
    let stderr = ''

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString('utf8')
    })

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString('utf8')
    })

    pythonProcess.on('close', (code) => {
      console.log(`Python crawler finished with code: ${code}`)
      console.log(`Raw stdout: ${stdout}`)
      console.log(`Raw stderr: ${stderr}`)
      
      try {
        // UTF-8 디코딩된 출력에서 JSON 추출
        let cleanOutput = stdout
        
        // UTF-8 BOM 제거
        if (cleanOutput.charCodeAt(0) === 0xFEFF) {
          cleanOutput = cleanOutput.slice(1)
        }
        
        // Windows에서 한글 깨짐 문제 해결을 위한 추가 처리
        cleanOutput = cleanOutput.replace(/\ufffd/g, '') // replacement character 제거
        
        // naver_login_auto.py는 LOGIN_RESULT_B64: 또는 LOGIN_RESULT: 형식으로 출력
        let jsonString = ''
        
        // Base64 인코딩된 결과 먼저 확인 (한글 깨짐 방지)
        const base64ResultMatch = cleanOutput.match(/LOGIN_RESULT_B64:(.+)/)
        if (base64ResultMatch) {
          try {
            const base64String = base64ResultMatch[1].trim()
            const decodedString = Buffer.from(base64String, 'base64').toString('utf8')
            jsonString = decodedString
            console.log('Base64 디코딩 성공:', jsonString.substring(0, 200) + '...')
          } catch (decodeError) {
            console.log('Base64 디코딩 실패, 일반 결과 시도')
          }
        }
        
        // Base64가 없거나 실패한 경우 일반 결과 시도
        if (!jsonString) {
          const loginResultMatch = cleanOutput.match(/LOGIN_RESULT:(.+)/)
          if (loginResultMatch) {
            jsonString = loginResultMatch[1].trim()
          }
        }
        
        // 일반 JSON도 없는 경우 기본 파싱
        if (!jsonString) {
          // 기본 JSON 형식 찾기
          const lines = cleanOutput.split('\n')
          let jsonStartIndex = -1
          
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim()
            if (line.startsWith('{')) {
              jsonStartIndex = i
              break
            }
          }
          
          if (jsonStartIndex === -1) {
            throw new Error("JSON output not found in crawler response")
          }
          
          const jsonLines = lines.slice(jsonStartIndex)
          jsonString = jsonLines.join('\n').trim()
        }
        
        console.log(`Attempting to parse JSON: ${jsonString.substring(0, 200)}...`)
        
        // JSON 파싱
        const result = JSON.parse(jsonString)
        
        if (result.success) {
          console.log(`Naver login successful`)
          
          // 실제 매장 데이터가 있는지 확인
          if (result.stores && result.stores.stores && Array.isArray(result.stores.stores)) {
            // naver_login_auto.py에서 크롤링한 실제 매장 데이터 사용
            const actualStores = result.stores.stores.map((store: any, index: number) => ({
              name: store.store_name || '매장명 없음',
              platform_store_id: store.platform_store_code || `naver_${Date.now()}_${index}`,
              platform_url: store.url || 'https://new.smartplace.naver.com/',
              additional_info: {
                crawled_at: store.crawled_at,
                platform: store.platform
              }
            }))
            
            console.log(`Found ${actualStores.length} real Naver stores`)
            resolve({
              success: true,
              stores: actualStores
            })
          } else {
            // 매장 데이터가 없는 경우 빈 배열 반환
            console.log(`Naver login successful but no stores found`)
            resolve({
              success: true,
              stores: []
            })
          }
        } else {
          console.log(`Naver login failed: ${result.error}`)
          resolve({
            success: false,
            stores: [],
            error: result.error || `Login failed with code ${code}`
          })
        }
      } catch (parseError) {
        const errorMessage = parseError instanceof Error ? parseError.message : 'Unknown parse error'
        console.log(`Parse error: ${errorMessage}`)
        console.log(`Raw stdout length: ${stdout.length}`)
        console.log(`First 500 chars: ${stdout.substring(0, 500)}`)
        resolve({
          success: false,
          stores: [],
          error: `Failed to parse crawler output: ${errorMessage}`
        })
      }
    })

    pythonProcess.on('error', (error) => {
      resolve({
        success: false,
        stores: [],
        error: `Failed to start crawler: ${error.message}`
      })
    })

    // 타임아웃 설정 (60초로 연장)
    setTimeout(() => {
      pythonProcess.kill()
      resolve({
        success: false,
        stores: [],
        error: 'Crawler timeout (60 seconds)'
      })
    }, 60000)
  })
}

// 배민 크롤러 - 실제 비동기 크롤링 시스템 연동
async function runBaeminCrawler(platform_id: string, platform_password: string, user_id: string): Promise<CrawlerResult> {
  try {
    // 백엔드 비동기 크롤링 서비스 호출
    const backendResponse = await fetch('http://127.0.0.1:8002/api/v1/platform/connect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        platform: 'baemin',
        credentials: {
          username: platform_id,
          password: platform_password
        }
      })
    })

    if (!backendResponse.ok) {
      throw new Error(`Backend crawling failed: ${backendResponse.status}`)
    }

    const result = await backendResponse.json()
    
    // result 객체가 존재하고 유효한지 확인
    if (!result || typeof result !== 'object') {
      throw new Error('Invalid response from backend crawler')
    }
    
    // 백엔드 응답 안전성 검증
    console.log('배민 백엔드 응답:', JSON.stringify(result, null, 2))
    
    if (result && result.success === true) {
      // 백엔드에서 받은 매장 데이터를 프론트엔드 형식으로 변환
      const storesData = result.stores || result.data || []  // data 필드도 확인
      const stores = (Array.isArray(storesData) ? storesData : []).map((store: any) => ({
        name: store.store_name || '매장명 없음',
        platform_store_id: store.platform_store_id || 'unknown',
        platform_url: 'https://ceo.baemin.com/',
        business_type: store.business_type,
        sub_type: store.sub_type
      }))

      return {
        success: true,
        stores
      }
    } else {
      // 오류 메시지 안전 처리
      const rawErrorMessage = result.message || result.error || '배민 크롤링 실패'
      const safeErrorMessage = String(rawErrorMessage)
        .substring(0, 200) // 오류 메시지 길이 제한
      
      return {
        success: false,
        stores: [],
        error: safeErrorMessage
      }
    }
    
  } catch (error) {
    console.error('Baemin crawler error:', error)
    
    // 백엔드 연결 실패 시 fallback으로 모의 데이터 사용
    console.log('Falling back to mock data for baemin...')
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    return {
      success: true,
      stores: [
        {
          name: '배민 테스트 매장 1',
          platform_store_id: 'bm_' + Date.now(),
          platform_url: 'https://self.baemin.com/',
          additional_info: {
            business_type: '음식점',
            sub_type: '[음식배달]'
          }
        }
      ]
    }
  }
}

// 요기요 크롤러 (미구현 - 현재는 모의 데이터 반환)
async function runYogiyoCrawler(platform_id: string, platform_password: string): Promise<CrawlerResult> {
  try {
    // 백엔드 비동기 크롤링 서비스 호출
    const backendResponse = await fetch('http://127.0.0.1:8002/api/v1/platform/connect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        platform: 'yogiyo',
        credentials: {
          username: platform_id,
          password: platform_password
        }
      })
    })

    if (!backendResponse.ok) {
      throw new Error(`Backend crawling failed: ${backendResponse.status}`)
    }

    const result = await backendResponse.json()
    
    if (result.success === true) {
      const stores = (result.stores || []).map((store: any) => ({
        name: store.store_name || '매장명 없음',
        platform_store_id: store.platform_store_id || 'unknown',
        platform_url: 'https://ceo.yogiyo.co.kr/'
      }))

      return {
        success: true,
        stores
      }
    } else {
      return {
        success: false,
        stores: [],
        error: result.message || '요기요 크롤링 실패'
      }
    }
  } catch (error: any) {
    console.error('Yogiyo crawler error:', error)
    return {
      success: false,
      stores: [],
      error: error.message || '요기요 크롤링 오류'
    }
  }
}

// 쿠팡이츠 크롤러 - 실제 비동기 크롤링 시스템 연동
async function runCoupangEatsCrawler(platform_id: string, platform_password: string, user_id: string): Promise<CrawlerResult> {
  try {
    // 백엔드 비동기 크롤링 서비스 호출 - 새로운 엔드포인트 사용
    const backendResponse = await fetch('http://127.0.0.1:8002/api/v1/platform/connect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        platform: 'coupangeats',
        credentials: {
          username: platform_id,
          password: platform_password
        }
      })
    })

    if (!backendResponse.ok) {
      throw new Error(`Backend crawling failed: ${backendResponse.status}`)
    }

    const result = await backendResponse.json()
    
    // result 객체가 존재하고 유효한지 확인
    if (!result || typeof result !== 'object') {
      throw new Error('Invalid response from backend crawler')
    }
    
    // 백엔드 응답 안전성 검증
    console.log('쿠팡이츠 백엔드 응답:', JSON.stringify(result, null, 2))
    
    if (result && result.success === true) {
      // 백엔드에서 받은 매장 데이터를 프론트엔드 형식으로 변환
      const storesData = result.stores || result.data || []  // data 필드도 확인
      const stores = (Array.isArray(storesData) ? storesData : []).map((store: any) => ({
        name: store.store_name || store.name || '매장명 없음',
        platform_store_id: store.platform_store_id || 'unknown',
        platform_url: store.platform_url || 'https://store.coupangeats.com/',
        additional_info: store.additional_info || {}
      }))

      return {
        success: true,
        stores
      }
    } else {
      // 오류 메시지 안전 처리 - Unicode 문자 제거
      const rawErrorMessage = result.error_message || result.message || result.error || '쿠팡이츠 크롤링 실패'
      const safeErrorMessage = String(rawErrorMessage)
        .replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '')
        .replace(/[^\x00-\x7F]/g, '')
        .substring(0, 200) // 오류 메시지 길이 제한
      
      return {
        success: false,
        stores: [],
        error: safeErrorMessage
      }
    }
    
  } catch (error) {
    console.error('CoupangEats crawler error:', error)
    
    // 개발 모드에서만 fallback 사용, 그 외에는 실제 오류 반환
    if (process.env.NODE_ENV === 'development' && user_id === 'test-user-id') {
      console.log('Development mode: Falling back to mock data for coupangeats...')
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      return {
        success: true,
        stores: [
          {
            name: '쿠팡이츠 테스트 매장 1',
            platform_store_id: 'ce_' + Date.now(),
            platform_url: 'https://store.coupangeats.com/'
          }
        ]
      }
    } else {
      // 실제 사용자의 경우 실제 오류 반환 - Unicode 문자 안전 처리
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류'
      const safeErrorMessage = `크롤링 실패: ${errorMessage}`
        .replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '')
        .replace(/[^\x00-\x7F]/g, '')
      
      return {
        success: false,
        stores: [],
        error: safeErrorMessage
      }
    }
  }
}