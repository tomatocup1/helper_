import { createClient } from '@/lib/supabase/client'
import cron from 'node-cron'
import { spawn } from 'child_process'
import path from 'path'

interface CrawlingJob {
  id: string
  store_id: string
  user_id: string
  platform: string
  platform_id: string
  platform_password: string
  store_name: string
  platform_store_id: string
}

interface CrawlingResult {
  success: boolean
  reviews_found: number
  reviews_new: number
  reviews_updated: number
  error?: string
  duration_seconds: number
}

export class ReviewScheduler {
  private supabase = createClient()
  private isRunning = false
  private activeJobs = new Map<string, any>()

  constructor() {
    console.log('ReviewScheduler initialized')
  }

  /**
   * 스케줄러 시작 - 매시간 자동 실행
   */
  start() {
    console.log('Starting review scheduler...')
    
    // 매시간 0분에 실행 (예: 01:00, 02:00, 03:00...)
    cron.schedule('0 * * * *', async () => {
      if (!this.isRunning) {
        await this.runCrawlingCycle()
      } else {
        console.log('Previous crawling cycle still running, skipping...')
      }
    }, {
      timezone: 'Asia/Seoul'
    })

    // 즉시 한 번 실행 (테스트용)
    setTimeout(() => {
      this.runCrawlingCycle()
    }, 5000)

    console.log('Review scheduler started - running every hour')
  }

  /**
   * 크롤링 사이클 실행
   */
  private async runCrawlingCycle() {
    this.isRunning = true
    const startTime = new Date()
    
    try {
      console.log(`[${startTime.toISOString()}] Starting crawling cycle...`)
      
      // 활성 매장 조회
      const jobs = await this.getActiveCrawlingJobs()
      console.log(`Found ${jobs.length} active stores to crawl`)
      
      if (jobs.length === 0) {
        console.log('No active stores found, ending cycle')
        return
      }

      // 병렬 크롤링 실행 (최대 3개씩)
      const concurrency = 3
      const results: CrawlingResult[] = []
      
      for (let i = 0; i < jobs.length; i += concurrency) {
        const batch = jobs.slice(i, i + concurrency)
        const batchResults = await Promise.allSettled(
          batch.map(job => this.executeCrawlingJob(job))
        )
        
        batchResults.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            results.push(result.value)
          } else {
            console.error(`Job ${batch[index].id} failed:`, result.reason)
            results.push({
              success: false,
              reviews_found: 0,
              reviews_new: 0,
              reviews_updated: 0,
              error: result.reason?.message || 'Unknown error',
              duration_seconds: 0
            })
          }
        })
        
