"use client"

import { useState, useEffect } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/store/auth-store-supabase'
import { createClient } from '@/lib/supabase/client'
import {
  Activity,
  Clock,
  CheckCircle,
  AlertTriangle,
  BarChart3,
  Play,
  Pause,
  RefreshCw,
  Store,
  MessageSquare
} from 'lucide-react'

interface ErrorLog {
  id: string
  store_name: string
  error_category: string
  severity: string
  error_message: string
  created_at: string
  is_resolved: boolean
  related_table?: string
}

interface CrawlingStats {
  total_stores: number
  active_stores: number
  last_24h_crawls: number
  total_reviews: number
  avg_rating: number
  last_successful_crawl?: string
}

export default function CrawlingMonitorPage() {
  const { user } = useAuth()
  const [logs, setLogs] = useState<ErrorLog[]>([])
  const [stats, setStats] = useState<CrawlingStats | null>(null)
  const [schedulerRunning, setSchedulerRunning] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const supabase = createClient()

  useEffect(() => {
    if (user) {
      fetchData()
      
      // 30초마다 자동 새로고침
      const interval = setInterval(fetchData, 30000)
      return () => clearInterval(interval)
    }
  }, [user])

  const fetchData = async () => {
    try {
      setRefreshing(true)
      await Promise.all([
        fetchErrorLogs(),
        fetchCrawlingStats(),
        checkSchedulerStatus()
      ])
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const fetchErrorLogs = async () => {
    try {
      const { data, error } = await supabase
        .from('error_logs')
        .select(`
          id,
          error_category,
          severity,
          error_message,
          created_at,
          is_resolved,
          related_table,
          platform_stores!inner(store_name)
        `)
        .eq('user_id', user?.id)
        .in('error_category', ['crawling', 'api'])
        .order('created_at', { ascending: false })
        .limit(20)

      if (error) throw error

      const transformedLogs = data?.map(log => ({
        id: log.id,
        store_name: (log.platform_stores as any)?.store_name || 'Unknown Store',
        error_category: log.error_category,
        severity: log.severity,
        error_message: log.error_message,
        created_at: log.created_at,
        is_resolved: log.is_resolved,
        related_table: log.related_table
      })) || []

      setLogs(transformedLogs)
    } catch (error) {
      console.error('Error fetching error logs:', error)
    }
  }

  const fetchCrawlingStats = async () => {
    try {
      // 기존 테이블들로부터 통계 계산
      const { data: storesData, error: storesError } = await supabase
        .from('platform_stores')
        .select('id, store_name, crawling_enabled, last_crawled_at')
        .eq('user_id', user?.id)
        .eq('platform', 'naver')

      if (storesError) throw storesError

      const { data: reviewsData, error: reviewsError } = await supabase
        .from('reviews_naver')
        .select('rating, review_date')
        .in('platform_store_id', storesData?.map(s => s.id) || [])
        .gte('review_date', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())

      if (reviewsError) throw reviewsError

      const stats = {
        total_stores: storesData?.length || 0,
        active_stores: storesData?.filter(s => s.crawling_enabled).length || 0,
        last_24h_crawls: storesData?.filter(s => 
          s.last_crawled_at && 
          new Date(s.last_crawled_at) > new Date(Date.now() - 24 * 60 * 60 * 1000)
        ).length || 0,
        total_reviews: reviewsData?.length || 0,
        avg_rating: reviewsData?.length > 0 
          ? Math.round((reviewsData.reduce((sum, r) => sum + (r.rating || 0), 0) / reviewsData.length) * 10) / 10
          : 0,
        last_successful_crawl: storesData
          ?.filter(s => s.last_crawled_at)
          ?.sort((a, b) => new Date(b.last_crawled_at).getTime() - new Date(a.last_crawled_at).getTime())[0]?.last_crawled_at
      }

      setStats(stats)
    } catch (error) {
      console.error('Error fetching crawling stats:', error)
    }
  }

  const checkSchedulerStatus = async () => {
    try {
      const response = await fetch('/api/scheduler/start')
      const data = await response.json()
      // 안전한 데이터 접근
      setSchedulerRunning(data && data.success === true)
    } catch (error) {
      console.error('Error checking scheduler status:', error)
      setSchedulerRunning(false)
    }
  }

  const startScheduler = async () => {
    try {
      const response = await fetch('/api/scheduler/start', {
        method: 'POST'
      })
      const data = await response.json()
      // 안전한 데이터 접근 확인
      
      if (data && data.success === true) {
        setSchedulerRunning(true)
        alert('스케줄러가 시작되었습니다.')
      } else {
        alert('스케줄러 시작에 실패했습니다.')
      }
    } catch (error) {
      console.error('Error starting scheduler:', error)
      alert('스케줄러 시작 중 오류가 발생했습니다.')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR')
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <Badge className="bg-red-100 text-red-800">치명적</Badge>
      case 'high':
        return <Badge className="bg-orange-100 text-orange-800">높음</Badge>
      case 'medium':
        return <Badge className="bg-yellow-100 text-yellow-800">보통</Badge>
      case 'low':
        return <Badge className="bg-blue-100 text-blue-800">낮음</Badge>
      default:
        return <Badge variant="secondary">{severity}</Badge>
    }
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="w-8 h-8 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto"></div>
            <p className="text-gray-600">모니터링 데이터를 불러오는 중...</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold brand-text">크롤링 모니터링</h1>
            <p className="text-muted-foreground mt-1">
              리뷰 자동 크롤링 시스템의 실시간 상태를 확인하세요
            </p>
          </div>
          <div className="flex space-x-3">
            <Button 
              variant="outline" 
              onClick={fetchData}
              disabled={refreshing}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              새로고침
            </Button>
            <Button 
              variant={schedulerRunning ? "destructive" : "default"}
              onClick={startScheduler}
            >
              {schedulerRunning ? (
                <>
                  <Pause className="w-4 h-4 mr-2" />
                  실행중
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  시작
                </>
              )}
            </Button>
          </div>
        </div>

        {/* 통계 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">등록된 매장</CardTitle>
              <Store className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_stores || 0}</div>
              <p className="text-xs text-muted-foreground">
                네이버 플레이스 연결
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">활성 매장</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.active_stores || 0}</div>
              <p className="text-xs text-green-600">
                크롤링 활성화됨
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">수집된 리뷰</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total_reviews || 0}</div>
              <p className="text-xs text-muted-foreground">
                최근 7일 누적
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">평균 평점</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.avg_rating || 0}점
              </div>
              <p className="text-xs text-muted-foreground">
                최근 7일 평균
              </p>
            </CardContent>
          </Card>
        </div>

        {/* 스케줄러 상태 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="w-5 h-5" />
              <span>스케줄러 상태</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className={`w-3 h-3 rounded-full ${schedulerRunning ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="font-medium">
                  {schedulerRunning ? '자동 크롤링 실행 중' : '자동 크롤링 중지됨'}
                </span>
              </div>
              <div className="text-sm text-gray-600">
                {schedulerRunning ? '매시간 0분에 자동 실행' : '수동 시작 필요'}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 최근 에러 로그 */}
        <Card>
          <CardHeader>
            <CardTitle>최근 크롤링 로그</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {logs.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p>크롤링 로그가 없습니다</p>
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Store className="w-4 h-4 text-gray-400" />
                        <span className="font-medium">{log.store_name}</span>
                        {getSeverityBadge(log.severity)}
                        {log.is_resolved && (
                          <Badge className="bg-green-100 text-green-800">해결됨</Badge>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">
                        {formatDate(log.created_at)}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">카테고리:</span>
                        <div className="font-medium">{log.error_category}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">심각도:</span>
                        <div className="font-medium">{log.severity}</div>
                      </div>
                      <div>
                        <span className="text-gray-600">관련 테이블:</span>
                        <div className="font-medium">{log.related_table || '-'}</div>
                      </div>
                    </div>
                    
                    <div className="bg-red-50 border border-red-200 rounded p-3">
                      <div className="flex items-start space-x-2">
                        <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
                        <div className="text-sm text-red-700">{log.error_message}</div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}