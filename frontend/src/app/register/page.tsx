"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/store/auth-store-supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Eye, EyeOff, Loader2, Store, Check } from 'lucide-react'

export default function RegisterPage() {
  const router = useRouter()
  const { register, isAuthenticated, isLoading, error, clearError } = useAuth()
  
  const [showPassword, setShowPassword] = useState(false)
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false)
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    business_number: '',
  })
  const [formErrors, setFormErrors] = useState<{[key: string]: string | undefined}>({})
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [agreedToPrivacy, setAgreedToPrivacy] = useState(false)

  // 이미 로그인된 경우 대시보드로 리디렉션
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, router])

  // 에러 상태 초기화
  useEffect(() => {
    clearError()
  }, [])

  const validateForm = (): boolean => {
    const errors: {[key: string]: string | undefined} = {}

    // 이메일 검증
    if (!formData.email) {
      errors.email = '이메일을 입력해주세요.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = '올바른 이메일 형식을 입력해주세요.'
    }

    // 비밀번호 검증
    if (!formData.password) {
      errors.password = '비밀번호를 입력해주세요.'
    } else if (formData.password.length < 8) {
      errors.password = '비밀번호는 최소 8자 이상이어야 합니다.'
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      errors.password = '비밀번호는 대문자, 소문자, 숫자를 포함해야 합니다.'
    }

    // 비밀번호 확인 검증
    if (!passwordConfirm) {
      errors.passwordConfirm = '비밀번호 확인을 입력해주세요.'
    } else if (formData.password !== passwordConfirm) {
      errors.passwordConfirm = '비밀번호가 일치하지 않습니다.'
    }

    // 이름 검증
    if (!formData.name) {
      errors.name = '이름을 입력해주세요.'
    } else if (formData.name.length < 2) {
      errors.name = '이름은 2자 이상이어야 합니다.'
    }

    // 전화번호 검증 (선택사항)
    if (formData.phone && !/^010-\d{4}-\d{4}$/.test(formData.phone)) {
      errors.phone = '올바른 전화번호 형식을 입력해주세요. (010-0000-0000)'
    }

    // 사업자등록번호 검증 (선택사항)
    if (formData.business_number && !/^\d{3}-\d{2}-\d{5}$/.test(formData.business_number)) {
      errors.business_number = '올바른 사업자등록번호 형식을 입력해주세요. (000-00-00000)'
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    if (!agreedToTerms || !agreedToPrivacy) {
      alert('서비스 이용약관과 개인정보처리방침에 동의해주세요.')
      return
    }

    try {
      const success = await register({
        ...formData,
        terms_agreed: agreedToTerms,
        privacy_agreed: agreedToPrivacy,
        marketing_agreed: false
      })
      
      if (success) {
        router.push('/dashboard')
      }
    } catch (registerError: any) {
      console.error('Register error:', registerError)
      
      // Supabase 설정 오류 감지
      if (registerError?.message?.includes('Invalid API key') || 
          registerError?.message?.includes('Project not found')) {
        console.error('🚨 Supabase configuration error detected!')
        console.error('📋 Please check your .env.local file and follow SUPABASE_FIX_GUIDE.md')
        alert('서비스 설정 오류가 발생했습니다. 개발자 콘솔을 확인해주세요.')
      } else {
        // 기타 회원가입 오류
        alert(registerError?.message || '회원가입 중 오류가 발생했습니다.')
      }
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
    
    // 에러 클리어
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: undefined
      }))
    }
  }

  const handlePhoneChange = (value: string) => {
    // 전화번호 자동 포맷팅
    const cleaned = value.replace(/\D/g, '')
    let formatted = cleaned
    
    if (cleaned.length >= 7) {
      formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3, 7)}-${cleaned.slice(7, 11)}`
    } else if (cleaned.length >= 3) {
      formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3)}`
    }
    
    handleInputChange('phone', formatted)
  }

  const handleBusinessNumberChange = (value: string) => {
    // 사업자등록번호 자동 포맷팅
    const cleaned = value.replace(/\D/g, '')
    let formatted = cleaned
    
    if (cleaned.length >= 8) {
      formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3, 5)}-${cleaned.slice(5, 10)}`
    } else if (cleaned.length >= 5) {
      formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3, 5)}-${cleaned.slice(5)}`
    } else if (cleaned.length >= 3) {
      formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3)}`
    }
    
    handleInputChange('business_number', formatted)
  }

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

        {/* 회원가입 폼 */}
        <Card className="border-0 shadow-xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">회원가입</CardTitle>
            <CardDescription className="text-center">
              무료로 시작하여 가게 운영을 스마트하게
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
                <Label htmlFor="email">이메일 *</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="store@example.com"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  error={!!formErrors.email}
                  helpText={formErrors.email}
                  disabled={isLoading}
                />
              </div>

              {/* 이름 */}
              <div className="space-y-2">
                <Label htmlFor="name">이름 *</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="홍길동"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  error={!!formErrors.name}
                  helpText={formErrors.name}
                  disabled={isLoading}
                />
              </div>

              {/* 전화번호 */}
              <div className="space-y-2">
                <Label htmlFor="phone">전화번호</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="010-0000-0000"
                  value={formData.phone || ''}
                  onChange={(e) => handlePhoneChange(e.target.value)}
                  error={!!formErrors.phone}
                  helpText={formErrors.phone}
                  disabled={isLoading}
                />
              </div>

              {/* 사업자등록번호 */}
              <div className="space-y-2">
                <Label htmlFor="business_number">사업자등록번호</Label>
                <Input
                  id="business_number"
                  type="text"
                  placeholder="000-00-00000"
                  value={formData.business_number || ''}
                  onChange={(e) => handleBusinessNumberChange(e.target.value)}
                  error={!!formErrors.business_number}
                  helpText={formErrors.business_number}
                  disabled={isLoading}
                />
              </div>

              {/* 비밀번호 */}
              <div className="space-y-2">
                <Label htmlFor="password">비밀번호 *</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="8자 이상, 대문자/소문자/숫자 포함"
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
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

              {/* 비밀번호 확인 */}
              <div className="space-y-2">
                <Label htmlFor="passwordConfirm">비밀번호 확인 *</Label>
                <div className="relative">
                  <Input
                    id="passwordConfirm"
                    type={showPasswordConfirm ? 'text' : 'password'}
                    placeholder="비밀번호를 다시 입력하세요"
                    value={passwordConfirm}
                    onChange={(e) => {
                      setPasswordConfirm(e.target.value)
                      if (formErrors.passwordConfirm) {
                        setFormErrors(prev => ({
                          ...prev,
                          passwordConfirm: undefined
                        }))
                      }
                    }}
                    error={!!formErrors.passwordConfirm}
                    helpText={formErrors.passwordConfirm}
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-2 text-muted-foreground hover:text-foreground"
                    onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                  >
                    {showPasswordConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* 약관 동의 */}
              <div className="space-y-3 pt-4">
                <div className="flex items-center space-x-2">
                  <input
                    id="terms"
                    type="checkbox"
                    checked={agreedToTerms}
                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                    className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                    disabled={isLoading}
                  />
                  <Label htmlFor="terms" className="text-sm">
                    <Link href="/terms" className="text-brand-600 hover:underline">
                      서비스 이용약관
                    </Link>에 동의합니다 *
                  </Label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <input
                    id="privacy"
                    type="checkbox"
                    checked={agreedToPrivacy}
                    onChange={(e) => setAgreedToPrivacy(e.target.checked)}
                    className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                    disabled={isLoading}
                  />
                  <Label htmlFor="privacy" className="text-sm">
                    <Link href="/privacy" className="text-brand-600 hover:underline">
                      개인정보처리방침
                    </Link>에 동의합니다 *
                  </Label>
                </div>
              </div>

              {/* 회원가입 버튼 */}
              <Button
                type="submit"
                variant="brand"
                size="lg"
                className="w-full"
                disabled={isLoading || !agreedToTerms || !agreedToPrivacy}
                loading={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    계정 생성 중...
                  </>
                ) : (
                  '무료로 시작하기'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* 로그인 링크 */}
        <div className="text-center space-y-4">
          <p className="text-sm text-muted-foreground">
            이미 계정이 있으신가요?{' '}
            <Link
              href="/login"
              className="text-brand-600 hover:text-brand-700 font-medium hover:underline"
            >
              로그인
            </Link>
          </p>
          
          {/* 무료 체험 혜택 */}
          <div className="text-xs text-muted-foreground space-y-1">
            <div className="flex items-center justify-center space-x-1">
              <Check className="w-3 h-3 text-green-600" />
              <span>월 10개 리뷰 무료 분석</span>
            </div>
            <div className="flex items-center justify-center space-x-1">
              <Check className="w-3 h-3 text-green-600" />
              <span>AI 자동 답글 생성</span>
            </div>
            <div className="flex items-center justify-center space-x-1">
              <Check className="w-3 h-3 text-green-600" />
              <span>기본 분석 리포트 제공</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}