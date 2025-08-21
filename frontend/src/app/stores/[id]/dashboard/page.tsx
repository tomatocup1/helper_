"use client"

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/store/auth-store-supabase'
import { createClient } from '@/lib/supabase/client'
import {
  ArrowLeft,
  Store,
  Settings,
  Activity,
  BarChart,
  MessageSquare,
  Star,
  TrendingUp,
  Calendar,
  Users,
  RefreshCw,
  ExternalLink
} from 'lucide-react'

interface PlatformStore {
  id: string
  store_name: string
  platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
  platform_store_id: string
  platform_id?: string
  business_type?: string
  address?: string
  phone?: string
  is_active: boolean
  crawling_enabled: boolean
  last_crawled_at?: string
  created_at: string
  total_reviews?: number
  average_rating?: number
}

interface DashboardStats {
  totalReviews: number
  averageRating: number
  recentReviews: number
  pendingReplies: number
  crawlingStatus: 'active' | 'inactive' | 'error'
  lastCrawledAt?: string
}

const platformNames = {
  naver: '네이버 플레이스',
  baemin: '배달의민족',
  yogiyo: '요기요',
  coupangeats: '쿠팡이츠'
}

const platformColors = {
  naver: 'bg-green-500',
  baemin: 'bg-blue-500',
  yogiyo: 'bg-orange-500',
  coupangeats: 'bg-purple-500'
}

