"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import {
  User,
  Bell,
  Shield,
  CreditCard,
  Zap,
  Settings as SettingsIcon,
  Mail,
  Phone,
  MapPin,
  Edit,
  Save,
  X,
  Check,
  AlertTriangle,
  Crown,
  Smartphone,
  Globe,
  Key,
  Download,
  Upload,
  Trash2
} from 'lucide-react'

// Mock data - 실제 구현 시 API에서 가져올 데이터
const mockUserSettings = {
  profile: {
    name: '김사장',
    email: 'owner@example.com',
    phone: '010-1234-5678',
    business_number: '123-45-67890',
    address: '서울시 강남구 테헤란로 123',
    company_name: '우리가게',
    profile_image: null
  },
  subscription: {
    tier: 'premium',
    status: 'active',
    next_billing_date: '2024-09-13',
    monthly_usage: {
      reviews_analyzed: 45,
      ai_replies_generated: 23,
      limit: 100
    }
  },
  notifications: {
    email_new_reviews: true,
    email_negative_reviews: true,
    email_weekly_report: true,
    sms_urgent_alerts: false,
    push_notifications: true
  },
  api_settings: {
    webhook_url: 'https://api.mystore.com/webhook',
    api_key: 'sk_live_**********************',
    auto_reply_enabled: true,
    ai_tone: 'friendly',
    response_language: 'ko'
  },
  integrations: {
    naver: { connected: true, last_sync: '2024-08-13T10:30:00Z' },
    google: { connected: true, last_sync: '2024-08-13T09:15:00Z' },
    kakao: { connected: false, last_sync: null }
  }
}

const subscriptionTiers = {
  basic: { 
    name: '베이직', 
    price: '무료', 
    color: 'bg-gray-100 text-gray-800',
    features: ['월 10개 리뷰 분석', '기본 AI 답글', '이메일 지원']
  },
  premium: { 
    name: '프리미엄', 
    price: '월 29,000원', 
    color: 'bg-blue-100 text-blue-800',
    features: ['월 100개 리뷰 분석', '고급 AI 답글', '실시간 알림', '우선 지원']
  },
  enterprise: { 
    name: '엔터프라이즈', 
    price: '월 99,000원', 
    color: 'bg-purple-100 text-purple-800',
    features: ['무제한 리뷰 분석', '커스텀 AI 모델', 'API 접근', '전담 매니저']
  }
}

const aiTones = [
  { value: 'friendly', label: '친근한 톤' },
  { value: 'professional', label: '전문적인 톤' },
  { value: 'casual', label: '캐주얼한 톤' },
  { value: 'formal', label: '정중한 톤' }
]

const languages = [
  { value: 'ko', label: '한국어' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'zh', label: '中文' }
]

