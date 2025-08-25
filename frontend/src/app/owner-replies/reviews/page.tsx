"use client"

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/types/database'
import {
  MessageSquare,
  Star,
  Filter,
  Search,
  Clock,
  CheckCircle,
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Bot,
  User,
  Send,
  Eye,
  RefreshCw,
  Store,
  Calendar,
  Image
} from 'lucide-react'

type ReviewsNaverRow = Database['public']['Tables']['reviews_naver']['Row']
type PlatformStoreRow = Database['public']['Tables']['platform_stores']['Row']

interface ReviewWithStore extends ReviewsNaverRow {
  platform_store: PlatformStoreRow
}

const filterOptions = [
  { value: 'all', label: '전체', description: '모든 리뷰 상태' },
  { value: 'draft', label: '작업 필요', description: '답글 작성, 승인, 전송이 필요한 리뷰' },
  { value: 'sent', label: '답글 완료', description: '답글이 전송 완료된 리뷰' },
  { value: 'pending_approval', label: '승인 대기', description: 'AI 답글이 승인을 기다리는 중' },
  { value: 'approved', label: '전송 대기', description: '승인되어 전송을 기다리는 중' },
  { value: 'failed', label: '전송 실패', description: '답글 전송에 실패한 리뷰' }
]

const sentimentOptions = [
  { value: 'all', label: '전체' },
  { value: 'positive', label: '긍정' },
  { value: 'negative', label: '부정' },
  { value: 'neutral', label: '중립' }
]