        // 배치 간 딜레이 (네이버 서버 부하 방지)
        if (i + concurrency < jobs.length) {
          await this.delay(30000) // 30초 대기
        }
      }
      
      // 결과 요약
      const summary = this.summarizeResults(results)
      const endTime = new Date()
      const totalDuration = Math.round((endTime.getTime() - startTime.getTime()) / 1000)
      
      console.log(`[${endTime.toISOString()}] Crawling cycle completed:`)
      console.log(`  - Duration: ${totalDuration}s`)
      console.log(`  - Jobs: ${summary.total} (${summary.successful} successful, ${summary.failed} failed)`)
      console.log(`  - Reviews: ${summary.total_reviews_found} found, ${summary.total_reviews_new} new`)
      
    } catch (error) {
      console.error('Crawling cycle error:', error)
    } finally {
      this.isRunning = false
    }
  }

  /**
   * 활성 크롤링 작업 조회
   */
  private async getActiveCrawlingJobs(): Promise<CrawlingJob[]> {
    try {
      const { data: stores, error } = await this.supabase
        .from('platform_stores')
        .select(`
          id,
          user_id,
          platform,
          platform_id,
          platform_password,
          store_name,
          platform_store_id,
          is_active,
          crawling_enabled,
          last_crawled_at,
          users!inner(id, is_active, subscription_plan)
        `)
        .eq('platform', 'naver') // 네이버만 처리
        .eq('is_active', true)
        .eq('crawling_enabled', true)
        .eq('users.is_active', true)

      if (error) {
        console.error('Error fetching active stores:', error)
        return []
      }

      if (!stores || stores.length === 0) {
        return []
      }

      // 크롤링 주기 필터링 (최소 1시간 간격)
      const now = new Date()
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000)

      const filteredStores = stores.filter(store => {
        if (!store.last_crawled_at) return true
        const lastCrawled = new Date(store.last_crawled_at)
        return lastCrawled < oneHourAgo
      })

      return filteredStores.map(store => ({
        id: store.id,
        store_id: store.id,
        user_id: store.user_id,
        platform: store.platform,
        platform_id: store.platform_id,
        platform_password: store.platform_password,
        store_name: store.store_name,
        platform_store_id: store.platform_store_id
      }))

    } catch (error) {
      console.error('Error in getActiveCrawlingJobs:', error)
      return []
    }
  }

  /**
   * 개별 크롤링 작업 실행
   */
  private async executeCrawlingJob(job: CrawlingJob): Promise<CrawlingResult> {
    const startTime = new Date()
    let logId: string | null = null

    try {
      // 크롤링 로그 시작
      const { data: log, error: logError } = await this.supabase
        .from('crawling_logs')
        .insert({
          store_id: job.store_id,
          user_id: job.user_id,
          crawling_type: 'reviews',
          status: 'started',
          started_at: startTime.toISOString(),
          crawling_settings: {
            date_filter: '7일', // 최근 7일
            auto_reply: false
          }
        })
        .select('id')
        .single()

      if (logError) {
        console.error('Error creating crawling log:', logError)
      } else {
        logId = log.id
      }

      console.log(`Starting crawling job for store: ${job.store_name} (${job.platform_store_id})`)

      // Python 크롤러 실행
      const result = await this.runPythonCrawler(job)
      
      const endTime = new Date()
      const duration = Math.round((endTime.getTime() - startTime.getTime()) / 1000)

      // 크롤링 로그 업데이트
      if (logId) {
        await this.supabase
          .from('crawling_logs')
          .update({
            status: result.success ? 'completed' : 'failed',
            completed_at: endTime.toISOString(),
            duration_seconds: duration,
            reviews_found: result.reviews_found,
            reviews_new: result.reviews_new,
            reviews_updated: result.reviews_updated,
            error_message: result.error || null
          })
          .eq('id', logId)
      }

      // 매장 정보 업데이트
      if (result.success) {
        await this.supabase
          .from('platform_stores')
          .update({
            last_crawled_at: endTime.toISOString(),
            total_reviews: result.reviews_found
          })
          .eq('id', job.store_id)
      }

      return {
        ...result,
        duration_seconds: duration
      }

    } catch (error) {
      const endTime = new Date()
      const duration = Math.round((endTime.getTime() - startTime.getTime()) / 1000)
      
      console.error(`Crawling job failed for ${job.store_name}:`, error)

      // 실패 로그 업데이트
      if (logId) {
        await this.supabase
          .from('crawling_logs')
          .update({
            status: 'failed',
            completed_at: endTime.toISOString(),
            duration_seconds: duration,
            error_message: error instanceof Error ? error.message : 'Unknown error'
          })
          .eq('id', logId)
      }

      return {
        success: false,
        reviews_found: 0,
        reviews_new: 0,
        reviews_updated: 0,
        error: error instanceof Error ? error.message : 'Unknown error',
        duration_seconds: duration
      }
    }
  }

  /**
   * Python 크롤러 실행
   */
  private async runPythonCrawler(job: CrawlingJob): Promise<CrawlingResult> {
    return new Promise((resolve, reject) => {
      const crawlerPath = path.join(process.cwd(), '../backend/scripts/naver_review_crawler.py')
      const workingDir = path.join(process.cwd(), '../backend/scripts')
      
      console.log(`Executing Python crawler: ${crawlerPath}`)
      console.log(`Store ID: ${job.platform_store_id}`)
      
      const pythonProcess = spawn('python', [
        crawlerPath,
        '--email', job.platform_id,
        '--password', job.platform_password,
        '--store-id', job.platform_store_id,
        '--mode', 'auto',
        '--days', '7'
      ], {
        cwd: workingDir,
        stdio: ['pipe', 'pipe', 'pipe']
      })

      let stdout = ''
      let stderr = ''
      const timeout = 10 * 60 * 1000 // 10분 타임아웃

      const timer = setTimeout(() => {
        pythonProcess.kill()
        reject(new Error('Crawling timeout (10 minutes)'))
      }, timeout)

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString()
      })

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString()
      })

      pythonProcess.on('close', (code) => {
        clearTimeout(timer)
        
        if (code === 0) {
          try {
            // stdout에서 JSON 결과 파싱
            const lines = stdout.split('\n')
            const resultLine = lines.find(line => line.startsWith('CRAWLING_RESULT:'))
            
            if (resultLine) {
              const resultJson = resultLine.replace('CRAWLING_RESULT:', '')
              const result = JSON.parse(resultJson)
              resolve(result)
            } else {
              // 기본 성공 결과
              resolve({
                success: true,
                reviews_found: 0,
                reviews_new: 0,
                reviews_updated: 0,
                duration_seconds: 0
              })
            }
          } catch (error) {
            console.error('Error parsing crawler result:', error)
            console.log('Stdout:', stdout)
            console.log('Stderr:', stderr)
            reject(new Error('Failed to parse crawler result'))
          }
        } else {
          console.error('Python crawler failed with code:', code)
          console.log('Stderr:', stderr)
          reject(new Error(`Python crawler exit code: ${code}`))
        }
      })

      pythonProcess.on('error', (error) => {
        clearTimeout(timer)
        reject(error)
      })
    })
  }

  /**
   * 결과 요약
   */
  private summarizeResults(results: CrawlingResult[]) {
    return {
      total: results.length,
      successful: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      total_reviews_found: results.reduce((sum, r) => sum + r.reviews_found, 0),
      total_reviews_new: results.reduce((sum, r) => sum + r.reviews_new, 0),
      total_reviews_updated: results.reduce((sum, r) => sum + r.reviews_updated, 0)
    }
  }

  /**
   * 딜레이 함수
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * 스케줄러 중지
   */
  stop() {
    console.log('Stopping review scheduler...')
    // cron 작업들 정리
    cron.getTasks().forEach(task => task.stop())
    console.log('Review scheduler stopped')
  }
}

// 싱글톤 인스턴스
export const reviewScheduler = new ReviewScheduler()