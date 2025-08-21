"use client"

import { useState } from 'react'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Label } from '@/components/ui/label'
import { 
  CreditCard,
  CheckCircle,
  Clock,
  Download,
  Eye,
  Star,
  Zap,
  Crown,
  Rocket,
  Calendar,
  Receipt,
  AlertCircle
} from 'lucide-react'

interface Plan {
  id: string
  name: string
  price: number
  period: 'month' | 'year'
  features: string[]
  limits: {
    stores: number
    reviews: number
    automation: boolean
    analytics: boolean
    priority_support: boolean
  }
  popular?: boolean
  current?: boolean
}

interface PaymentHistory {
  id: string
  date: string
  amount: number
  plan: string
  status: 'completed' | 'pending' | 'failed'
  invoice_url?: string
}

const plans: Plan[] = [
  {
    id: 'free',
    name: '무료 플랜',
    price: 0,
    period: 'month',
    features: [
      '매장 1개 등록',
      '월 10개 리뷰 분석',
      '기본 답글 템플릿',
      '주간 리포트'
    ],
    limits: {
      stores: 1,
      reviews: 10,
      automation: false,
      analytics: false,
      priority_support: false
    },
    current: true
  },
  {
    id: 'basic',
    name: '베이직',
    price: 29000,
    period: 'month',
    features: [
      '매장 3개 등록',
      '월 100개 리뷰 분석',
      'AI 답글 자동화',
      '상세 분석 리포트',
      '이메일 지원'
    ],
    limits: {
      stores: 3,
      reviews: 100,
      automation: true,
      analytics: true,
      priority_support: false
    },
    popular: true
  },
  {
    id: 'professional',
    name: '프로페셔널',
    price: 59000,
    period: 'month',
    features: [
      '매장 10개 등록',
      '월 500개 리뷰 분석',
      'AI 답글 자동화',
      '고급 분석 & 인사이트',
      '우선 지원',
      '맞춤 템플릿'
    ],
    limits: {
      stores: 10,
      reviews: 500,
      automation: true,
      analytics: true,
      priority_support: true
    }
  },
  {
    id: 'enterprise',
    name: '엔터프라이즈',
    price: 99000,
    period: 'month',
    features: [
      '무제한 매장',
      '무제한 리뷰 분석',
      'AI 답글 자동화',
      '실시간 대시보드',
      '전담 계정 매니저',
      'API 연동',
      '맞춤 개발'
    ],
    limits: {
      stores: 999,
      reviews: 99999,
      automation: true,
      analytics: true,
      priority_support: true
    }
  }
]

const mockPaymentHistory: PaymentHistory[] = [
  {
    id: '1',
    date: '2024-01-15',
    amount: 29000,
    plan: '베이직 플랜',
    status: 'completed',
    invoice_url: '#'
  },
  {
    id: '2',
    date: '2023-12-15',
    amount: 29000,
    plan: '베이직 플랜',
    status: 'completed',
    invoice_url: '#'
  },
  {
    id: '3',
    date: '2023-11-15',
    amount: 29000,
    plan: '베이직 플랜',
    status: 'completed',
    invoice_url: '#'
  }
]

