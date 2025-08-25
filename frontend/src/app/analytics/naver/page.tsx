"use client"

import { useState, useEffect } from 'react'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import { createClient } from '@/lib/supabase/client'
import { 
  StatisticsTrendChart, 
  StatisticsSummaryCards, 
  InflowChannelChart, 
  InflowKeywordChart 
} from '@/components/analytics/StatisticsChart'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import { 
  Calendar,
  TrendingUp, 
  TrendingDown, 
  Minus,
  Phone,
  MessageSquare,
  MapPin,
  ShoppingCart,
  Users,
  Search,
  Hash,
  RefreshCw,
  Download,
  Filter,
  Eye,
  BarChart3
} from 'lucide-react'
import { format, subDays, startOfWeek, endOfWeek, startOfMonth, endOfMonth } from 'date-fns'
import { ko } from 'date-fns/locale'

interface StatisticsData {
  id: string
  platform_store_id: string
  date: string
  place_inflow: number
  place_inflow_change: number | null
  reservation_order: number
  reservation_order_change: number | null
  smart_call: number
  smart_call_change: number | null
  review_registration: number
  review_registration_change: number | null
  inflow_channels: InflowChannelData[]
  inflow_keywords: InflowKeywordData[]
  created_at: string
  updated_at: string
}

interface InflowChannelData {
  rank: number
  channel_name: string
  count: number
}

interface InflowKeywordData {
  rank: number
  keyword: string
  count: number
}

interface PlatformStore {
  id: string
  store_name: string
  platform_store_id: string
}

const TrendIcon = ({ value }: { value: number | null }) => {
  if (value === null) return <Minus className="w-4 h-4 text-gray-400" />
  if (value > 0) return <TrendingUp className="w-4 h-4 text-green-500" />
  if (value < 0) return <TrendingDown className="w-4 h-4 text-red-500" />
  return <Minus className="w-4 h-4 text-gray-400" />
}

const TrendBadge = ({ value }: { value: number | null }) => {
  if (value === null) return <Badge variant="secondary">-</Badge>
  
  const variant = value > 0 ? 'default' : value < 0 ? 'destructive' : 'secondary'
  const sign = value > 0 ? '+' : ''
  
  return (
    <Badge variant={variant} className="ml-2">
      {sign}{value}%
    </Badge>
  )
}

