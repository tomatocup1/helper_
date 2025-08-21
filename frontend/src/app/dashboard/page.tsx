"use client"

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import {
  Store,
  MessageSquare,
  Star,
  TrendingUp,
  Users,
  Clock,
  AlertTriangle,
  CheckCircle,
  Plus,
  BarChart3,
  ArrowUp,
  ArrowDown
} from 'lucide-react'

// Mock data - 실제 구현 시 API에서 가져올 데이터
const mockDashboardData = {
  overview: {
    total_stores: 2,
    total_reviews: 156,
    average_rating: 4.3,
    reply_rate: 85.5,
    new_reviews_today: 5,
    pending_replies: 3
  },
  recent_reviews: [
    {
      id: '1',
      store_name: '홍대 맛집 카페',
      reviewer_name: '김고객',
      rating: 5,
      content: '정말 맛있었어요! 직원분들도 친절하시고 분위기도 좋네요.',
      sentiment: 'positive',
      reply_status: 'replied',
      created_at: '2024-08-13T14:30:00Z'
    },
    {
      id: '2',
      store_name: '강남 헤어샵',
      reviewer_name: '이고객',
      rating: 2,
      content: '서비스가 좀 아쉬웠어요. 예약 시간을 지키지 않았습니다.',
      sentiment: 'negative',
      reply_status: 'pending',
      created_at: '2024-08-13T10:15:00Z'
    },
    {
      id: '3',
      store_name: '홍대 맛집 카페',
      reviewer_name: '박고객',
      rating: 4,
      content: '커피가 맛있어요. 다만 좀 시끄러워서 공부하기는 어려울 것 같아요.',
      sentiment: 'neutral',
      reply_status: 'generated',
      created_at: '2024-08-13T09:20:00Z'
    }
  ],
  alerts: [
    {
      type: 'warning',
      message: '강남 헤어샵에 부정적 리뷰가 있습니다.',
      action: '확인 필요'
    },
    {
      type: 'info',
      message: '이번 주 리뷰 수가 20% 증가했습니다.',
      action: '리포트 보기'
    }
  ]
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [data, setData] = useState(mockDashboardData)
  
  // 개발 모드용 임시 사용자 데이터
  const displayUser = user || {
    name: '테스트 사용자',
    subscription_plan: 'free'
  }

  // 실제 구현 시 API 호출
  useEffect(() => {
    // fetchDashboardData()
  }, [])

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 1) return '방금 전'
    if (diffInHours < 24) return `${diffInHours}시간 전`
    return `${Math.floor(diffInHours / 24)}일 전`
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-50'
      case 'negative': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getReplyStatusIcon = (status: string) => {
    switch (status) {
      case 'replied': return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'generated': return <Clock className="w-4 h-4 text-blue-600" />
      case 'pending': return <AlertTriangle className="w-4 h-4 text-orange-600" />
      default: return <Clock className="w-4 h-4 text-gray-600" />
    }
  }

  return (
    <AppLayout>
      <div className="space-y-8">
      {/* 페이지 헤더 */}
      <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">대시보드</h1>
          <p className="text-gray-600 mt-1">
            안녕하세요, <span className="font-medium">{displayUser?.name}</span>님! 오늘도 가게 운영을 스마트하게 관리해보세요.
          </p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline">
            <BarChart3 className="w-4 h-4 mr-2" />
            리포트 보기
          </Button>
          <Button variant="brand" asChild>
            <Link href="/stores/add">
              <Plus className="w-4 h-4 mr-2" />
              매장 추가
            </Link>
          </Button>
        </div>
      </div>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">등록된 매장</CardTitle>
            <Store className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.overview.total_stores}</div>
            <p className="text-xs text-muted-foreground">
              활성 매장 운영 중
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">총 리뷰 수</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.overview.total_reviews}</div>
            <p className="text-xs text-green-600 flex items-center">
              <ArrowUp className="w-3 h-3 mr-1" />
              오늘 {data.overview.new_reviews_today}개 추가
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">평균 평점</CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.overview.average_rating}</div>
            <p className="text-xs text-muted-foreground flex items-center">
              <Star className="w-3 h-3 mr-1 fill-yellow-400 text-yellow-400" />
              5점 만점 기준
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">답글 완료율</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.overview.reply_rate}%</div>
            <p className="text-xs text-orange-600 flex items-center">
              <Clock className="w-3 h-3 mr-1" />
              {data.overview.pending_replies}개 답글 대기
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* 최근 리뷰 */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>최근 리뷰</span>
                <Button variant="outline" size="sm">
                  전체 보기
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.recent_reviews.map((review) => (
                  <div key={review.id} className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="font-medium text-sm">{review.store_name}</span>
                          <span className="text-gray-500">·</span>
                          <span className="text-gray-500 text-sm">{review.reviewer_name}</span>
                          <div className="flex items-center">
                            {[...Array(5)].map((_, i) => (
                              <Star
                                key={i}
                                className={`w-3 h-3 ${
                                  i < review.rating
                                    ? 'fill-yellow-400 text-yellow-400'
                                    : 'text-gray-300'
                                }`}
                              />
                            ))}
                          </div>
                        </div>
                        <p className="text-sm text-gray-700">{review.content}</p>
                      </div>
                      <div className="flex items-center space-x-2 ml-4">
                        <span className={`text-xs px-2 py-1 rounded-full ${getSentimentColor(review.sentiment)}`}>
                          {review.sentiment === 'positive' ? '긍정' : 
                           review.sentiment === 'negative' ? '부정' : '중립'}
                        </span>
                        {getReplyStatusIcon(review.reply_status)}
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{formatTime(review.created_at)}</span>
                      <span>
                        {review.reply_status === 'replied' ? '답글 완료' :
                         review.reply_status === 'generated' ? 'AI 답글 생성됨' :
                         '답글 대기 중'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 알림 및 액션 */}
        <div className="space-y-6">
          {/* 알림 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">알림</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.alerts.map((alert, index) => (
                  <div key={index} className="border-l-4 border-orange-400 bg-orange-50 p-3 rounded">
                    <div className="flex items-start space-x-2">
                      <AlertTriangle className="w-4 h-4 text-orange-600 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-orange-800">{alert.message}</p>
                        <Button variant="link" className="p-0 h-auto text-xs text-orange-600">
                          {alert.action}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 빠른 액션 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">빠른 액션</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Button variant="outline" className="w-full justify-start" asChild>
                  <Link href="/stores/add">
                    <Store className="w-4 h-4 mr-2" />
                    새 매장 등록
                  </Link>
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <MessageSquare className="w-4 h-4 mr-2" />
                  리뷰 답글 작성
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  분석 리포트 보기
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Users className="w-4 h-4 mr-2" />
                  구독 플랜 업그레이드
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 구독 정보 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">구독 정보</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">현재 플랜</span>
                  <span className="font-medium capitalize">{displayUser?.subscription_plan}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">이번 달 리뷰 분석</span>
                  <span className="text-sm">45 / 100</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-brand-600 h-2 rounded-full" style={{ width: '45%' }}></div>
                </div>
                <Button variant="brand" size="sm" className="w-full">
                  플랜 업그레이드
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
      </div>
    </AppLayout>
  )
}