export default function BillingPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState<string | null>(null)
  const [paymentHistory] = useState<PaymentHistory[]>(mockPaymentHistory)

  const currentPlan = plans.find(plan => plan.current) || plans[0]

  const handleUpgrade = async (planId: string) => {
    setLoading(planId)
    try {
      // 토스 페이먼츠 연동 로직
      console.log('Upgrading to plan:', planId)
      
      // 실제로는 토스 페이먼츠 SDK를 사용
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // 결제 성공 후 처리
      alert('결제가 완료되었습니다!')
    } catch (error) {
      console.error('결제 실패:', error)
      alert('결제에 실패했습니다. 다시 시도해주세요.')
    } finally {
      setLoading(null)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed': return '완료'
      case 'pending': return '대기중'
      case 'failed': return '실패'
      default: return '알 수 없음'
    }
  }

  const getPlanIcon = (planId: string) => {
    switch (planId) {
      case 'free': return <Star className="w-5 h-5" />
      case 'basic': return <Zap className="w-5 h-5" />
      case 'professional': return <Crown className="w-5 h-5" />
      case 'enterprise': return <Rocket className="w-5 h-5" />
      default: return <Star className="w-5 h-5" />
    }
  }

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* 헤더 */}
        <div>
          <h1 className="text-3xl font-bold brand-text">결제 관리</h1>
          <p className="text-muted-foreground">
            구독 플랜을 관리하고 결제 내역을 확인하세요
          </p>
        </div>

        <Tabs defaultValue="plans" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="plans">구독 플랜</TabsTrigger>
            <TabsTrigger value="current">현재 구독</TabsTrigger>
            <TabsTrigger value="history">결제 내역</TabsTrigger>
          </TabsList>

          {/* 구독 플랜 */}
          <TabsContent value="plans" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {plans.map((plan) => (
                <Card 
                  key={plan.id} 
                  className={`relative ${
                    plan.popular ? 'ring-2 ring-brand-500 shadow-lg' : ''
                  } ${plan.current ? 'bg-blue-50 border-blue-200' : ''}`}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <Badge className="bg-brand-600 text-white">가장 인기</Badge>
                    </div>
                  )}
                  {plan.current && (
                    <div className="absolute top-4 right-4">
                      <Badge className="bg-blue-600 text-white">현재 플랜</Badge>
                    </div>
                  )}
                  
                  <CardHeader className="text-center">
                    <div className="flex justify-center mb-2">
                      {getPlanIcon(plan.id)}
                    </div>
                    <CardTitle className="text-lg">{plan.name}</CardTitle>
                    <div className="space-y-1">
                      <div className="text-3xl font-bold">
                        {plan.price === 0 ? '무료' : `₩${plan.price.toLocaleString()}`}
                      </div>
                      {plan.price > 0 && (
                        <div className="text-sm text-muted-foreground">
                          / {plan.period === 'month' ? '월' : '년'}
                        </div>
                      )}
                    </div>
                  </CardHeader>
                  
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      {plan.features.map((feature, index) => (
                        <div key={index} className="flex items-center">
                          <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                          <span className="text-sm">{feature}</span>
                        </div>
                      ))}
                    </div>
                    
                    <div className="pt-4">
                      {plan.current ? (
                        <Button disabled className="w-full">
                          현재 이용중
                        </Button>
                      ) : (
                        <Button
                          variant={plan.popular ? "default" : "outline"}
                          className="w-full"
                          onClick={() => handleUpgrade(plan.id)}
                          disabled={loading === plan.id}
                        >
                          {loading === plan.id ? (
                            <div className="flex items-center">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                              결제 중...
                            </div>
                          ) : plan.price === 0 ? (
                            '무료로 시작'
                          ) : (
                            '업그레이드'
                          )}
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>플랜 비교</CardTitle>
                <CardDescription>
                  각 플랜의 세부 기능을 비교해보세요
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3">기능</th>
                        <th className="text-center p-3">무료</th>
                        <th className="text-center p-3">베이직</th>
                        <th className="text-center p-3">프로</th>
                        <th className="text-center p-3">엔터프라이즈</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b">
                        <td className="p-3">매장 등록</td>
                        <td className="text-center p-3">1개</td>
                        <td className="text-center p-3">3개</td>
                        <td className="text-center p-3">10개</td>
                        <td className="text-center p-3">무제한</td>
                      </tr>
                      <tr className="border-b">
                        <td className="p-3">월 리뷰 분석</td>
                        <td className="text-center p-3">10개</td>
                        <td className="text-center p-3">100개</td>
                        <td className="text-center p-3">500개</td>
                        <td className="text-center p-3">무제한</td>
                      </tr>
                      <tr className="border-b">
                        <td className="p-3">AI 답글 자동화</td>
                        <td className="text-center p-3">❌</td>
                        <td className="text-center p-3">✅</td>
                        <td className="text-center p-3">✅</td>
                        <td className="text-center p-3">✅</td>
                      </tr>
                      <tr className="border-b">
                        <td className="p-3">고급 분석</td>
                        <td className="text-center p-3">❌</td>
                        <td className="text-center p-3">✅</td>
                        <td className="text-center p-3">✅</td>
                        <td className="text-center p-3">✅</td>
                      </tr>
                      <tr>
                        <td className="p-3">우선 지원</td>
                        <td className="text-center p-3">❌</td>
                        <td className="text-center p-3">❌</td>
                        <td className="text-center p-3">✅</td>
                        <td className="text-center p-3">✅</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 현재 구독 */}
          <TabsContent value="current" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center">
                      {getPlanIcon(currentPlan.id)}
                      <span className="ml-2">{currentPlan.name}</span>
                      <Badge className="ml-2 bg-green-100 text-green-800">활성</Badge>
                    </CardTitle>
                    <CardDescription>
                      현재 이용중인 구독 플랜입니다
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-sm font-medium text-muted-foreground">월 요금</Label>
                        <p className="text-2xl font-bold">
                          {currentPlan.price === 0 ? '무료' : `₩${currentPlan.price.toLocaleString()}`}
                        </p>
                      </div>
                      <div>
                        <Label className="text-sm font-medium text-muted-foreground">다음 결제일</Label>
                        <p className="text-lg font-medium">2024-02-15</p>
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">매장 등록</span>
                        <span className="text-sm font-medium">1 / {currentPlan.limits.stores}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-brand-600 h-2 rounded-full" 
                          style={{ width: `${(1 / currentPlan.limits.stores) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">이번 달 리뷰 분석</span>
                        <span className="text-sm font-medium">23 / {currentPlan.limits.reviews}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ width: `${(23 / currentPlan.limits.reviews) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex space-x-2 pt-4">
                      <Button variant="outline" className="flex-1">
                        플랜 변경
                      </Button>
                      <Button variant="outline" className="flex-1">
                        구독 취소
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">다음 결제</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center">
                        <Calendar className="w-4 h-4 mr-2 text-muted-foreground" />
                        <span className="text-sm">2024년 2월 15일</span>
                      </div>
                      <div className="flex items-center">
                        <CreditCard className="w-4 h-4 mr-2 text-muted-foreground" />
                        <span className="text-sm">**** **** **** 1234</span>
                      </div>
                      <div className="text-lg font-bold">
                        ₩{currentPlan.price.toLocaleString()}
                      </div>
                      <Button variant="outline" className="w-full" size="sm">
                        결제 수단 변경
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">이용 현황</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm">AI 답글 생성</span>
                        <Badge variant="secondary">45개</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">리뷰 분석</span>
                        <Badge variant="secondary">23개</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">리포트 생성</span>
                        <Badge variant="secondary">4개</Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* 결제 내역 */}
          <TabsContent value="history" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">결제 내역</h3>
                <p className="text-sm text-muted-foreground">
                  지난 결제 내역을 확인하고 영수증을 다운로드하세요
                </p>
              </div>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-2" />
                전체 내역 다운로드
              </Button>
            </div>

            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b">
                      <tr>
                        <th className="text-left p-4">결제일</th>
                        <th className="text-left p-4">플랜</th>
                        <th className="text-left p-4">금액</th>
                        <th className="text-left p-4">상태</th>
                        <th className="text-right p-4">영수증</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paymentHistory.map((payment) => (
                        <tr key={payment.id} className="border-b">
                          <td className="p-4">
                            <div className="flex items-center">
                              <Receipt className="w-4 h-4 mr-2 text-muted-foreground" />
                              {new Date(payment.date).toLocaleDateString('ko-KR')}
                            </div>
                          </td>
                          <td className="p-4">
                            <span className="font-medium">{payment.plan}</span>
                          </td>
                          <td className="p-4">
                            <span className="font-medium">
                              ₩{payment.amount.toLocaleString()}
                            </span>
                          </td>
                          <td className="p-4">
                            <Badge className={getStatusColor(payment.status)}>
                              {getStatusLabel(payment.status)}
                            </Badge>
                          </td>
                          <td className="p-4 text-right">
                            {payment.invoice_url && (
                              <Button variant="ghost" size="sm">
                                <Eye className="w-4 h-4 mr-1" />
                                보기
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <AlertCircle className="w-5 h-5 mr-2" />
                  결제 정보
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="font-medium text-blue-800 mb-2">안전한 결제</h4>
                  <p className="text-sm text-blue-600">
                    모든 결제는 토스페이먼츠를 통해 안전하게 처리됩니다. 
                    카드 정보는 저장되지 않으며, PCI DSS 인증을 받은 시스템에서 처리됩니다.
                  </p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <strong>결제 방식:</strong> 신용카드, 계좌이체, 가상계좌
                  </div>
                  <div>
                    <strong>자동 결제:</strong> 매월 같은 날짜에 자동 결제
                  </div>
                  <div>
                    <strong>환불 정책:</strong> 이용하지 않은 기간에 대해 일할 계산 환불
                  </div>
                  <div>
                    <strong>세금계산서:</strong> 사업자 등록 고객에게 발행 가능
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  )
}