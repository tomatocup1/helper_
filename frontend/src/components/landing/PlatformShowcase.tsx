"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  CheckCircle, 
  Clock, 
  TrendingUp, 
  Zap, 
  Globe,
  Smartphone,
  Star,
  MessageSquare,
  BarChart3,
  Shield,
  ArrowRight
} from 'lucide-react'

interface Platform {
  id: string
  name: string
  displayName: string
  icon: string
  color: string
  bgColor: string
  borderColor: string
  status: 'active' | 'coming-soon'
  description: string
  features: string[]
  stats: {
    stores: number
    reviews: number
    responseRate: number
  }
}

const platforms: Platform[] = [
  {
    id: 'naver',
    name: 'naver',
    displayName: '네이버 플레이스',
    icon: '🗺️',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    status: 'active',
    description: '국내 최대 지도 서비스로 높은 고객 접촉률을 자랑합니다',
    features: ['실시간 리뷰 모니터링', 'AI 답글 자동 생성', '통계 분석'],
    stats: {
      stores: 847,
      reviews: 34521,
      responseRate: 94.2
    }
  },
  {
    id: 'baemin',
    name: 'baemin',
    displayName: '배달의민족',
    icon: '🛵',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    status: 'active',
    description: '배달 시장 점유율 1위, 고객 리뷰가 매출에 직접 영향',
    features: ['24시간 자동 크롤링', 'AI 답글 등록', '평점 분석'],
    stats: {
      stores: 623,
      reviews: 28934,
      responseRate: 91.8
    }
  },
  {
    id: 'coupangeats',
    name: 'coupangeats',
    displayName: '쿠팡이츠',
    icon: '📦',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    status: 'active',
    description: '빠른 배달로 인기 상승 중인 플랫폼, 신규 고객 유입 효과',
    features: ['리뷰 자동 수집', '맞춤형 답글 생성', '트렌드 분석'],
    stats: {
      stores: 412,
      reviews: 15678,
      responseRate: 89.5
    }
  },
  {
    id: 'yogiyo',
    name: 'yogiyo',
    displayName: '요기요',
    icon: '🍔',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    status: 'active',
    description: '오랜 역사를 가진 배달 플랫폼, 충성 고객층이 두터움',
    features: ['리뷰 모니터링', 'AI 답글 시스템', '고객 분석'],
    stats: {
      stores: 356,
      reviews: 12845,
      responseRate: 87.3
    }
  },
  {
    id: 'google',
    name: 'google',
    displayName: '구글 마이 비즈니스',
    icon: '🌐',
    color: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    status: 'coming-soon',
    description: '글로벌 검색 노출로 해외 고객까지 접근 가능',
    features: ['글로벌 리뷰 관리', '다국어 답글 지원', 'SEO 최적화'],
    stats: {
      stores: 0,
      reviews: 0,
      responseRate: 0
    }
  }
]

const totalStats = {
  stores: platforms.filter(p => p.status === 'active').reduce((sum, p) => sum + p.stats.stores, 0),
  reviews: platforms.filter(p => p.status === 'active').reduce((sum, p) => sum + p.stats.reviews, 0),
  avgResponseRate: platforms.filter(p => p.status === 'active').reduce((sum, p, _, arr) => sum + p.stats.responseRate / arr.length, 0)
}

