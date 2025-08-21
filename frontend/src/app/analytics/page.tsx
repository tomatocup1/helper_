"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Star,
  MessageSquare,
  Users,
  Calendar,
  Download,
  Filter,
  RefreshCw,
  Target,
  Award,
  AlertCircle
} from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

// Mock data - 실제 구현 시 API에서 가져올 데이터
const mockAnalyticsData = {
  overview: {
    total_reviews_this_month: 45,
    reviews_growth: 12.5,
    average_rating_this_month: 4.3,
    rating_change: 0.2,
    reply_rate_this_month: 89.5,
    reply_rate_change: 5.2,
    customer_satisfaction: 85.2,
    satisfaction_change: -2.1
  },
  monthly_reviews: [
    { month: '1월', reviews: 28, rating: 4.1 },
    { month: '2월', reviews: 32, rating: 4.2 },
    { month: '3월', reviews: 38, rating: 4.0 },
    { month: '4월', reviews: 41, rating: 4.3 },
    { month: '5월', reviews: 35, rating: 4.4 },
    { month: '6월', reviews: 45, rating: 4.3 }
  ],
  sentiment_distribution: [
    { name: '긍정', value: 68, color: '#10b981' },
    { name: '중립', value: 22, color: '#6b7280' },
    { name: '부정', value: 10, color: '#ef4444' }
  ],
  rating_distribution: [
    { rating: '5점', count: 28, percentage: 62.2 },
    { rating: '4점', count: 8, percentage: 17.8 },
    { rating: '3점', count: 5, percentage: 11.1 },
    { rating: '2점', count: 3, percentage: 6.7 },
    { rating: '1점', count: 1, percentage: 2.2 }
  ],
  popular_keywords: [
    { keyword: '맛있다', count: 15, sentiment: 'positive' },
    { keyword: '친절', count: 12, sentiment: 'positive' },
    { keyword: '깨끗', count: 8, sentiment: 'positive' },
    { keyword: '대기시간', count: 6, sentiment: 'negative' },
    { keyword: '가격', count: 5, sentiment: 'neutral' },
    { keyword: '서비스', count: 4, sentiment: 'negative' }
  ],
  store_performance: [
    {
      store_name: '홍대 맛집 카페',
      total_reviews: 28,
      average_rating: 4.5,
      sentiment_score: 0.75,
      reply_rate: 92.9,
      trend: 'up'
    },
    {
      store_name: '강남 헤어샵',
      total_reviews: 17,
      average_rating: 4.1,
      sentiment_score: 0.65,
      reply_rate: 82.4,
      trend: 'down'
    }
  ],
  platform_analytics: [
    { platform: '네이버', reviews: 20, rating: 4.4, growth: 15.2 },
    { platform: '구글', reviews: 15, rating: 4.2, growth: 8.7 },
    { platform: '카카오맵', reviews: 10, rating: 4.3, growth: 12.1 }
  ]
}

const periods = [
  { value: 'last_7_days', label: '최근 7일' },
  { value: 'last_30_days', label: '최근 30일' },
  { value: 'last_3_months', label: '최근 3개월' },
  { value: 'last_6_months', label: '최근 6개월' }
]

