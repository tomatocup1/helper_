"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { MessageSquare, Sparkles, Star, ThumbsUp, Clock, Zap } from 'lucide-react'

interface SampleReview {
  id: string
  platform: string
  rating: number
  content: string
  customer: string
  sentiment: 'positive' | 'negative' | 'neutral'
  platformColor: string
  platformIcon: string
}

const sampleReviews: SampleReview[] = [
  {
    id: '1',
    platform: '네이버',
    rating: 5,
    content: '음식도 맛있고 서비스도 정말 좋았어요! 다음에도 또 올게요.',
    customer: '김*수',
    sentiment: 'positive',
    platformColor: 'bg-green-500',
    platformIcon: '🗺️'
  },
  {
    id: '2',
    platform: '배달의민족',
    rating: 2,
    content: '배달이 너무 늦게 와서 음식이 식어버렸네요. 개선 부탁드려요.',
    customer: '이*영',
    sentiment: 'negative',
    platformColor: 'bg-blue-500',
    platformIcon: '🛵'
  },
  {
    id: '3',
    platform: '쿠팡이츠',
    rating: 4,
    content: '맛은 좋은데 포장이 아쉬워요. 그래도 재주문 의향 있습니다.',
    customer: '박*민',
    sentiment: 'neutral',
    platformColor: 'bg-orange-500',
    platformIcon: '📦'
  }
]

const aiReplies = {
  '1': {
    reply: "안녕하세요! 저희 매장을 이용해주셔서 정말 감사합니다 😊 맛있게 드셨다니 너무 기뻐요! 항상 고객분들께 최고의 서비스를 제공하기 위해 노력하겠습니다. 다음에 또 뵙기를 기대하며, 언제든지 방문해주세요. 감사합니다!",
    tone: "친근하고 감사함을 표현",
    sentiment: "긍정적 답변"
  },
  '2': {
    reply: "안녕하세요, 이번 배달 서비스로 불편을 드려 정말 죄송합니다. 배달 시간 지연으로 음식 품질에 영향을 드린 점 깊이 반성하고 있습니다. 배달 파트너와 긴급 회의를 통해 개선책을 마련하겠으며, 다음 주문 시에는 더욱 신속하고 따뜻한 음식으로 보답드리겠습니다. 소중한 의견 감사드립니다.",
    tone: "사과하고 개선 의지 표명",
    sentiment: "문제 해결 중심"
  },
  '3': {
    reply: "안녕하세요! 맛에 대한 좋은 평가 감사드립니다 🙏 포장 관련 아쉬운 점 말씀해주셔서 감사해요. 더 나은 포장재와 방법을 검토해서 다음에는 더 만족스러운 경험을 드릴게요! 재주문 의향까지 남겨주셔서 정말 고맙습니다. 기대에 부응하도록 최선을 다하겠습니다!",
    tone: "개선 의지와 감사 표현",
    sentiment: "건설적 대응"
  }
}

