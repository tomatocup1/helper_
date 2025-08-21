"use client"

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/store/auth-store-supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Eye, EyeOff, Loader2, Store } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const { login, isAuthenticated, isLoading, error, clearError } = useAuth()
  
  const [showPassword, setShowPassword] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [formErrors, setFormErrors] = useState<{email?: string; password?: string}>({})

  // 이미 로그인된 경우 대시보드로 리디렉션
  useEffect(() => {
    console.log('Login page - auth state:', { isAuthenticated, isLoading })
    if (isAuthenticated) {
      console.log('Already authenticated, redirecting to dashboard')
      router.push('/dashboard')
    }
  }, [isAuthenticated, isLoading, router])

  // 에러 상태 초기화
  useEffect(() => {
    clearError()
  }, [])

  const validateForm = (): boolean => {
    const errors: {email?: string; password?: string} = {}

    if (!email) {
      errors.email = '이메일을 입력해주세요.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = '올바른 이메일 형식을 입력해주세요.'
    }

    if (!password) {
      errors.password = '비밀번호를 입력해주세요.'
    } else if (password.length < 6) {
      errors.password = '비밀번호는 최소 6자 이상이어야 합니다.'
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    console.log('Starting login process...')
    const success = await login(email, password)
    if (success) {
      console.log('Login successful, redirecting to dashboard...')
      router.push('/dashboard')
    }
  }, [email, password, login, router])


  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-brand-100 p-4">
      <div className="w-full max-w-md space-y-6">
        {/* 로고 및 헤더 */}
        <div className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 brand-gradient rounded-2xl flex items-center justify-center">
            <Store className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold brand-text">우리가게 도우미</h1>
            <p className="text-muted-foreground mt-2">
              소상공인을 위한 스마트 리뷰 관리 서비스
            </p>
          </div>
        </div>

        {/* 로그인 폼 */}
        <Card className="border-0 shadow-xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">로그인</CardTitle>
            <CardDescription className="text-center">
              계정에 로그인하여 서비스를 이용하세요
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* 서버 에러 표시 */}
              {error && (
                <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
                  {error}
                </div>
              )}

              {/* 이메일 */}
              <div className="space-y-2">
                <Label htmlFor="email">이메일</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="store@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (formErrors.email) {
                      setFormErrors(prev => ({ ...prev, email: undefined }))
                    }
                  }}
                  error={!!formErrors.email}
                  helpText={formErrors.email}
                  disabled={isLoading}
                />
              </div>

              {/* 비밀번호 */}
              <div className="space-y-2">
                <Label htmlFor="password">비밀번호</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="비밀번호를 입력하세요"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      if (formErrors.password) {
                        setFormErrors(prev => ({ ...prev, password: undefined }))
                      }
                    }}
                    error={!!formErrors.password}
                    helpText={formErrors.password}
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-2 text-muted-foreground hover:text-foreground"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* 로그인 유지 */}
              <div className="flex items-center space-x-2">
                <input
                  id="remember"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                  disabled={isLoading}
                />
                <Label htmlFor="remember" className="text-sm">
                  로그인 상태 유지
                </Label>
              </div>

              {/* 로그인 버튼 */}
              <Button
                type="submit"
                variant="brand"
                size="lg"
                className="w-full"
                disabled={isLoading}
                loading={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    로그인 중...
                  </>
                ) : (
                  '로그인'
                )}
              </Button>

              {/* 비밀번호 찾기 */}
              <div className="text-center">
                <Link
                  href="/forgot-password"
                  className="text-sm text-brand-600 hover:text-brand-700 hover:underline"
                >
                  비밀번호를 잊으셨나요?
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* 회원가입 링크 */}
        <div className="text-center space-y-4">
          <p className="text-sm text-muted-foreground">
            아직 계정이 없으신가요?{' '}
            <Link
              href="/register"
              className="text-brand-600 hover:text-brand-700 font-medium hover:underline"
            >
              회원가입
            </Link>
          </p>
          
          {/* 추가 정보 */}
          <div className="text-xs text-muted-foreground space-y-1">
            <p>• 무료 체험으로 서비스를 경험해보세요</p>
            <p>• 월 10개 리뷰까지 무료로 분석 가능</p>
          </div>
          
          {/* 개발 환경 데모 계정 안내 */}
          <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-800 font-medium mb-2">🔓 데모 계정으로 체험하기</p>
            <div className="text-xs text-blue-700 space-y-1">
              <p>이메일: <code className="bg-blue-100 px-1 rounded">demo@example.com</code></p>
              <p>비밀번호: <code className="bg-blue-100 px-1 rounded">demo123</code></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}