export default function AnalyticsPage() {
  const { user } = useAuth()
  const [data, setData] = useState(mockAnalyticsData)
  const [period, setPeriod] = useState('last_30_days')
  const [isLoading, setIsLoading] = useState(false)

  // 실제 구현 시 API 호출
  useEffect(() => {
    setIsLoading(true)
    // fetchAnalyticsData(period)
    setTimeout(() => setIsLoading(false), 1000)
  }, [period])

  const formatPercentage = (value: number, showSign: boolean = true) => {
    const sign = value > 0 ? '+' : ''
    return `${showSign ? sign : ''}${value.toFixed(1)}%`
  }

  const getTrendIcon = (value: number) => {
    if (value > 0) {
      return <TrendingUp className="w-4 h-4 text-green-600" />
    } else if (value < 0) {
      return <TrendingDown className="w-4 h-4 text-red-600" />
    }
    return null
  }

  const getTrendColor = (value: number) => {
    if (value > 0) return 'text-green-600'
    if (value < 0) return 'text-red-600'
    return 'text-gray-600'
  }

  const getKeywordSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'bg-green-100 text-green-800'
      case 'negative': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <AppLayout>
      <div className="space-y-8">
      {/* 페이지 헤더 */}
      <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">분석 리포트</h1>
          <p className="text-gray-600 mt-1">
            매장 운영 데이터를 분석하고 인사이트를 확인하세요.
          </p>
        </div>
        <div className="flex space-x-3">
          <select
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            {periods.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <Button variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            새로고침
          </Button>
          <Button variant="brand">
            <Download className="w-4 h-4 mr-2" />
            리포트 다운로드
          </Button>
        </div>
      </div>

      {/* 핵심 지표 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">이번 달 리뷰 수</p>
                <p className="text-2xl font-bold">{data.overview.total_reviews_this_month}</p>
              </div>
              <MessageSquare className="w-8 h-8 text-blue-600" />
            </div>
            <div className={`flex items-center mt-2 text-sm ${getTrendColor(data.overview.reviews_growth)}`}>
              {getTrendIcon(data.overview.reviews_growth)}
              <span className="ml-1">
                전월 대비 {formatPercentage(data.overview.reviews_growth)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">평균 평점</p>
                <p className="text-2xl font-bold">{data.overview.average_rating_this_month}</p>
              </div>
              <Star className="w-8 h-8 text-yellow-500" />
            </div>
            <div className={`flex items-center mt-2 text-sm ${getTrendColor(data.overview.rating_change)}`}>
              {getTrendIcon(data.overview.rating_change)}
              <span className="ml-1">
                전월 대비 {formatPercentage(data.overview.rating_change)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">답글 완료율</p>
                <p className="text-2xl font-bold">{data.overview.reply_rate_this_month}%</p>
              </div>
              <Target className="w-8 h-8 text-green-600" />
            </div>
            <div className={`flex items-center mt-2 text-sm ${getTrendColor(data.overview.reply_rate_change)}`}>
              {getTrendIcon(data.overview.reply_rate_change)}
              <span className="ml-1">
                전월 대비 {formatPercentage(data.overview.reply_rate_change)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">고객 만족도</p>
                <p className="text-2xl font-bold">{data.overview.customer_satisfaction}%</p>
              </div>
              <Award className="w-8 h-8 text-purple-600" />
            </div>
            <div className={`flex items-center mt-2 text-sm ${getTrendColor(data.overview.satisfaction_change)}`}>
              {getTrendIcon(data.overview.satisfaction_change)}
              <span className="ml-1">
                전월 대비 {formatPercentage(data.overview.satisfaction_change)}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* 월별 리뷰 추이 */}
        <Card>
          <CardHeader>
            <CardTitle>월별 리뷰 추이</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.monthly_reviews}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" domain={[0, 5]} />
                <Tooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="reviews" fill="#3b82f6" name="리뷰 수" />
                <Line 
                  yAxisId="right" 
                  type="monotone" 
                  dataKey="rating" 
                  stroke="#f59e0b" 
                  strokeWidth={3}
                  name="평균 평점" 
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 감정 분석 */}
        <Card>
          <CardHeader>
            <CardTitle>리뷰 감정 분석</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.sentiment_distribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name} ${value}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {data.sentiment_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* 평점 분포 */}
        <Card>
          <CardHeader>
            <CardTitle>평점 분포</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.rating_distribution.map((item, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <span className="w-8 text-sm font-medium">{item.rating}</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-yellow-500 h-2 rounded-full" 
                      style={{ width: `${item.percentage}%` }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-600 w-12 text-right">{item.count}개</span>
                  <span className="text-xs text-gray-500 w-12 text-right">{item.percentage}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 인기 키워드 */}
        <Card>
          <CardHeader>
            <CardTitle>인기 키워드</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.popular_keywords.map((keyword, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-medium">#{keyword.keyword}</span>
                    <Badge className={getKeywordSentimentColor(keyword.sentiment)}>
                      {keyword.sentiment === 'positive' ? '긍정' : 
                       keyword.sentiment === 'negative' ? '부정' : '중립'}
                    </Badge>
                  </div>
                  <span className="text-sm text-gray-600">{keyword.count}회</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 매장별 성과 */}
      <Card>
        <CardHeader>
          <CardTitle>매장별 성과 비교</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3">매장명</th>
                  <th className="text-center py-3">리뷰 수</th>
                  <th className="text-center py-3">평균 평점</th>
                  <th className="text-center py-3">감정 점수</th>
                  <th className="text-center py-3">답글 완료율</th>
                  <th className="text-center py-3">트렌드</th>
                </tr>
              </thead>
              <tbody>
                {data.store_performance.map((store, index) => (
                  <tr key={index} className="border-b">
                    <td className="py-3 font-medium">{store.store_name}</td>
                    <td className="text-center py-3">{store.total_reviews}</td>
                    <td className="text-center py-3">
                      <div className="flex items-center justify-center">
                        <Star className="w-4 h-4 text-yellow-500 mr-1" />
                        {store.average_rating}
                      </div>
                    </td>
                    <td className="text-center py-3">
                      <Badge 
                        className={
                          store.sentiment_score > 0.7 ? 'bg-green-100 text-green-800' :
                          store.sentiment_score > 0.5 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }
                      >
                        {(store.sentiment_score * 100).toFixed(0)}%
                      </Badge>
                    </td>
                    <td className="text-center py-3">{store.reply_rate}%</td>
                    <td className="text-center py-3">
                      {store.trend === 'up' ? (
                        <TrendingUp className="w-4 h-4 text-green-600 mx-auto" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-600 mx-auto" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* 플랫폼별 분석 */}
      <Card>
        <CardHeader>
          <CardTitle>플랫폼별 분석</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            {data.platform_analytics.map((platform, index) => (
              <div key={index} className="border rounded-lg p-4">
                <h4 className="font-medium mb-3">{platform.platform}</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">리뷰 수</span>
                    <span className="font-medium">{platform.reviews}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">평균 평점</span>
                    <span className="font-medium">{platform.rating}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">성장률</span>
                    <span className={`font-medium ${getTrendColor(platform.growth)}`}>
                      {formatPercentage(platform.growth)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 인사이트 및 권장사항 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-blue-600" />
            <span>AI 인사이트 및 권장사항</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
              <h4 className="font-medium text-blue-800 mb-2">📈 긍정적인 트렌드</h4>
              <p className="text-sm text-blue-700">
                이번 달 리뷰 수가 전월 대비 12.5% 증가했습니다. 특히 '맛있다', '친절'과 같은 긍정적 키워드가 늘어났습니다.
              </p>
            </div>
            
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
              <h4 className="font-medium text-yellow-800 mb-2">⚠️ 주의사항</h4>
              <p className="text-sm text-yellow-700">
                '대기시간'과 '서비스' 관련 부정적 리뷰가 증가했습니다. 운영 프로세스 개선을 검토해보세요.
              </p>
            </div>
            
            <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded">
              <h4 className="font-medium text-green-800 mb-2">💡 권장사항</h4>
              <p className="text-sm text-green-700">
                답글 완료율이 89.5%로 우수합니다. AI 답글 자동화를 통해 100% 달성을 목표로 하세요.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      </div>
    </AppLayout>
  )
}