export default function StoreDashboardPage() {
  const params = useParams()
  const router = useRouter()
  const { user, isAuthenticated } = useAuth()
  const [store, setStore] = useState<PlatformStore | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCrawling, setIsCrawling] = useState(false)
  const supabase = createClient()

  const storeId = params.id as string

  useEffect(() => {
    if (isAuthenticated && user && storeId) {
      fetchStoreAndStats()
    }
  }, [isAuthenticated, user, storeId])

  const fetchStoreAndStats = async () => {
    try {
      setIsLoading(true)

      // 매장 정보 조회
      const { data: storeData, error: storeError } = await supabase
        .from('platform_stores')
        .select('*')
        .eq('id', storeId)
        .eq('user_id', user?.id)
        .single()

      if (storeError || !storeData) {
        console.error('Store not found:', storeError)
        router.push('/stores')
        return
      }

      setStore(storeData)

      // 대시보드 통계 데이터 생성 (실제 구현에서는 API에서 가져와야 함)
      const mockStats: DashboardStats = {
        totalReviews: storeData.total_reviews || 0,
        averageRating: storeData.average_rating || 0,
        recentReviews: Math.floor(Math.random() * 10) + 1,
        pendingReplies: Math.floor(Math.random() * 5),
        crawlingStatus: storeData.crawling_enabled ? 'active' : 'inactive',
        lastCrawledAt: storeData.last_crawled_at
      }

      setStats(mockStats)
    } catch (error) {
      console.error('Error fetching store data:', error)
      router.push('/stores')
    } finally {
      setIsLoading(false)
    }
  }

  const handleManualCrawl = async () => {
    if (!store) return

    setIsCrawling(true)
    try {
      // 수동 크롤링 API 호출 (향후 구현)
      console.log('Manual crawling triggered for store:', store.id)
      
      // 시뮬레이션 지연
      await new Promise(resolve => setTimeout(resolve, 3000))
      
      // 통계 새로고침
      await fetchStoreAndStats()
    } catch (error) {
      console.error('Manual crawling failed:', error)
    } finally {
      setIsCrawling(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto"></div>
          <p className="text-gray-600">매장 정보를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  if (!store) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <Store className="w-12 h-12 text-gray-400 mx-auto" />
          <p className="text-gray-600">매장을 찾을 수 없습니다.</p>
          <Link href="/stores">
            <Button variant="outline">매장 목록으로 돌아가기</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center space-x-4">
        <Link href="/stores">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center space-x-3">
            <Store className="w-6 h-6 text-brand-600" />
            <div>
              <h1 className="text-3xl font-bold brand-text">{store.store_name}</h1>
              <div className="flex items-center space-x-4 mt-1">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${platformColors[store.platform]}`}></div>
                  <span className="text-sm text-muted-foreground">
                    {platformNames[store.platform]}
                  </span>
                </div>
                <span className="text-sm text-muted-foreground">
                  ID: {store.platform_store_id}
                </span>
                <Badge variant={store.is_active ? "default" : "secondary"}>
                  {store.is_active ? "활성" : "비활성"}
                </Badge>
              </div>
            </div>
          </div>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/stores/${store.id}/settings`}>
              <Settings className="w-4 h-4 mr-2" />
              설정
            </Link>
          </Button>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <MessageSquare className="w-5 h-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">총 리뷰</p>
                <p className="text-2xl font-bold">{stats?.totalReviews || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Star className="w-5 h-5 text-yellow-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">평균 평점</p>
                <p className="text-2xl font-bold">
                  {stats?.averageRating ? stats.averageRating.toFixed(1) : '0.0'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-green-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">최근 리뷰</p>
                <p className="text-2xl font-bold">{stats?.recentReviews || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-purple-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">답글 대기</p>
                <p className="text-2xl font-bold">{stats?.pendingReplies || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 주요 기능 카드들 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 크롤링 관리 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="w-5 h-5" />
              <span>크롤링 관리</span>
            </CardTitle>
            <CardDescription>
              매장 리뷰 자동 수집 설정 및 수동 실행
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">자동 크롤링</span>
              <Badge variant={store.crawling_enabled ? "default" : "secondary"}>
                {store.crawling_enabled ? "활성" : "비활성"}
              </Badge>
            </div>
            
            {stats?.lastCrawledAt && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">마지막 수집</span>
                <span className="text-sm text-muted-foreground">
                  {new Date(stats.lastCrawledAt).toLocaleDateString('ko-KR', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            )}

            <Button 
              className="w-full" 
              onClick={handleManualCrawl}
              disabled={isCrawling}
            >
              {isCrawling ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                  수집 중...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  수동 수집 실행
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* 리뷰 관리 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="w-5 h-5" />
              <span>리뷰 관리</span>
            </CardTitle>
            <CardDescription>
              수집된 리뷰 조회 및 AI 답글 관리
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-blue-600">{stats?.totalReviews || 0}</p>
                <p className="text-xs text-muted-foreground">전체 리뷰</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-600">{stats?.pendingReplies || 0}</p>
                <p className="text-xs text-muted-foreground">답글 대기</p>
              </div>
            </div>
            
            <Button variant="outline" className="w-full" asChild>
              <Link href={`/stores/${store.id}/reviews`}>
                <MessageSquare className="w-4 h-4 mr-2" />
                리뷰 목록 보기
              </Link>
            </Button>
          </CardContent>
        </Card>

        {/* 통계 및 분석 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart className="w-5 h-5" />
              <span>통계 및 분석</span>
            </CardTitle>
            <CardDescription>
              리뷰 트렌드 및 감정 분석 결과
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>평균 평점</span>
                <span className="font-medium">
                  {stats?.averageRating ? stats.averageRating.toFixed(1) : '0.0'} / 5.0
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-yellow-500 h-2 rounded-full" 
                  style={{ 
                    width: `${((stats?.averageRating || 0) / 5) * 100}%` 
                  }}
                ></div>
              </div>
            </div>
            
            <Button variant="outline" className="w-full" asChild>
              <Link href={`/stores/${store.id}/analytics`}>
                <BarChart className="w-4 h-4 mr-2" />
                상세 분석 보기
              </Link>
            </Button>
          </CardContent>
        </Card>

        {/* 매장 정보 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Store className="w-5 h-5" />
              <span>매장 정보</span>
            </CardTitle>
            <CardDescription>
              기본 정보 및 설정 관리
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2 text-sm">
              {store.business_type && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">업종</span>
                  <span>{store.business_type}</span>
                </div>
              )}
              {store.address && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">주소</span>
                  <span className="text-right max-w-[200px] truncate">{store.address}</span>
                </div>
              )}
              {store.phone && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">전화번호</span>
                  <span>{store.phone}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">등록일</span>
                <span>
                  {new Date(store.created_at).toLocaleDateString('ko-KR')}
                </span>
              </div>
            </div>
            
            <Button variant="outline" className="w-full" asChild>
              <Link href={`/stores/${store.id}/settings`}>
                <Settings className="w-4 h-4 mr-2" />
                매장 설정
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}