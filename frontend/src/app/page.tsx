"use client"

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Store, MessageSquare, BarChart3, Settings, ArrowRight } from 'lucide-react'

export default function HomePage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    // 로그인한 사용자는 대시보드로 리다이렉트
    if (user && !loading) {
      router.push('/dashboard')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
          <p className="text-muted-foreground">로딩 중...</p>
        </div>
      </div>
    )
  }

  // 로그인하지 않은 사용자를 위한 랜딩 페이지
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
        <div className="container mx-auto px-4 py-16">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-brand-600 to-brand-700 bg-clip-text text-transparent">
              우리가게 도우미
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              AI 기반 리뷰 관리로 소상공인의 성공을 돕습니다
            </p>
            <div className="flex gap-4 justify-center">
              <Link href="/login">
                <Button size="lg" className="font-semibold">
                  로그인
                </Button>
              </Link>
              <Link href="/register">
                <Button size="lg" variant="outline" className="font-semibold">
                  무료로 시작하기
                </Button>
              </Link>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <Card>
              <CardHeader>
                <Store className="h-10 w-10 text-brand-600 mb-2" />
                <CardTitle>매장 관리</CardTitle>
                <CardDescription>
                  여러 매장을 한 곳에서 편리하게 관리하세요
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• 매장별 리뷰 통합 관리</li>
                  <li>• 실시간 알림 설정</li>
                  <li>• 매장 정보 업데이트</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <MessageSquare className="h-10 w-10 text-brand-600 mb-2" />
                <CardTitle>AI 리뷰 답변</CardTitle>
                <CardDescription>
                  AI가 작성한 맞춤형 답변으로 시간을 절약하세요
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• 감정 분석 기반 답변</li>
                  <li>• 브랜드 톤 맞춤 설정</li>
                  <li>• 원클릭 답변 작성</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <BarChart3 className="h-10 w-10 text-brand-600 mb-2" />
                <CardTitle>분석 & 인사이트</CardTitle>
                <CardDescription>
                  리뷰 데이터를 분석하여 비즈니스 인사이트를 얻으세요
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• 리뷰 트렌드 분석</li>
                  <li>• 고객 만족도 추적</li>
                  <li>• 개선점 도출</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  // 로그인한 사용자는 대시보드로 리다이렉트되므로 여기까지 오지 않음
  return null
}