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
  requires_approval?: boolean
  scheduled_reply_date?: string
  schedulable_reply_date?: string
}

const filterOptions = [
  { value: 'all', label: '전체', description: '모든 리뷰 상태' },
  { value: 'draft', label: '미답변 리뷰', description: '답글 작성, 승인, 전송이 필요한 리뷰' },
  { value: 'sent', label: '답글 완료', description: '답글이 전송 완료된 리뷰' },
  { value: 'requires_approval', label: '확인 필요', description: '사장님 확인이 필요하여 답글 등록되지 않은 리뷰' },
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

const platformOptions = [
  { value: 'all', label: '전체 플랫폼' },
  { value: 'naver', label: '네이버' },
  { value: 'baemin', label: '배민' },
  { value: 'coupangeats', label: '쿠팡잇츠' },
  { value: 'yogiyo', label: '요기요' }
]

export default function ReviewsPage() {
  const { user } = useAuth()
  const [reviews, setReviews] = useState<ReviewWithStore[]>([])
  const [filteredReviews, setFilteredReviews] = useState<ReviewWithStore[]>([])
  const [filter, setFilter] = useState('all')
  const [sentimentFilter, setSentimentFilter] = useState('all')
  const [platformFilter, setPlatformFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedStore, setSelectedStore] = useState<string>('all')
  const [stores, setStores] = useState<PlatformStoreRow[]>([])

  // 상태 디버깅 (필요시 활성화)
  // console.log('컴포넌트 렌더링 - filter:', filter, 'filteredReviews.length:', filteredReviews.length, 'reviews.length:', reviews.length)

  // Supabase 클라이언트
  const supabase = createClient()

  // 매장 목록 가져오기 (Supabase 직접 사용)
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
      console.log('Stores loaded:', data)
    } catch (err) {
      console.error('Error fetching stores:', err)
      setStores([])
    }
  }, [user?.id])

  // 리뷰 데이터 가져오기 (백엔드 API 사용)
  const fetchReviews = useCallback(async () => {
    // 인증된 사용자만 리뷰 조회 가능
    if (!user?.id) {
      console.log('사용자 인증 필요: 로그인 후 이용해주세요')
      setReviews([])
      setError('로그인이 필요합니다.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      // 백엔드 API 호출하여 모든 플랫폼의 리뷰 가져오기
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8002'
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

      // 데이터 구조 확인 및 처리
      const reviewsData = apiResult.data?.reviews || apiResult.reviews || []

      // 매장 정보와 연결하여 타입에 맞게 변환
      const reviewsWithStore = reviewsData.map((review: any) => {
        // 디버깅: 승인 관련 필드 확인
        console.log('Review data:', {
          id: review.id,
          requires_approval: review.requires_approval,
          scheduled_reply_date: review.scheduled_reply_date,
          schedulable_reply_date: review.schedulable_reply_date,
          reply_status: review.reply_status
        })
        
        return {
          ...review,
          platform_store: review.platform_stores, // 백엔드에서 온 매장 정보 사용
          // 필드명 통일
          rating: review.rating || 0,
          reviewer_name: review.reviewer_name || '익명',
          review_text: review.review_text || '',
          review_date: review.review_date || review.created_at,
          has_photos: review.has_photos || false,
          photo_count: review.photo_count || 0,
          // 테스트 데이터 추가 (실제 데이터가 없는 경우)
          requires_approval: review.requires_approval ?? (Math.random() > 0.5), // 50% 확률로 승인 필요
          schedulable_reply_date: review.schedulable_reply_date ?? (() => {
            // 테스트용 예약 시간 생성 (내일 또는 모레 00시)
            const tomorrow = new Date()
            tomorrow.setDate(tomorrow.getDate() + (Math.random() > 0.5 ? 1 : 2))
            tomorrow.setHours(0, 0, 0, 0)
            return tomorrow.toISOString()
          })()
        }
      })

      setReviews(reviewsWithStore)
      console.log(`리뷰 조회 완료: ${reviewsWithStore.length}개`)
      
    } catch (err) {
      console.error('Error fetching reviews:', err)
      setError('리뷰를 불러오는 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [user?.id, selectedStore])

  // 초기 데이터 로드 - 매장을 먼저 로드한 후 리뷰 로드
  useEffect(() => {
    fetchStores()
  }, [fetchStores])

  useEffect(() => {
    // 매장 데이터가 로드된 후에 리뷰 조회
    fetchReviews()
  }, [fetchReviews])

  // 필터링 로직
  useEffect(() => {
    let filtered = reviews

    // 답글 상태 필터
    if (filter !== 'all') {
      if (filter === 'draft') {
        // "미답변 리뷰"는 답글이 필요한 모든 상태를 포함
        filtered = filtered.filter(review => 
          review.reply_status === 'draft' || 
          !review.reply_status || 
          review.reply_status === 'approved'
        )
      } else if (filter === 'requires_approval') {
        // "확인 필요"는 사장님 확인이 필요하면서 답글이 완료되지 않은 리뷰
        filtered = filtered.filter(review => 
          review.requires_approval === true && review.reply_status !== 'sent'
        )
      } else {
        filtered = filtered.filter(review => review.reply_status === filter)
      }
    }

    // 감정 필터
    if (sentimentFilter !== 'all') {
      filtered = filtered.filter(review => review.sentiment === sentimentFilter)
    }

    // 플랫폼 필터
    if (platformFilter !== 'all') {
      filtered = filtered.filter(review => (review as any).platform === platformFilter)
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
  }, [reviews, filter, sentimentFilter, platformFilter, searchTerm])

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

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'naver': return 'bg-green-100 text-green-800'
      case 'baemin': return 'bg-cyan-100 text-cyan-800'
      case 'coupangeats': return 'bg-red-100 text-red-800'
      case 'yogiyo': return 'bg-orange-100 text-orange-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPlatformName = (platform: string) => {
    switch (platform) {
      case 'naver': return '네이버'
      case 'baemin': return '배민'
      case 'coupangeats': return '쿠팡잇츠'
      case 'yogiyo': return '요기요'
      default: return platform
    }
  }

  // 사장님 확인 필요 메시지 생성 함수
  const getApprovalMessage = (review: ReviewWithStore) => {
    if (!review.requires_approval || review.reply_status === 'sent') {
      return null
    }

    // schedulable_reply_date 또는 scheduled_reply_date 필드 확인
    const dateField = review.schedulable_reply_date || review.scheduled_reply_date
    const scheduledDate = dateField ? new Date(dateField) : null
    
    if (!scheduledDate || isNaN(scheduledDate.getTime())) {
      return "사장님 확인이 필요한 댓글입니다."
    }

    const now = new Date()
    const tomorrow = new Date(now)
    tomorrow.setDate(tomorrow.getDate() + 1)
    const dayAfterTomorrow = new Date(now)
    dayAfterTomorrow.setDate(dayAfterTomorrow.getDate() + 2)

    const month = String(scheduledDate.getMonth() + 1).padStart(2, '0')
    const day = String(scheduledDate.getDate()).padStart(2, '0')
    const hour = String(scheduledDate.getHours()).padStart(2, '0')

    // 같은 날인지 확인
    const isToday = scheduledDate.toDateString() === now.toDateString()
    const isTomorrow = scheduledDate.toDateString() === tomorrow.toDateString()
    const isDayAfterTomorrow = scheduledDate.toDateString() === dayAfterTomorrow.toDateString()

    let dateText = `${month}/${day}일`
    if (isToday) {
      dateText = "오늘"
    } else if (isTomorrow) {
      dateText = "내일"
    } else if (isDayAfterTomorrow) {
      dateText = "모레"
    }

    return `사장님 확인이 필요한 댓글입니다. ${dateText} ${hour}시 이후에 답글이 등록될 예정입니다.`
  }

  // 통계 계산 (필터 로직과 동일하게)
  const statistics = {
    total: reviews.length,
    // "미답변 리뷰"에는 draft, null, approved 상태 모두 포함
    draft: reviews.filter(r => 
      r.reply_status === 'draft' || 
      !r.reply_status || 
      r.reply_status === 'approved'
    ).length,
    sent: reviews.filter(r => r.reply_status === 'sent').length,
    pending: reviews.filter(r => r.reply_status === 'pending_approval').length,
    approved: reviews.filter(r => r.reply_status === 'approved').length,
    failed: reviews.filter(r => r.reply_status === 'failed').length,
    // 확인필요: requires_approval이 true이면서 답글이 완료되지 않은 리뷰
    requiresApproval: reviews.filter(r => 
      r.requires_approval === true && r.reply_status !== 'sent'
    ).length,
    // 네이버 제외하고 실제 평점이 있는 리뷰만으로 평균 계산
    averageRating: (() => {
      const reviewsWithRating = reviews.filter(r => r.rating && r.rating > 0);
      return reviewsWithRating.length > 0 
        ? (reviewsWithRating.reduce((acc, r) => acc + r.rating, 0) / reviewsWithRating.length).toFixed(1)
        : '0.0';
    })()
  }

  return (
    <AppLayout>
      <div className="space-y-8">
      {/* 페이지 헤더 */}
      <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">리뷰 관리</h1>
          <p className="text-gray-600 mt-1">
            모든 플랫폼의 리뷰를 관리하고 답글을 작성하세요. (네이버, 배민, 쿠팡잇츠, 요기요)
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
        }`} onClick={() => setFilter('draft')} title="아직 답글이 작성되지 않은 리뷰">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-orange-600" />
              <div>
                <p className="text-sm text-gray-600">미답변 리뷰</p>
                <p className="text-2xl font-bold text-orange-600">{statistics.draft}</p>
              </div>
            </div>
            <div className="mt-2">
              <Badge className="text-xs bg-orange-100 text-orange-700">📝 미답변</Badge>
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

        <Card className={`cursor-pointer hover:shadow-md transition-shadow ${
          filter === 'requires_approval' ? 'ring-2 ring-amber-500 bg-amber-50' : ''
        }`} onClick={() => setFilter('requires_approval')} title="사장님 확인이 필요하여 답글이 등록되지 않은 리뷰">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              <div>
                <p className="text-sm text-gray-600">확인 필요</p>
                <p className="text-2xl font-bold text-amber-600">{statistics.requiresApproval}</p>
              </div>
            </div>
            <div className="mt-2">
              <Badge className="text-xs bg-amber-100 text-amber-700">⚠️ 사장님 확인</Badge>
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
                  ({store.platform}) {store.store_name}
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
              {/* 플랫폼 필터 */}
              <select
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
              >
                {platformOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>

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
                          <Badge className={`text-xs ${getPlatformColor((review as any).platform)}`}>
                            {getPlatformName((review as any).platform)}
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

                  {/* 사장님 확인 필요 메시지 */}
                  {getApprovalMessage(review) && (
                    <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg p-4 shadow-sm">
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0 mt-0.5">
                          <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center">
                            <AlertTriangle className="w-4 h-4 text-amber-600" />
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <Badge className="bg-amber-100 text-amber-800 text-xs px-2 py-1">
                              🔔 승인 대기
                            </Badge>
                          </div>
                          <p className="text-sm font-medium text-amber-900 leading-relaxed">
                            {getApprovalMessage(review)}
                          </p>
                          <p className="text-xs text-amber-700 mt-2 leading-relaxed">
                            💡 AI가 자동으로 답글을 생성하여 예약된 시간에 전송됩니다. 
                            필요시 답글을 미리 확인하고 수정할 수 있습니다.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

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
               filter === 'draft' ? '미답변 리뷰가 없습니다' :
               filter === 'sent' ? '답글을 완료한 리뷰가 없습니다' :
               filter === 'requires_approval' ? '확인이 필요한 리뷰가 없습니다' :
               filter !== 'all' || sentimentFilter !== 'all' ? '필터 조건에 맞는 리뷰가 없습니다' :
               '리뷰가 없습니다'
              }
            </h3>
            <p className="text-gray-600">
              {searchTerm ? '다른 검색어를 시도해보세요.' :
               filter === 'draft' ? '모든 리뷰에 답글이 작성되었습니다! 🎉 답글 생성, 승인, 전송이 모두 완료되었어요.' :
               filter === 'sent' ? '답글을 완료한 리뷰들을 확인하세요.' :
               filter === 'requires_approval' ? '사장님 확인이 필요한 리뷰가 없습니다. 모든 리뷰가 자동으로 처리되고 있어요! ✨' :
               filter !== 'all' || sentimentFilter !== 'all' || platformFilter !== 'all' ? '다른 필터 조건을 시도해보세요.' :
               stores.length === 0 ? '먼저 매장을 등록해주세요.' :
               '리뷰가 수집되면 여기에 표시됩니다.'
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
              {filter === 'requires_approval' && reviews.length > 0 && (
                <Button variant="outline" onClick={() => setFilter('all')}>
                  모든 리뷰 보기
                </Button>
              )}
              {(searchTerm || (filter !== 'draft' && filter !== 'requires_approval') || sentimentFilter !== 'all' || platformFilter !== 'all') && (
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setSearchTerm('')
                    setFilter('draft')
                    setSentimentFilter('all')
                    setPlatformFilter('all')
                  }}
                >
                  미답변 리뷰 보기
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