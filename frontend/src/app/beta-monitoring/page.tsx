"use client"

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  MessageSquare,
  Store,
  Users,
  TrendingUp,
  Clock,
  Smartphone,
  Server,
  Database
} from 'lucide-react'

interface SystemMetrics {
  crawling: {
    total_stores: number
    active_stores: number
    success_rate: number
    last_run: string
    daily_reviews: number
  }
  ai_replies: {
    generated_today: number
    posted_today: number
    success_rate: number
    avg_response_time: number
  }
  alimtalk: {
    sent_today: number
    failed_today: number
    success_rate: number
    urgent_alerts: number
  }
  infrastructure: {
    frontend_status: 'healthy' | 'warning' | 'error'
    backend_status: 'healthy' | 'warning' | 'error'
    database_status: 'healthy' | 'warning' | 'error'
    response_time: number
  }
}

interface StoreStats {
  store_id: string
  store_name: string
  platform: string
  daily_reviews: number
  ai_replies: number
  alimtalk_sent: number
  last_activity: string
  status: 'active' | 'warning' | 'error'
}

const BetaMonitoringDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [storeStats, setStoreStats] = useState<StoreStats[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  // 실시간 데이터 업데이트
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 시스템 메트릭 조회
        const metricsResponse = await fetch('/api/beta/metrics')
        const metricsData = await metricsResponse.json()
        setMetrics(metricsData)

        // 매장별 통계 조회
        const storesResponse = await fetch('/api/beta/stores')
        const storesData = await storesResponse.json()
        setStoreStats(storesData)

        setLastUpdate(new Date().toLocaleString('ko-KR'))
        setLoading(false)
      } catch (error) {
        console.error('데이터 조회 실패:', error)
        setLoading(false)
      }
    }

    fetchData()

    // 30초마다 업데이트
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
        return 'text-green-600'
      case 'warning':
        return 'text-yellow-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />
      default:
        return <Clock className="h-4 w-4 text-gray-600" />
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p>베타 모니터링 데이터 로딩 중...</p>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="p-6">
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>데이터 로딩 실패</AlertTitle>
          <AlertDescription>
            모니터링 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">베타 서비스 모니터링</h1>
          <p className="text-gray-600">실시간 시스템 상태 및 성능 모니터링</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">마지막 업데이트</p>
          <p className="font-medium">{lastUpdate}</p>
        </div>
      </div>

      {/* 시스템 상태 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">인프라 상태</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs">Frontend</span>
                {getStatusIcon(metrics.infrastructure.frontend_status)}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs">Backend</span>
                {getStatusIcon(metrics.infrastructure.backend_status)}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs">Database</span>
                {getStatusIcon(metrics.infrastructure.database_status)}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">크롤링 상태</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.crawling.success_rate}%</div>
            <div className="text-xs text-muted-foreground">
              {metrics.crawling.active_stores}/{metrics.crawling.total_stores} 매장 활성
            </div>
            <Progress value={metrics.crawling.success_rate} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI 답글</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.ai_replies.posted_today}</div>
            <div className="text-xs text-muted-foreground">
              오늘 등록된 답글 ({metrics.ai_replies.success_rate}% 성공률)
            </div>
            <Progress value={metrics.ai_replies.success_rate} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">알림톡</CardTitle>
            <Smartphone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.alimtalk.sent_today}</div>
            <div className="text-xs text-muted-foreground">
              오늘 발송 (긴급: {metrics.alimtalk.urgent_alerts}건)
            </div>
            <Progress value={metrics.alimtalk.success_rate} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* 상세 모니터링 */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">전체 현황</TabsTrigger>
          <TabsTrigger value="stores">매장별 상태</TabsTrigger>
          <TabsTrigger value="performance">성능 지표</TabsTrigger>
          <TabsTrigger value="alerts">알림 로그</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>일일 처리 현황</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span>수집된 리뷰</span>
                  <Badge variant="secondary">{metrics.crawling.daily_reviews}개</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>생성된 답글</span>
                  <Badge variant="secondary">{metrics.ai_replies.generated_today}개</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>등록된 답글</span>
                  <Badge variant="secondary">{metrics.ai_replies.posted_today}개</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>발송된 알림</span>
                  <Badge variant="secondary">{metrics.alimtalk.sent_today}개</Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>시스템 성능</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span>평균 응답시간</span>
                  <Badge variant={metrics.infrastructure.response_time > 2000 ? "destructive" : "secondary"}>
                    {metrics.infrastructure.response_time}ms
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>AI 응답시간</span>
                  <Badge variant="secondary">{metrics.ai_replies.avg_response_time}s</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>마지막 크롤링</span>
                  <Badge variant="secondary">{metrics.crawling.last_run}</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="stores" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>매장별 활성도</CardTitle>
              <CardDescription>베타 참여 매장들의 실시간 상태</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {storeStats.map((store) => (
                  <div key={store.store_id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div className={getStatusColor(store.status)}>
                        {getStatusIcon(store.status)}
                      </div>
                      <div>
                        <p className="font-medium">{store.store_name}</p>
                        <p className="text-sm text-gray-600">{store.platform}</p>
                      </div>
                    </div>
                    <div className="text-right space-y-1">
                      <div className="flex space-x-2">
                        <Badge variant="outline">{store.daily_reviews} 리뷰</Badge>
                        <Badge variant="outline">{store.ai_replies} 답글</Badge>
                        <Badge variant="outline">{store.alimtalk_sent} 알림</Badge>
                      </div>
                      <p className="text-xs text-gray-500">{store.last_activity}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>크롤링 성능</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>성공률</span>
                    <span>{metrics.crawling.success_rate}%</span>
                  </div>
                  <Progress value={metrics.crawling.success_rate} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>답글 시스템</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>성공률</span>
                    <span>{metrics.ai_replies.success_rate}%</span>
                  </div>
                  <Progress value={metrics.ai_replies.success_rate} />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>최근 알림 로그</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertTitle>시스템 정상</AlertTitle>
                  <AlertDescription>
                    모든 서비스가 정상적으로 동작하고 있습니다.
                  </AlertDescription>
                </Alert>

                {metrics.alimtalk.urgent_alerts > 0 && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>긴급 알림 발송</AlertTitle>
                    <AlertDescription>
                      {metrics.alimtalk.urgent_alerts}건의 긴급 리뷰 알림이 발송되었습니다.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default BetaMonitoringDashboard