export default function PlatformShowcase() {
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>(platforms[0])
  const [animatedStats, setAnimatedStats] = useState({
    stores: 0,
    reviews: 0,
    responseRate: 0
  })

  useEffect(() => {
    const duration = 2000
    const steps = 60
    const stepDuration = duration / steps

    let currentStep = 0
    const timer = setInterval(() => {
      currentStep++
      const progress = Math.min(1, currentStep / steps)
      
      setAnimatedStats({
        stores: Math.round(totalStats.stores * progress),
        reviews: Math.round(totalStats.reviews * progress),
        responseRate: totalStats.avgResponseRate * progress
      })

      if (currentStep >= steps) {
        clearInterval(timer)
      }
    }, stepDuration)

    return () => clearInterval(timer)
  }, [])

  return (
    <div className="bg-gradient-to-br from-gray-50 to-blue-50 py-16">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Globe className="h-8 w-8 text-blue-600" />
            <h2 className="text-3xl font-bold text-gray-900">
              멀티플랫폼 통합 관리
            </h2>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            4개 주요 플랫폼을 하나의 시스템으로 통합 관리하여 효율성을 극대화하세요
          </p>
        </div>

        {/* 전체 통계 */}
        <div className="grid md:grid-cols-3 gap-6 max-w-3xl mx-auto mb-12">
          <Card>
            <CardContent className="p-6 text-center">
              <div className="bg-blue-100 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <Smartphone className="h-6 w-6 text-blue-600" />
              </div>
              <div className="text-3xl font-bold text-blue-600 mb-1">
                {animatedStats.stores.toLocaleString()}
              </div>
              <p className="text-gray-600">연동 매장</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6 text-center">
              <div className="bg-green-100 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <MessageSquare className="h-6 w-6 text-green-600" />
              </div>
              <div className="text-3xl font-bold text-green-600 mb-1">
                {animatedStats.reviews.toLocaleString()}
              </div>
              <p className="text-gray-600">처리된 리뷰</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6 text-center">
              <div className="bg-yellow-100 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <TrendingUp className="h-6 w-6 text-yellow-600" />
              </div>
              <div className="text-3xl font-bold text-yellow-600 mb-1">
                {animatedStats.responseRate.toFixed(1)}%
              </div>
              <p className="text-gray-600">평균 답글률</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* 플랫폼 선택 */}
          <div>
            <h3 className="text-xl font-semibold mb-4">지원 플랫폼</h3>
            <div className="space-y-3">
              {platforms.map((platform) => (
                <Card 
                  key={platform.id}
                  className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                    selectedPlatform.id === platform.id ? 'ring-2 ring-blue-500' : ''
                  } ${platform.status === 'coming-soon' ? 'opacity-75' : ''}`}
                  onClick={() => setSelectedPlatform(platform)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{platform.icon}</span>
                        <div>
                          <h4 className="font-semibold text-gray-900">
                            {platform.displayName}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            {platform.status === 'active' ? (
                              <>
                                <CheckCircle className="h-4 w-4 text-green-500" />
                                <span className="text-sm text-green-600 font-medium">
                                  서비스 중
                                </span>
                              </>
                            ) : (
                              <>
                                <Clock className="h-4 w-4 text-orange-500" />
                                <span className="text-sm text-orange-600 font-medium">
                                  준비 중
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      {platform.status === 'active' && (
                        <div className="text-right text-sm">
                          <p className="font-semibold text-gray-900">
                            {platform.stats.stores.toLocaleString()}개 매장
                          </p>
                          <p className="text-gray-600">
                            답글률 {platform.stats.responseRate}%
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* 선택된 플랫폼 상세 */}
          <div className="lg:col-span-2">
            <Card className={`${selectedPlatform.bgColor} ${selectedPlatform.borderColor} border-2`}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{selectedPlatform.icon}</span>
                  <div>
                    <CardTitle className={`${selectedPlatform.color} text-2xl`}>
                      {selectedPlatform.displayName}
                    </CardTitle>
                    <CardDescription className="text-gray-600 mt-2">
                      {selectedPlatform.description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {selectedPlatform.status === 'active' ? (
                  <div className="space-y-6">
                    {/* 플랫폼 통계 */}
                    <div className="grid grid-cols-3 gap-4 bg-white/50 rounded-lg p-4">
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${selectedPlatform.color} mb-1`}>
                          {selectedPlatform.stats.stores.toLocaleString()}
                        </div>
                        <p className="text-sm text-gray-600">연동 매장</p>
                      </div>
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${selectedPlatform.color} mb-1`}>
                          {selectedPlatform.stats.reviews.toLocaleString()}
                        </div>
                        <p className="text-sm text-gray-600">처리 리뷰</p>
                      </div>
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${selectedPlatform.color} mb-1`}>
                          {selectedPlatform.stats.responseRate}%
                        </div>
                        <p className="text-sm text-gray-600">답글률</p>
                      </div>
                    </div>

                    {/* 지원 기능 */}
                    <div>
                      <h4 className="font-semibold mb-3 flex items-center gap-2">
                        <Zap className={`h-5 w-5 ${selectedPlatform.color}`} />
                        주요 기능
                      </h4>
                      <div className="grid gap-2">
                        {selectedPlatform.features.map((feature, index) => (
                          <div key={index} className="flex items-center gap-2 bg-white/50 rounded-lg p-3">
                            <CheckCircle className={`h-4 w-4 ${selectedPlatform.color}`} />
                            <span className="text-gray-700">{feature}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 실시간 상태 */}
                    <div className="bg-white/50 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 bg-green-500 rounded-full animate-pulse`}></div>
                          <span className="font-medium text-gray-700">실시간 모니터링 중</span>
                        </div>
                        <Badge variant="outline" className="bg-white">
                          마지막 업데이트: 2분 전
                        </Badge>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Clock className={`h-16 w-16 ${selectedPlatform.color} mx-auto mb-4 opacity-50`} />
                    <h4 className="text-lg font-semibold mb-2">서비스 준비 중</h4>
                    <p className="text-gray-600 mb-4">
                      곧 출시 예정입니다. 베타 테스트 신청을 받고 있어요!
                    </p>
                    <Button variant="outline" className="flex items-center gap-2">
                      베타 테스트 신청
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* 통합 관리의 장점 */}
        <div className="mt-16">
          <h3 className="text-2xl font-bold text-center mb-8">통합 관리의 장점</h3>
          
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <Card>
              <CardContent className="p-6 text-center">
                <div className="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <BarChart3 className="h-8 w-8 text-blue-600" />
                </div>
                <h4 className="font-semibold mb-2">통합 대시보드</h4>
                <p className="text-gray-600">
                  모든 플랫폼의 리뷰와 통계를 한눈에 확인하고 비교 분석할 수 있습니다
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6 text-center">
                <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <Shield className="h-8 w-8 text-green-600" />
                </div>
                <h4 className="font-semibold mb-2">일관된 브랜드 톤</h4>
                <p className="text-gray-600">
                  모든 플랫폼에서 동일한 브랜드 톤과 메시지로 고객과 소통할 수 있습니다
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6 text-center">
                <div className="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <Star className="h-8 w-8 text-purple-600" />
                </div>
                <h4 className="font-semibold mb-2">효율성 극대화</h4>
                <p className="text-gray-600">
                  하나의 시스템으로 여러 플랫폼을 관리하여 시간과 비용을 크게 절약합니다
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* CTA */}
        <div className="text-center mt-12">
          <div className="bg-white rounded-xl p-8 shadow-lg max-w-2xl mx-auto">
            <h3 className="text-2xl font-bold mb-4">
              지금 바로 멀티플랫폼 관리를 시작하세요
            </h3>
            <p className="text-gray-600 mb-6">
              4개 플랫폼 동시 연동으로 리뷰 관리 효율성을 300% 높여보세요
            </p>
            <div className="flex gap-4 justify-center">
              <Button size="lg" className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
                30일 무료 체험
              </Button>
              <Button size="lg" variant="outline">
                플랫폼별 상세 기능 보기
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}