export default function NaverAnalyticsPage() {
  const { user } = useAuth()
  const [stores, setStores] = useState<PlatformStore[]>([])
  const [selectedStore, setSelectedStore] = useState<string>('')
  const [statistics, setStatistics] = useState<StatisticsData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<string>('7days')
  const [refreshing, setRefreshing] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const today = new Date()
    return today.toISOString().split('T')[0] // YYYY-MM-DD 형식
  })

  // 매장 목록 조회
  const fetchStores = async () => {
    try {
      console.log('User object:', user)
      
      // Supabase 클라이언트에서 직접 access_token 가져오기
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      const accessToken = session?.access_token || user?.id
      
      console.log('Session access token:', session?.access_token)
      console.log('Final token used:', accessToken)
      
      const response = await fetch('/api/stores?platform=naver', {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      })
      
      if (!response.ok) throw new Error('매장 정보를 불러올 수 없습니다.')
      
      const data = await response.json()
      // 안전한 데이터 접근
      const storesArray = Array.isArray(data) ? data : []
      setStores(storesArray)
      
      if (storesArray.length > 0 && !selectedStore) {
        setSelectedStore(storesArray[0].id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '매장 정보 로딩 실패')
    }
  }

  // 통계 데이터 조회
  const fetchStatistics = async () => {
    if (!selectedStore) return
    
    try {
      setLoading(true)
      
      // Supabase 클라이언트에서 직접 access_token 가져오기
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      const accessToken = session?.access_token || user?.id
      
      const params = new URLSearchParams({
        store_id: selectedStore,
        period: dateRange === 'daily' ? 'daily' : dateRange,
        ...(dateRange === 'daily' && { date: selectedDate })
      })
      
      const response = await fetch(`/api/analytics/naver?${params}`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      })
      
      if (!response.ok) throw new Error('통계 데이터를 불러올 수 없습니다.')
      
      const data = await response.json()
      // 안전한 데이터 접근
      if (data && typeof data === 'object') {
        setStatistics(data)
        setError(null)
      } else {
        setError('통계 데이터 형식이 올바르지 않습니다.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '통계 데이터 로딩 실패')
    } finally {
      setLoading(false)
    }
  }

  // 통계 크롤링 실행
  const triggerCrawling = async () => {
    if (!selectedStore) return
    
    try {
      setRefreshing(true)
      
      // Supabase 클라이언트에서 직접 access_token 가져오기
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      const accessToken = session?.access_token || user?.id
      
      const store = stores.find(s => s.id === selectedStore)
      
      const response = await fetch('/api/crawling/statistics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          store_id: selectedStore,
          platform_store_id: store?.platform_store_id
        })
      })
      
      if (!response.ok) throw new Error('크롤링 실행에 실패했습니다.')
      
      // 잠시 대기 후 데이터 새로고침
      setTimeout(() => {
        fetchStatistics()
      }, 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '크롤링 실행 실패')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (user) {
      fetchStores()
    }
  }, [user])

  useEffect(() => {
    if (selectedStore) {
      fetchStatistics()
    }
  }, [selectedStore, dateRange, selectedDate])

  const getLatestStatistics = (): StatisticsData | null => {
    if (statistics.length === 0) return null
    return statistics.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())[0]
  }

  const latestStats = getLatestStatistics()

  if (!user) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="text-center">
            <h2 className="text-2xl font-semibold mb-2">로그인이 필요합니다</h2>
            <p className="text-muted-foreground">네이버 통계를 확인하려면 로그인해주세요.</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">네이버 스마트플레이스 통계</h1>
          <p className="text-muted-foreground">
            방문 전/후 지표 및 유입 분석 데이터
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* 매장 선택 */}
          <Select value={selectedStore} onValueChange={setSelectedStore}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="매장을 선택하세요" />
            </SelectTrigger>
            <SelectContent>
              {stores.map((store) => (
                <SelectItem key={store.id} value={store.id}>
                  {store.store_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* 기간 선택 */}
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">일일</SelectItem>
              <SelectItem value="7days">최근 7일</SelectItem>
              <SelectItem value="30days">최근 30일</SelectItem>
              <SelectItem value="90days">최근 90일</SelectItem>
            </SelectContent>
          </Select>

          {/* 일일 모드일 때 날짜 선택 */}
          {dateRange === 'daily' && (
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              max={new Date().toISOString().split('T')[0]}
            />
          )}

          {/* 새로고침 버튼 */}
          <Button 
            variant="outline" 
            onClick={triggerCrawling}
            disabled={refreshing || !selectedStore}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? '크롤링 중...' : '새로고침'}
          </Button>
        </div>
      </div>

      {/* 오류 메시지 */}
      {error && (
        <Alert>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 로딩 상태 */}
      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-[100px]" />
                <Skeleton className="h-4 w-4" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-7 w-[60px] mb-1" />
                <Skeleton className="h-3 w-[80px]" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <>
          {/* 최신 통계 요약 카드 */}
          {statistics.length > 0 && (
            <StatisticsSummaryCards data={statistics} />
          )}

          {/* 트렌드 차트 - 기간 모드에서만 표시 */}
          {dateRange !== 'daily' && statistics.length > 1 && (
            <StatisticsTrendChart
              data={statistics}
              title="지표 트렌드 분석"
              description="시간에 따른 각 지표의 변화 추이"
            />
          )}

          {/* 일일 모드 - 선택된 날짜 정보 */}
          {dateRange === 'daily' && statistics.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>선택된 날짜: {selectedDate}</CardTitle>
                <CardDescription>
                  {selectedDate} 일일 통계 데이터
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground">
                  해당 날짜의 네이버 스마트플레이스 통계입니다.
                </div>
              </CardContent>
            </Card>
          )}

          {/* 유입 분석 차트 */}
          {statistics.length > 0 && (
            <div className="grid gap-6 lg:grid-cols-2">
              <InflowChannelChart data={statistics} />
              <InflowKeywordChart data={statistics} />
            </div>
          )}

          {/* 데이터가 없는 경우 */}
          {!loading && statistics.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">통계 데이터가 없습니다</h3>
                <p className="text-muted-foreground text-center mb-4">
                  {dateRange === 'daily' 
                    ? `${selectedDate} 날짜의 통계 데이터가 없습니다. '새로고침' 버튼을 클릭하여 해당 날짜의 데이터를 수집하세요.`
                    : '선택한 기간의 네이버 통계 데이터를 수집하려면 \'새로고침\' 버튼을 클릭하여 크롤링을 실행하세요.'
                  }
                </p>
                <Button onClick={triggerCrawling} disabled={refreshing || !selectedStore}>
                  <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                  {refreshing ? '크롤링 중...' : '통계 수집하기'}
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
    </AppLayout>
  )
}