export default function InteractiveDemo() {
  const [selectedReview, setSelectedReview] = useState<SampleReview | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [showReply, setShowReply] = useState(false)
  const [typingText, setTypingText] = useState('')

  const handleGenerateReply = (review: SampleReview) => {
    setSelectedReview(review)
    setIsGenerating(true)
    setShowReply(false)
    setTypingText('')

    // 실제 자동 생성 과정 시뮬레이션
    setTimeout(() => {
      setIsGenerating(false)
      setShowReply(true)
      
      // 타이핑 효과
      const reply = aiReplies[review.id as keyof typeof aiReplies].reply
      let i = 0
      const typing = setInterval(() => {
        if (i < reply.length) {
          setTypingText(reply.slice(0, i + 1))
          i++
        } else {
          clearInterval(typing)
        }
      }, 30)
    }, 2500)
  }

  return (
    <div className="bg-gradient-to-br from-blue-50 to-purple-50 py-16">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Sparkles className="h-8 w-8 text-blue-600" />
            <h2 className="text-3xl font-bold text-gray-900">
              자동 답글 생성 실시간 체험
            </h2>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            실제 리뷰를 클릭하여 시스템이 어떻게 상황에 맞는 답글을 생성하는지 확인해보세요
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* 리뷰 선택 영역 */}
          <div>
            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              실제 고객 리뷰 예시
            </h3>
            <div className="space-y-4">
              {sampleReviews.map((review) => (
                <Card 
                  key={review.id}
                  className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                    selectedReview?.id === review.id ? 'ring-2 ring-blue-500' : ''
                  }`}
                  onClick={() => handleGenerateReply(review)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{review.platformIcon}</span>
                        <div>
                          <Badge variant="outline" className={`${review.platformColor} text-white border-0`}>
                            {review.platform}
                          </Badge>
                          <div className="flex items-center gap-1 mt-1">
                            {Array.from({ length: 5 }).map((_, i) => (
                              <Star
                                key={i}
                                className={`h-4 w-4 ${
                                  i < review.rating 
                                    ? 'fill-yellow-400 text-yellow-400' 
                                    : 'text-gray-300'
                                }`}
                              />
                            ))}
                          </div>
                        </div>
                      </div>
                      <span className="text-sm text-gray-500">{review.customer}</span>
                    </div>
                    <p className="text-gray-700 leading-relaxed">
                      "{review.content}"
                    </p>
                    <div className="mt-3 flex items-center justify-between">
                      <Badge 
                        variant={review.sentiment === 'positive' ? 'default' : review.sentiment === 'negative' ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {review.sentiment === 'positive' ? '긍정' : review.sentiment === 'negative' ? '부정' : '중립'}
                      </Badge>
                      <Button size="sm" variant="outline" className="flex items-center gap-1">
                        <Zap className="h-4 w-4" />
                        자동 답글 생성
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* 자동 답글 생성 결과 */}
          <div>
            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              자동 생성 답글
            </h3>
            
            {!selectedReview ? (
              <Card className="h-80 flex items-center justify-center">
                <CardContent className="text-center">
                  <MessageSquare className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">리뷰를 선택하면 자동으로 답글이 생성됩니다</p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      {selectedReview.platformIcon} {selectedReview.platform} 리뷰 답글
                    </CardTitle>
                    {isGenerating && (
                      <div className="flex items-center gap-2 text-blue-600">
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent" />
                        <span className="text-sm">자동 생성 중...</span>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {isGenerating ? (
                    <div className="space-y-4">
                      <div className="bg-gray-100 rounded-lg p-4">
                        <div className="space-y-2">
                          <div className="h-4 bg-gray-200 rounded animate-pulse" />
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2" />
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Clock className="h-4 w-4" />
                        감정 분석 → 톤앤매너 설정 → 자동 답글 생성
                      </div>
                    </div>
                  ) : showReply ? (
                    <div className="space-y-4">
                      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border-l-4 border-blue-500">
                        <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                          {typingText}
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="bg-gray-50 rounded-lg p-3">
                          <span className="font-medium text-gray-700">답글 톤</span>
                          <p className="text-gray-600 mt-1">
                            {aiReplies[selectedReview.id as keyof typeof aiReplies].tone}
                          </p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <span className="font-medium text-gray-700">대응 전략</span>
                          <p className="text-gray-600 mt-1">
                            {aiReplies[selectedReview.id as keyof typeof aiReplies].sentiment}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-4 border-t">
                        <div className="flex items-center gap-2 text-green-600">
                          <ThumbsUp className="h-4 w-4" />
                          <span className="text-sm font-medium">자동 생성 완료</span>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline">
                            수정하기
                          </Button>
                          <Button size="sm">
                            바로 등록
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        <div className="text-center mt-12">
          <div className="bg-white rounded-xl p-6 shadow-lg max-w-2xl mx-auto">
            <div className="flex items-center justify-center gap-4 text-sm text-gray-600 mb-4">
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                <span>평균 생성시간: 3초</span>
              </div>
              <div className="flex items-center gap-1">
                <Sparkles className="h-4 w-4" />
                <span>정확도: 95%+</span>
              </div>
              <div className="flex items-center gap-1">
                <MessageSquare className="h-4 w-4" />
                <span>월 처리량: 1,000+</span>
              </div>
            </div>
            <Button size="lg" className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
              무료로 시작하기
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}