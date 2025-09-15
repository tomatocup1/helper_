"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { Calculator, TrendingUp, Clock, DollarSign, Zap, Target } from 'lucide-react'

interface ROIData {
  monthlyReviews: number
  timePerReview: number
  hourlyWage: number
  responseRate: number
}

interface ROIResults {
  currentMonthlyHours: number
  currentMonthlyCost: number
  aiMonthlyHours: number
  aiMonthlyCost: number
  timeSaved: number
  costSaved: number
  yearlyTimeSaved: number
  yearlyCostSaved: number
  productivityIncrease: number
}

const defaultData: ROIData = {
  monthlyReviews: 50,
  timePerReview: 5,
  hourlyWage: 12000,
  responseRate: 30
}

export default function ROICalculator() {
  const [data, setData] = useState<ROIData>(defaultData)
  const [results, setResults] = useState<ROIResults | null>(null)

  const calculateROI = (inputData: ROIData): ROIResults => {
    const { monthlyReviews, timePerReview, hourlyWage, responseRate } = inputData
    
    // 현재 방식 계산
    const reviewsToAnswer = (monthlyReviews * responseRate) / 100
    const currentMonthlyHours = (reviewsToAnswer * timePerReview) / 60
    const currentMonthlyCost = currentMonthlyHours * hourlyWage
    
    // AI 방식 계산 (90% 시간 절약, 100% 답글률)
    const aiReviewsAnswered = monthlyReviews // 모든 리뷰에 답글
    const aiTimePerReview = 0.5 // 30초 (검토 + 클릭)
    const aiMonthlyHours = (aiReviewsAnswered * aiTimePerReview) / 60
    const aiMonthlyCost = aiMonthlyHours * hourlyWage + 29000 // 베이직 플랜
    
    // 절약 효과
    const timeSaved = Math.max(0, currentMonthlyHours - aiMonthlyHours)
    const costSaved = Math.max(0, currentMonthlyCost - aiMonthlyCost)
    const yearlyTimeSaved = timeSaved * 12
    const yearlyCostSaved = costSaved * 12
    
    // 생산성 증가율 (답글률 개선)
    const productivityIncrease = ((100 - responseRate) / responseRate) * 100

    return {
      currentMonthlyHours,
      currentMonthlyCost,
      aiMonthlyHours,
      aiMonthlyCost,
      timeSaved,
      costSaved,
      yearlyTimeSaved,
      yearlyCostSaved,
      productivityIncrease
    }
  }

  useEffect(() => {
    const newResults = calculateROI(data)
    setResults(newResults)
  }, [data])

  const updateData = (key: keyof ROIData, value: number) => {
    setData(prev => ({ ...prev, [key]: value }))
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR').format(Math.round(amount))
  }

  const formatTime = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)}분`
    }
    return `${hours.toFixed(1)}시간`
  }

  return (
    <div className="bg-gradient-to-br from-green-50 to-blue-50 py-16">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Calculator className="h-8 w-8 text-green-600" />
            <h2 className="text-3xl font-bold text-gray-900">
              투자 수익률 계산기
            </h2>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            현재 리뷰 관리에 소요되는 시간과 비용을 입력하여 AI 도입 시 절약 효과를 확인해보세요
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* 입력 섹션 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5" />
                현재 리뷰 관리 현황
              </CardTitle>
              <CardDescription>
                정확한 계산을 위해 현재 상황을 입력해주세요
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="monthlyReviews">월 평균 리뷰 수</Label>
                <Input
                  id="monthlyReviews"
                  type="number"
                  value={data.monthlyReviews}
                  onChange={(e) => updateData('monthlyReviews', parseInt(e.target.value) || 0)}
                  className="text-lg"
                />
                <p className="text-sm text-gray-500">모든 플랫폼 합계</p>
              </div>

              <div className="space-y-3">
                <Label>리뷰당 답글 작성 시간: {data.timePerReview}분</Label>
                <Slider
                  value={[data.timePerReview]}
                  onValueChange={(value) => updateData('timePerReview', value[0])}
                  max={20}
                  min={1}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1분</span>
                  <span>20분</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="hourlyWage">시간당 인건비 (원)</Label>
                <Input
                  id="hourlyWage"
                  type="number"
                  value={data.hourlyWage}
                  onChange={(e) => updateData('hourlyWage', parseInt(e.target.value) || 0)}
                  className="text-lg"
                />
                <p className="text-sm text-gray-500">사장님 또는 직원 시급</p>
              </div>

              <div className="space-y-3">
                <Label>현재 답글률: {data.responseRate}%</Label>
                <Slider
                  value={[data.responseRate]}
                  onValueChange={(value) => updateData('responseRate', value[0])}
                  max={100}
                  min={0}
                  step={5}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>0%</span>
                  <span>100%</span>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium mb-2">현재 상황 요약</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">답글 대상</span>
                    <p className="font-medium">{Math.round((data.monthlyReviews * data.responseRate) / 100)}개/월</p>
                  </div>
                  <div>
                    <span className="text-gray-600">소요 시간</span>
                    <p className="font-medium">{formatTime(results?.currentMonthlyHours || 0)}/월</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 결과 섹션 */}
          <div className="space-y-6">
            {/* 비교 카드 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  AI 도입 효과 비교
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-sm text-gray-600">구분</p>
                      <p className="font-medium">항목</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">현재</p>
                      <Badge variant="outline" className="text-red-600 border-red-200">
                        수동 관리
                      </Badge>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">AI 도입 후</p>
                      <Badge className="bg-blue-600">
                        자동화
                      </Badge>
                    </div>
                  </div>

                  <div className="space-y-3 border-t pt-4">
                    <div className="grid grid-cols-3 gap-4 text-center py-2 bg-gray-50 rounded">
                      <div className="font-medium">답글률</div>
                      <div className="text-red-600 font-semibold">{data.responseRate}%</div>
                      <div className="text-blue-600 font-semibold">100%</div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 text-center py-2">
                      <div className="font-medium">월 소요시간</div>
                      <div className="text-red-600 font-semibold">
                        {formatTime(results?.currentMonthlyHours || 0)}
                      </div>
                      <div className="text-blue-600 font-semibold">
                        {formatTime(results?.aiMonthlyHours || 0)}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 text-center py-2 bg-gray-50 rounded">
                      <div className="font-medium">월 비용</div>
                      <div className="text-red-600 font-semibold">
                        {formatCurrency(results?.currentMonthlyCost || 0)}원
                      </div>
                      <div className="text-blue-600 font-semibold">
                        {formatCurrency(results?.aiMonthlyCost || 0)}원
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 절약 효과 */}
            <div className="grid grid-cols-2 gap-4">
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="bg-green-100 p-2 rounded-lg">
                      <Clock className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">월 시간 절약</p>
                      <p className="text-2xl font-bold text-green-600">
                        {formatTime(results?.timeSaved || 0)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="bg-blue-100 p-2 rounded-lg">
                      <DollarSign className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">월 비용 절약</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {formatCurrency(results?.costSaved || 0)}원
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* 연간 효과 */}
            <Card className="bg-gradient-to-r from-green-500 to-blue-500 text-white">
              <CardContent className="p-6">
                <div className="text-center">
                  <Zap className="h-8 w-8 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold mb-4">연간 절약 효과</h3>
                  
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-sm opacity-90">시간 절약</p>
                      <p className="text-3xl font-bold">
                        {formatTime(results?.yearlyTimeSaved || 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm opacity-90">비용 절약</p>
                      <p className="text-3xl font-bold">
                        {formatCurrency(results?.yearlyCostSaved || 0)}원
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-white/20">
                    <p className="text-sm opacity-90">답글률 개선으로 인한 추가 효과</p>
                    <p className="text-xl font-semibold">
                      고객 응답률 +{Math.round(100 - data.responseRate)}%p 개선
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* CTA */}
            <Card>
              <CardContent className="p-6 text-center">
                <h3 className="text-lg font-semibold mb-2">
                  월 {formatCurrency(results?.costSaved || 0)}원 절약하기
                </h3>
                <p className="text-gray-600 mb-4">
                  30일 무료 체험으로 효과를 직접 확인해보세요
                </p>
                <div className="flex gap-3 justify-center">
                  <button className="px-6 py-3 bg-gradient-to-r from-green-600 to-blue-600 text-white rounded-lg font-semibold hover:from-green-700 hover:to-blue-700 transition-colors">
                    무료 체험 시작
                  </button>
                  <button className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors">
                    상담 문의
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}