export default function ReviewsPage() {
  const { user } = useAuth()
  const [reviews, setReviews] = useState<ReviewWithStore[]>([])
  const [filteredReviews, setFilteredReviews] = useState<ReviewWithStore[]>([])
  const [filter, setFilter] = useState('draft')
  const [sentimentFilter, setSentimentFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedStore, setSelectedStore] = useState<string>('all')
  const [stores, setStores] = useState<PlatformStoreRow[]>([])

  // Supabase 클라이언트
  const supabase = createClient()

  // 매장 목록 가져오기
  const fetchStores = useCallback(async () => {
    if (!user?.id) return

    try {
      const { data, error } = await supabase
        .from('platform_stores')
        .select('*')
        .eq('user_id', user.id)
        .eq('is_active', true)
        .order('store_name', { ascending: true })

      if (error) throw error
      setStores(data || [])
    } catch (err) {
      console.error('Error fetching stores:', err)
    }
  }, [user?.id])

  // 리뷰 데이터 가져오기 (백엔드 API 사용)
  const fetchReviews = useCallback(async () => {
    if (!user?.id) return

    setIsLoading(true)
    setError(null)

    try {
      // 먼저 사용자의 매장들 가져오기
      const { data: userStores, error: storesError } = await supabase
        .from('platform_stores')
        .select('*')
        .eq('user_id', user.id)
        .eq('is_active', true)

      if (storesError) throw storesError
      if (!userStores || userStores.length === 0) {
        setReviews([])
        setFilteredReviews([])
        return
      }

      // 백엔드 API 호출하여 모든 플랫폼의 리뷰 가져오기
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001'
      let apiUrl = `${backendUrl}/api/v1/reviews?limit=500&user_id=${user.id}`
      
      // 매장 필터 적용
      if (selectedStore !== 'all') {
        apiUrl += `&store_id=${selectedStore}`
      }

      const response = await fetch(apiUrl)
      if (!response.ok) {
        throw new Error('리뷰 조회 API 호출 실패')
      }
      
      const apiResult = await response.json()
      if (!apiResult.success) {
        throw new Error(apiResult.message || '리뷰 조회 실패')
      }

      // 매장 정보와 연결
      const reviewsWithStore = apiResult.reviews.map((review: any) => {
        const matchingStore = userStores.find(store => store.id === review.platform_store_id)
        return {
          ...review,
          platform_store: matchingStore,
          // 플랫폼별 필드명 통일 (요기요 → 네이버 형식으로)
          rating: review.overall_rating || review.rating || 0,
          reviewer_name: review.reviewer_name || '익명',
          review_text: review.review_text || '',
          review_date: review.review_date || review.created_at,
          has_photos: review.has_photos || false,
          photo_count: review.photo_count || 0,
          // 요기요 고유 필드들
          taste_rating: review.taste_rating,
          quantity_rating: review.quantity_rating,
          order_menu: review.order_menu,
          yogiyo_dsid: review.yogiyo_dsid
        }
      }).filter((review: any) => 
        // 사용자의 매장에 속하는 리뷰만 필터링
        userStores.some(store => store.id === review.platform_store_id)
      )

      setReviews(reviewsWithStore)
      console.log(`리뷰 조회 완료: ${reviewsWithStore.length}개 (요기요 포함)`)
      
    } catch (err) {
      console.error('Error fetching reviews:', err)
      setError('리뷰를 불러오는 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [user?.id, selectedStore])

  // 초기 데이터 로드
  useEffect(() => {
    fetchStores()
  }, [fetchStores])

  useEffect(() => {
    fetchReviews()
  }, [fetchReviews])

  // 필터링 로직
  useEffect(() => {
    let filtered = reviews

    // 답글 상태 필터
    if (filter !== 'all') {
      if (filter === 'draft') {
        // "답글 대기"는 작업이 필요한 모든 상태를 포함
        filtered = filtered.filter(review => 
          review.reply_status === 'draft' || 
          !review.reply_status || 
          review.reply_status === 'approved'
        )
      } else {
        filtered = filtered.filter(review => review.reply_status === filter)
      }
    }

    // 감정 필터
    if (sentimentFilter !== 'all') {
      filtered = filtered.filter(review => review.sentiment === sentimentFilter)
    }

    // 검색 필터
    if (searchTerm) {
      filtered = filtered.filter(review => 
        review.review_text?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        review.reviewer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        review.platform_store?.store_name?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    setFilteredReviews(filtered)
  }, [reviews, filter, sentimentFilter, searchTerm])

  const formatTime = (dateString: string | null) => {
    if (!dateString) return '날짜 없음'
    
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 1) return '방금 전'
    if (diffInHours < 24) return `${diffInHours}시간 전`
    if (diffInHours < 168) return `${Math.floor(diffInHours / 24)}일 전`
    
    // 한국어 날짜 형식
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const getSentimentIcon = (sentiment: string | null) => {
    switch (sentiment) {
      case 'positive':
        return <ThumbsUp className="w-4 h-4 text-green-600" />
      case 'negative':
        return <ThumbsDown className="w-4 h-4 text-red-600" />
      case 'neutral':
        return <Minus className="w-4 h-4 text-gray-600" />
      default:
        return <Minus className="w-4 h-4 text-gray-400" />
    }
  }

  const getSentimentColor = (sentiment: string | null) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-50'
      case 'negative': return 'text-red-600 bg-red-50'
      case 'neutral': return 'text-gray-600 bg-gray-50'
      default: return 'text-gray-400 bg-gray-50'
    }
  }

  const getReplyStatusIcon = (status: string | null) => {
    switch (status) {
      case 'sent':
        return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-blue-600" />
      case 'pending_approval':
        return <Clock className="w-4 h-4 text-yellow-600" />
      case 'draft':
        return <Clock className="w-4 h-4 text-orange-600" />
      case 'failed':
        return <AlertTriangle className="w-4 h-4 text-red-600" />
      default:
        return <Minus className="w-4 h-4 text-gray-400" />
    }
  }

  const getReplyStatusText = (status: string | null) => {
    switch (status) {
      case 'sent': return '답글 완료'
      case 'approved': return '승인됨'
      case 'pending_approval': return '승인 대기'
      case 'draft': return '답글 대기'
      case 'failed': return '전송 실패'
      default: return '미답변'
    }
  }

  const getReplyStatusColor = (status: string | null) => {
    switch (status) {
      case 'sent': return 'bg-green-100 text-green-800'
      case 'approved': return 'bg-blue-100 text-blue-800'
      case 'pending_approval': return 'bg-yellow-100 text-yellow-800'
      case 'draft': return 'bg-orange-100 text-orange-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  // 통계 계산 (필터 로직과 동일하게)
  const statistics = {
    total: reviews.length,
    // "답글 대기"에는 draft, null, approved 상태 모두 포함
    draft: reviews.filter(r => 
      r.reply_status === 'draft' || 
      !r.reply_status || 
      r.reply_status === 'approved'
    ).length,
    sent: reviews.filter(r => r.reply_status === 'sent').length,
    pending: reviews.filter(r => r.reply_status === 'pending_approval').length,
    approved: reviews.filter(r => r.reply_status === 'approved').length,
    failed: reviews.filter(r => r.reply_status === 'failed').length,
    averageRating: reviews.length > 0 
      ? (reviews.reduce((acc, r) => acc + (r.rating || 0), 0) / reviews.length).toFixed(1)
      : '0.0',
    positiveRate: reviews.length > 0
      ? Math.round((reviews.filter(r => r.sentiment === 'positive').length / reviews.length) * 100)
      : 0
  }

  return (
    <AppLayout>
      <div className="space-y-8">
      {/* 페이지 헤더 */}
      <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">리뷰 관리</h1>
          <p className="text-gray-600 mt-1">
            모든 플랫폼의 리뷰를 관리하고 답글을 작성하세요. (네이버, 쿠팡잇츠)
          </p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" onClick={fetchReviews}>
            <RefreshCw className="w-4 h-4 mr-2" />
            새로고침
          </Button>
          <Button variant="outline">
            <Bot className="w-4 h-4 mr-2" />
            AI 답글 일괄 생성
          </Button>
        </div>
      </div>

      {/* 요약 통계 - 클릭 가능 */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('all')}>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <MessageSquare className="w-5 h-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600">총 리뷰</p>
                <p className="text-2xl font-bold text-blue-600">{statistics.total}</p>
              </div>
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-xs">전체 보기</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className={`cursor-pointer hover:shadow-md transition-shadow ${
          filter === 'draft' ? 'ring-2 ring-orange-500 bg-orange-50' : ''
        }`} onClick={() => setFilter('draft')} title="답글 작성, 승인, 전송이 필요한 리뷰">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-orange-600" />
              <div>
                <p className="text-sm text-gray-600">작업 필요</p>
                <p className="text-2xl font-bold text-orange-600">{statistics.draft}</p>
              </div>
            </div>
            <div className="mt-2">
              <Badge className="text-xs bg-orange-100 text-orange-700">⚙️ 작업 필요</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className={`cursor-pointer hover:shadow-md transition-shadow ${
          filter === 'sent' ? 'ring-2 ring-green-500 bg-green-50' : ''
        }`} onClick={() => setFilter('sent')}>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600">답글 완료</p>
                <p className="text-2xl font-bold text-green-600">{statistics.sent}</p>
              </div>
            </div>
            <div className="mt-2">
              <Badge className="text-xs bg-green-100 text-green-700">✅ 완료</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-default">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Star className="w-5 h-5 text-yellow-500" />
              <div>
                <p className="text-sm text-gray-600">평균 평점</p>
                <p className="text-2xl font-bold text-yellow-600">{statistics.averageRating}</p>
              </div>
            </div>
            <div className="mt-2">
              <div className="flex">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-3 h-3 ${
                      i < Math.floor(parseFloat(statistics.averageRating))
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-gray-300'
                    }`}
                  />
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-default">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <ThumbsUp className="w-5 h-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600">긍정 비율</p>
                <p className="text-2xl font-bold text-green-600">{statistics.positiveRate}%</p>
              </div>
            </div>
            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-600 h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${statistics.positiveRate}%` }}
                ></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 필터 및 검색 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col space-y-4 md:flex-row md:items-center md:space-y-0 md:space-x-4">
            {/* 매장 선택 */}
            <select
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              value={selectedStore}
              onChange={(e) => setSelectedStore(e.target.value)}
            >
              <option value="all">모든 매장</option>
              {stores.map(store => (
                <option key={store.id} value={store.id}>
                  {store.store_name}
                </option>
              ))}
            </select>

            {/* 검색 */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="리뷰 내용, 매장명, 작성자로 검색..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>

            <div className="flex space-x-2">
              {/* 답글 상태 필터 */}
              <select
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                {filterOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>

              {/* 감정 필터 */}
              <select
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                value={sentimentFilter}
                onChange={(e) => setSentimentFilter(e.target.value)}
              >
                {sentimentOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 리뷰 목록 */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-6">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
                  <div className="space-y-3">
                    <div className="h-3 bg-gray-200 rounded"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <Card className="text-center py-12">
            <CardContent>
              <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">오류 발생</h3>
              <p className="text-gray-600">{error}</p>
              <Button variant="outline" className="mt-4" onClick={fetchReviews}>
                다시 시도
              </Button>
            </CardContent>
          </Card>
        ) : (
          filteredReviews.map((review) => {
            const getCardBorderStyle = (status: string | null) => {
              switch (status) {
                case 'sent':
                  return 'border-l-4 border-l-green-500 bg-green-50/30'
                case 'approved':
                  return 'border-l-4 border-l-blue-500 bg-blue-50/30'
                case 'pending_approval':
                  return 'border-l-4 border-l-yellow-500 bg-yellow-50/30'
                case 'draft':
                  return 'border-l-4 border-l-orange-500 bg-orange-50/30'
                case 'failed':
                  return 'border-l-4 border-l-red-500 bg-red-50/30'
                default:
                  return 'border-l-4 border-l-gray-300'
              }
            }
            
            return (
            <Card key={review.id} className={`hover:shadow-md transition-shadow ${getCardBorderStyle(review.reply_status)}`}>
              <CardContent className="p-6">
                <div className="space-y-4">
                  {/* 리뷰 헤더 */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <div className="flex items-center space-x-2">
                          <Store className="w-4 h-4 text-gray-500" />
                          <span className="font-medium">{review.platform_store?.store_name}</span>
                        </div>
                        <span className="text-gray-500">·</span>
                        <span className="text-gray-700">{review.reviewer_name || '익명'}</span>
                        {review.reviewer_level && (
                          <>
                            <span className="text-gray-500">·</span>
                            <Badge variant="outline" className="text-xs">
                              {review.reviewer_level}
                            </Badge>
                          </>
                        )}
                        {review.is_visited_review && (
                          <Badge variant="secondary" className="text-xs">
                            방문 인증
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className="flex items-center">
                          {[...Array(5)].map((_, i) => (
                            <Star
                              key={i}
                              className={`w-4 h-4 ${
                                i < (review.rating || 0)
                                  ? 'fill-yellow-400 text-yellow-400'
                                  : 'text-gray-300'
                              }`}
                            />
                          ))}
                        </div>
                        {/* 요기요 세부 별점 표시 */}
                        {((review as any).taste_rating || (review as any).quantity_rating) && (
                          <div className="flex items-center space-x-2 text-xs text-gray-600">
                            {(review as any).taste_rating && (
                              <span>맛 {(review as any).taste_rating}★</span>
                            )}
                            {(review as any).quantity_rating && (
                              <span>양 {(review as any).quantity_rating}★</span>
                            )}
                          </div>
                        )}
                        <div className="flex items-center space-x-2 text-sm text-gray-500">
                          <Calendar className="w-3 h-3" />
                          <span>{formatTime(review.review_date)}</span>
                        </div>
                        {review.has_photos && (
                          <div className="flex items-center space-x-1 text-sm text-gray-500">
                            <Image className="w-3 h-3" />
                            <span>{review.photo_count}장</span>
                          </div>
                        )}
                        {/* 플랫폼 표시 */}
                        {(review as any).platform && (
                          <Badge variant="outline" className="text-xs capitalize">
                            {(review as any).platform}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {review.sentiment && (
                        <span className={`text-xs px-2 py-1 rounded-full ${getSentimentColor(review.sentiment)}`}>
                          {review.sentiment === 'positive' ? '긍정' : 
                           review.sentiment === 'negative' ? '부정' : '중립'}
                        </span>
                      )}
                      <div className="flex items-center space-x-1">
                        {getReplyStatusIcon(review.reply_status)}
                        <span className={`text-xs px-2 py-1 rounded-full ${getReplyStatusColor(review.reply_status)}`}>
                          {getReplyStatusText(review.reply_status)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 리뷰 내용 */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-gray-800 whitespace-pre-wrap">{review.review_text || '내용 없음'}</p>
                    
                    {/* 요기요 주문 메뉴 표시 */}
                    {(review as any).order_menu && (
                      <div className="mt-3 p-2 bg-blue-50 rounded border-l-4 border-blue-400">
                        <p className="text-xs text-blue-700 font-medium">주문 메뉴</p>
                        <p className="text-xs text-blue-800 mt-1">{(review as any).order_menu}</p>
                      </div>
                    )}
                    
                    {review.extracted_keywords && Array.isArray(review.extracted_keywords) && review.extracted_keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {(review.extracted_keywords as string[]).map((keyword, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            #{keyword}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 사업자 답글 */}
                  {review.reply_text && (
                    <div className="bg-brand-50 rounded-lg p-4 ml-8">
                      <div className="flex items-center space-x-2 mb-2">
                        <User className="w-4 h-4 text-brand-600" />
                        <span className="text-sm font-medium text-brand-700">사장님</span>
                        {review.reply_sent_at && (
                          <span className="text-xs text-gray-500">
                            · {formatTime(review.reply_sent_at)}
                          </span>
                        )}
                      </div>
                      <p className="text-gray-800 whitespace-pre-wrap">{review.reply_text}</p>
                    </div>
                  )}

                  {/* AI 생성 답글 (답글 완료된 경우 숨김) */}
                  {review.ai_generated_reply && review.reply_status !== 'sent' && (
                    <div className="bg-purple-50 rounded-lg p-4 ml-8 border border-purple-200">
                      <div className="flex items-center space-x-2 mb-2">
                        <Bot className="w-4 h-4 text-purple-600" />
                        <span className="text-sm font-medium text-purple-700">AI 생성 답글</span>
                        {review.ai_confidence_score && (
                          <Badge variant="outline" className="text-xs">
                            신뢰도 {Math.round(review.ai_confidence_score * 100)}%
                          </Badge>
                        )}
                        <Badge className="text-xs bg-purple-100 text-purple-700">
                          {getReplyStatusText(review.reply_status)}
                        </Badge>
                      </div>
                      <p className="text-gray-800 whitespace-pre-wrap">{review.ai_generated_reply}</p>
                      
                      {/* AI 답글에 대한 액션 버튼 */}
                      <div className="flex space-x-2 mt-3 pt-3 border-t border-purple-200">
                        {review.reply_status === 'draft' && (
                          <>
                            <Button variant="outline" size="sm" className="text-purple-600 border-purple-200">
                              <Eye className="w-3 h-3 mr-1" />
                              검토
                            </Button>
                            <Button size="sm" className="bg-purple-600 hover:bg-purple-700">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              승인 후 전송
                            </Button>
                          </>
                        )}
                        {review.reply_status === 'pending_approval' && (
                          <>
                            <Button variant="outline" size="sm">
                              수정
                            </Button>
                            <Button size="sm" className="bg-green-600 hover:bg-green-700">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              승인
                            </Button>
                          </>
                        )}
                        {review.reply_status === 'approved' && (
                          <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                            <Send className="w-3 h-3 mr-1" />
                            답글 전송
                          </Button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 하단 액션 버튼 - AI 답글이 없거나 답글이 없는 경우만 표시 */}
                  {(!review.ai_generated_reply || review.reply_status === 'sent') && (
                    <div className="flex items-center justify-between pt-4 border-t">
                      <div className="flex items-center space-x-2 text-sm text-gray-600">
                        {getSentimentIcon(review.sentiment)}
                        <span>{getReplyStatusText(review.reply_status)}</span>
                        {review.reply_status === 'sent' && (
                          <Badge className="text-xs bg-green-100 text-green-700">
                            ✅ 답글 완료
                          </Badge>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        {(review.reply_status === 'draft' || !review.reply_status) && !review.ai_generated_reply && (
                          <>
                            <Button variant="outline" size="sm">
                              <Bot className="w-4 h-4 mr-2" />
                              AI 답글 생성
                            </Button>
                            <Button variant="brand" size="sm">
                              <Send className="w-4 h-4 mr-2" />
                              직접 답글
                            </Button>
                          </>
                        )}
                        {review.reply_status === 'sent' && (
                          <Button variant="outline" size="sm">
                            <Eye className="w-4 h-4 mr-2" />
                            답글 보기
                          </Button>
                        )}
                        {review.reply_status === 'failed' && (
                          <Button variant="outline" size="sm">
                            <RefreshCw className="w-4 h-4 mr-2" />
                            재시도
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
            )
          })
        )}
      </div>

      {/* 빈 상태 */}
      {!isLoading && !error && filteredReviews.length === 0 && (
        <Card className="text-center py-12">
          <CardContent>
            <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {searchTerm ? '검색 결과가 없습니다' :
               filter === 'draft' ? '작업이 필요한 리뷰가 없습니다' :
               filter === 'sent' ? '답글을 완료한 리뷰가 없습니다' :
               filter !== 'all' || sentimentFilter !== 'all' ? '필터 조건에 맞는 리뷰가 없습니다' :
               '리뷰가 없습니다'
              }
            </h3>
            <p className="text-gray-600">
              {searchTerm ? '다른 검색어를 시도해보세요.' :
               filter === 'draft' ? '모든 리뷰에 대한 작업이 완료되었습니다! 🎉 답글 생성, 승인, 전송이 모두 끝났어요.' :
               filter === 'sent' ? '답글을 완료한 리뷰들을 확인하세요.' :
               filter !== 'all' || sentimentFilter !== 'all' ? '다른 필터 조건을 시도해보세요.' :
               stores.length === 0 ? '먼저 매장을 등록해주세요.' :
               '네이버 리뷰가 수집되면 여기에 표시됩니다.'
              }
            </p>
            <div className="mt-4 space-x-2">
              {stores.length === 0 && (
                <Button variant="brand" onClick={() => window.location.href = '/stores/add'}>
                  매장 등록하기
                </Button>
              )}
              {filter === 'draft' && reviews.length > 0 && (
                <Button variant="outline" onClick={() => setFilter('all')}>
                  모든 리뷰 보기
                </Button>
              )}
              {(searchTerm || filter !== 'draft' || sentimentFilter !== 'all') && (
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setSearchTerm('')
                    setFilter('draft')
                    setSentimentFilter('all')
                  }}
                >
                  작업 필요한 리뷰 보기
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
      </div>
    </AppLayout>
  )
}