export default function SettingsPage() {
  const { user, updateProfile } = useAuth()
  const [settings, setSettings] = useState(mockUserSettings)
  const [activeTab, setActiveTab] = useState('profile')
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [editForm, setEditForm] = useState(settings.profile)

  // 실제 구현 시 API 호출
  useEffect(() => {
    // fetchUserSettings()
  }, [])

  const tabs = [
    { id: 'profile', label: '프로필', icon: User },
    { id: 'subscription', label: '구독 관리', icon: CreditCard },
    { id: 'notifications', label: '알림 설정', icon: Bell },
    { id: 'integrations', label: '플랫폼 연동', icon: Globe },
    { id: 'api', label: 'API 설정', icon: Key },
    { id: 'security', label: '보안', icon: Shield }
  ]

  const handleSaveProfile = async () => {
    setIsSaving(true)
    try {
      // API 호출로 프로필 업데이트
      // await updateProfile(editForm)
      setSettings(prev => ({ ...prev, profile: editForm }))
      setIsEditing(false)
    } catch (error) {
      console.error('프로필 업데이트 실패:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleNotificationToggle = (key: string) => {
    setSettings(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        [key]: !prev.notifications[key as keyof typeof prev.notifications]
      }
    }))
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const getUsagePercentage = () => {
    const { reviews_analyzed, limit } = settings.subscription.monthly_usage
    return (reviews_analyzed / limit) * 100
  }

  const renderProfileTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>기본 정보</CardTitle>
            {!isEditing ? (
              <Button variant="outline" onClick={() => setIsEditing(true)}>
                <Edit className="w-4 h-4 mr-2" />
                편집
              </Button>
            ) : (
              <div className="flex space-x-2">
                <Button variant="outline" onClick={() => setIsEditing(false)}>
                  <X className="w-4 h-4 mr-2" />
                  취소
                </Button>
                <Button variant="brand" onClick={handleSaveProfile} disabled={isSaving}>
                  {isSaving ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  ) : (
                    <Save className="w-4 h-4 mr-2" />
                  )}
                  저장
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center space-x-6">
            <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center">
              <User className="w-8 h-8 text-gray-600" />
            </div>
            <div>
              <Button variant="outline" size="sm">
                <Upload className="w-4 h-4 mr-2" />
                사진 업로드
              </Button>
              <p className="text-xs text-gray-500 mt-1">JPG, PNG 파일 (최대 2MB)</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">이름</label>
              {isEditing ? (
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  value={editForm.name}
                  onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                />
              ) : (
                <p className="text-gray-900">{settings.profile.name}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">이메일</label>
              {isEditing ? (
                <input
                  type="email"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  value={editForm.email}
                  onChange={(e) => setEditForm(prev => ({ ...prev, email: e.target.value }))}
                />
              ) : (
                <p className="text-gray-900">{settings.profile.email}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">전화번호</label>
              {isEditing ? (
                <input
                  type="tel"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  value={editForm.phone}
                  onChange={(e) => setEditForm(prev => ({ ...prev, phone: e.target.value }))}
                />
              ) : (
                <p className="text-gray-900">{settings.profile.phone}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">사업자등록번호</label>
              {isEditing ? (
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  value={editForm.business_number}
                  onChange={(e) => setEditForm(prev => ({ ...prev, business_number: e.target.value }))}
                />
              ) : (
                <p className="text-gray-900">{settings.profile.business_number}</p>
              )}
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">주소</label>
              {isEditing ? (
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  value={editForm.address}
                  onChange={(e) => setEditForm(prev => ({ ...prev, address: e.target.value }))}
                />
              ) : (
                <p className="text-gray-900">{settings.profile.address}</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderSubscriptionTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>현재 구독 플랜</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Crown className="w-8 h-8 text-purple-600" />
              <div>
                <h3 className="text-lg font-medium">
                  {subscriptionTiers[settings.subscription.tier as keyof typeof subscriptionTiers].name} 플랜
                </h3>
                <p className="text-gray-600">
                  {subscriptionTiers[settings.subscription.tier as keyof typeof subscriptionTiers].price}
                </p>
              </div>
            </div>
            <Badge className={subscriptionTiers[settings.subscription.tier as keyof typeof subscriptionTiers].color}>
              {settings.subscription.status === 'active' ? '활성' : '비활성'}
            </Badge>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium mb-3">이번 달 사용량</h4>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span>리뷰 분석</span>
                <span>
                  {settings.subscription.monthly_usage.reviews_analyzed} / {settings.subscription.monthly_usage.limit}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-brand-600 h-2 rounded-full" 
                  style={{ width: `${getUsagePercentage()}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">다음 결제일</span>
            <span className="font-medium">{formatDate(settings.subscription.next_billing_date)}</span>
          </div>

          <div className="flex space-x-3">
            <Button variant="brand">
              플랜 업그레이드
            </Button>
            <Button variant="outline">
              결제 정보 변경
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 플랜 비교 */}
      <Card>
        <CardHeader>
          <CardTitle>플랜 비교</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            {Object.entries(subscriptionTiers).map(([key, tier]) => (
              <div key={key} className="border rounded-lg p-4 text-center">
                <h3 className="font-medium text-lg mb-2">{tier.name}</h3>
                <p className="text-2xl font-bold mb-4">{tier.price}</p>
                <ul className="space-y-2 text-sm">
                  {tier.features.map((feature, index) => (
                    <li key={index} className="flex items-center">
                      <Check className="w-4 h-4 text-green-600 mr-2" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Button 
                  variant={settings.subscription.tier === key ? "outline" : "brand"} 
                  className="w-full mt-4"
                  disabled={settings.subscription.tier === key}
                >
                  {settings.subscription.tier === key ? '현재 플랜' : '선택하기'}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderNotificationsTab = () => (
    <Card>
      <CardHeader>
        <CardTitle>알림 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">새 리뷰 알림</h4>
              <p className="text-sm text-gray-600">새로운 리뷰가 등록되면 이메일로 알림을 받습니다</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('email_new_reviews')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                settings.notifications.email_new_reviews ? 'bg-brand-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.notifications.email_new_reviews ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">부정적 리뷰 즉시 알림</h4>
              <p className="text-sm text-gray-600">부정적인 리뷰가 등록되면 즉시 알림을 받습니다</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('email_negative_reviews')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                settings.notifications.email_negative_reviews ? 'bg-brand-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.notifications.email_negative_reviews ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">주간 리포트</h4>
              <p className="text-sm text-gray-600">매주 분석 리포트를 이메일로 받습니다</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('email_weekly_report')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                settings.notifications.email_weekly_report ? 'bg-brand-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.notifications.email_weekly_report ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">SMS 긴급 알림</h4>
              <p className="text-sm text-gray-600">긴급한 이슈 발생시 SMS로 알림을 받습니다</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('sms_urgent_alerts')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                settings.notifications.sms_urgent_alerts ? 'bg-brand-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.notifications.sms_urgent_alerts ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  )

  const renderIntegrationsTab = () => (
    <Card>
      <CardHeader>
        <CardTitle>플랫폼 연동</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {Object.entries(settings.integrations).map(([platform, integration]) => (
          <div key={platform} className="flex items-center justify-between border rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <Globe className="w-8 h-8 text-gray-600" />
              <div>
                <h4 className="font-medium capitalize">{platform}</h4>
                <p className="text-sm text-gray-600">
                  {integration.connected ? (
                    `마지막 동기화: ${integration.last_sync ? formatDate(integration.last_sync) : '없음'}`
                  ) : (
                    '연결되지 않음'
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Badge className={integration.connected ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                {integration.connected ? '연결됨' : '연결 안됨'}
              </Badge>
              <Button variant={integration.connected ? "outline" : "brand"} size="sm">
                {integration.connected ? '연결 해제' : '연결하기'}
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )

  const renderApiTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>API 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">API 키</label>
            <div className="flex space-x-2">
              <input
                type="password"
                value={settings.api_settings.api_key}
                readOnly
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
              />
              <Button variant="outline" size="sm">
                새 키 생성
              </Button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">웹훅 URL</label>
            <input
              type="url"
              value={settings.api_settings.webhook_url}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">AI 답글 톤</label>
            <select
              value={settings.api_settings.ai_tone}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            >
              {aiTones.map(tone => (
                <option key={tone.value} value={tone.value}>{tone.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">응답 언어</label>
            <select
              value={settings.api_settings.response_language}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            >
              {languages.map(lang => (
                <option key={lang.value} value={lang.value}>{lang.label}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">자동 답글 활성화</h4>
              <p className="text-sm text-gray-600">새 리뷰에 AI가 자동으로 답글을 생성합니다</p>
            </div>
            <button
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                settings.api_settings.auto_reply_enabled ? 'bg-brand-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.api_settings.auto_reply_enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API 문서</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">개발자 문서</h4>
              <p className="text-sm text-gray-600">API 사용법과 예제를 확인하세요</p>
            </div>
            <Button variant="outline">
              <Download className="w-4 h-4 mr-2" />
              문서 다운로드
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderSecurityTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>보안 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">비밀번호 변경</h4>
              <p className="text-sm text-gray-600">정기적으로 비밀번호를 변경하세요</p>
            </div>
            <Button variant="outline">
              변경하기
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">2단계 인증</h4>
              <p className="text-sm text-gray-600">계정 보안을 강화하세요</p>
            </div>
            <Badge className="bg-red-100 text-red-800">비활성</Badge>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">로그인 기록</h4>
              <p className="text-sm text-gray-600">최근 로그인 활동을 확인하세요</p>
            </div>
            <Button variant="outline">
              보기
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-red-600">위험 구역</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="border border-red-200 rounded-lg p-4 bg-red-50">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-medium text-red-800">계정 삭제</h4>
                <p className="text-sm text-red-700 mt-1">
                  계정을 삭제하면 모든 데이터가 영구적으로 삭제됩니다. 이 작업은 되돌릴 수 없습니다.
                </p>
                <Button variant="outline" className="mt-3 border-red-300 text-red-700 hover:bg-red-50">
                  <Trash2 className="w-4 h-4 mr-2" />
                  계정 삭제
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile': return renderProfileTab()
      case 'subscription': return renderSubscriptionTab()
      case 'notifications': return renderNotificationsTab()
      case 'integrations': return renderIntegrationsTab()
      case 'api': return renderApiTab()
      case 'security': return renderSecurityTab()
      default: return renderProfileTab()
    }
  }

  return (
    <AppLayout>
      <div className="space-y-8">
      {/* 페이지 헤더 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">설정</h1>
        <p className="text-gray-600 mt-1">
          계정 정보와 서비스 설정을 관리하세요.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row lg:space-x-8">
        {/* 탭 네비게이션 */}
        <div className="lg:w-64 mb-8 lg:mb-0">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 text-left rounded-md transition-colors ${
                    activeTab === tab.id
                      ? 'bg-brand-100 text-brand-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* 탭 컨텐츠 */}
        <div className="flex-1">
          {renderTabContent()}
        </div>
      </div>
      </div>
    </AppLayout>
  )
}