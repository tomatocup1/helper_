"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/store/auth-store-supabase'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { 
  ArrowLeft, 
  Globe, 
  Eye, 
  EyeOff, 
  Loader2,
  CheckCircle,
  AlertCircle,
  Store 
} from 'lucide-react'

type Platform = 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'

// 백엔드 URL 상수
const BACKEND_URL = 'https://helper-backend-4ilp.onrender.com'

interface PlatformInfo {
  id: Platform
  name: string
  description: string
  color: string
  bgColor: string
  icon: string
  loginUrl: string
}

const platforms: PlatformInfo[] = [
  {
    id: 'naver',
    name: '네이버 플레이스',
    description: '네이버 지도, 블로그 리뷰 관리',
    color: 'text-green-600',
    bgColor: 'bg-green-50 border-green-200 hover:border-green-300',
    icon: '🗺️',
    loginUrl: 'https://nid.naver.com/nidlogin.login'
  },
  {
    id: 'baemin',
    name: '배달의민족',
    description: '배달 주문, 리뷰 관리',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 border-blue-200 hover:border-blue-300',
    icon: '🛵',
    loginUrl: 'https://ceo.baemin.com/'
  },
  {
    id: 'yogiyo',
    name: '요기요',
    description: '요기요 사장님 서비스',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50 border-orange-200 hover:border-orange-300',
    icon: '🍕',
    loginUrl: 'https://ceo.yogiyo.co.kr/'
  },
  {
    id: 'coupangeats',
    name: '쿠팡이츠',
    description: '쿠팡이츠 사장님 서비스',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50 border-purple-200 hover:border-purple-300',
    icon: '🚚',
    loginUrl: 'https://partners.coupangeats.com/'
  }
]

const steps = [
  { id: 1, title: '플랫폼 선택', description: '매장이 등록된 플랫폼을 선택하세요' },
  { id: 2, title: '계정 연결', description: '플랫폼 로그인 정보를 입력하세요' },
  { id: 3, title: '매장 수집', description: '자동으로 매장 정보를 수집합니다' }
]

export default function AddStorePage() {
  const router = useRouter()
  const { user } = useAuth()
  const [currentStep, setCurrentStep] = useState(1)
  
  // 개발 모드용 임시 사용자 데이터
  const displayUser = user || {
    id: 'test-user-id',
    name: '테스트 사용자',
    email: 'test@example.com'
  }
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionResult, setConnectionResult] = useState<'success' | 'error' | null>(null)
  const [discoveredStores, setDiscoveredStores] = useState<any[]>([])
  const [selectedStores, setSelectedStores] = useState<string[]>([])
  const [isRegistering, setIsRegistering] = useState(false)
  
  // 폼 상태
  const [formData, setFormData] = useState({
    platform_id: '',
    platform_password: '',
  })
  
  const [errors, setErrors] = useState<{[key: string]: string}>({})

  const handlePlatformSelect = (platform: Platform) => {
    setSelectedPlatform(platform)
    setCurrentStep(2)
  }

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {}
    
    if (!formData.platform_id.trim()) {
      newErrors.platform_id = '계정 아이디/이메일을 입력해주세요'
    }
    
    if (!formData.platform_password.trim()) {
      newErrors.platform_password = '비밀번호를 입력해주세요'
    } else if (formData.platform_password.length < 6) {
      newErrors.platform_password = '비밀번호는 6자 이상이어야 합니다'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleConnect = async () => {
    if (!validateForm() || !selectedPlatform) return

    setIsConnecting(true)
    setCurrentStep(3)

    try {
      // Render 백엔드로 직접 API 호출
      const response = await fetch(`${BACKEND_URL}/api/v1/platform/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          platform: selectedPlatform,
          credentials: {
            username: formData.platform_id,
            password: formData.platform_password
          },
          user_id: user?.id || 'a7654c42-10ed-435f-97d8-d2c2dfeccbcb' // 실제 로그인된 사용자 ID
        })
      })
      
      const result = await response.json()
      
      // 응답 데이터 안전성 검증
      if (!result || typeof result !== 'object') {
        console.error('Connection failed: Invalid response format')
        setConnectionResult('error')
        return
      }
      
      if (response.ok && result.success === true) {
        // stores 배열 안전성 검증
        const stores = Array.isArray(result.stores) ? result.stores : []
        setDiscoveredStores(stores)
        setConnectionResult('success')
      } else {
        const errorMessage = result.error || result.error_message || '연결 실패'
        console.error('Connection failed:', errorMessage)
        setConnectionResult('error')
      }
      
    } catch (error) {
      console.error('Connection failed:', error)
      setConnectionResult('error')
    } finally {
      setIsConnecting(false)
    }
  }

  const handleStoreSelection = (storeId: string, checked: boolean) => {
    setSelectedStores(prev =>
      checked
        ? [...prev, storeId]
        : prev.filter(id => id !== storeId)
    )
  }

  const handleSelectAll = () => {
    setSelectedStores(discoveredStores.map(store => store.platform_store_id || store.id))
  }

  const handleSelectNone = () => {
    setSelectedStores([])
  }

  const handleRegisterSelectedStores = async () => {
    if (selectedStores.length === 0) return

    setIsRegistering(true)
    try {
      const selectedStoreData = discoveredStores.filter(store => {
        const storeKey = store.platform_store_id || store.id;
        return selectedStores.includes(storeKey);
      })

      for (const store of selectedStoreData) {
        const response = await fetch(`${BACKEND_URL}/api/stores`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: displayUser?.id || user?.id || 'a7654c42-10ed-435f-97d8-d2c2dfeccbcb',
            platform: selectedPlatform,
            platform_store_id: store.platform_store_id,
            store_name: store.store_name || store.name,
            platform_url: store.platform_url || `https://${selectedPlatform}.com/store/${store.platform_store_id}`,
            platform_id: formData.platform_id,
            platform_pw: formData.platform_password,
          })
        })

        if (!response.ok) {
          try {
            const errorData = await response.json()
            console.error('Failed to register store:', store.name, 'Error:', errorData?.error || 'Unknown error')
          } catch (e) {
            console.error('Failed to register store:', store.name, 'Parse error:', e)
          }
        } else {
          try {
            const successData = await response.json()
            console.log('Successfully registered store:', store.name, successData?.message || 'Success')
          } catch (e) {
            console.log('Successfully registered store:', store.name, 'Response parse error:', e)
          }
        }
      }

      router.push('/stores')
    } catch (error) {
      console.error('Error registering stores:', error)
    } finally {
      setIsRegistering(false)
    }
  }

  const handleFinish = () => {
    router.push('/stores')
  }

  const currentPlatform = platforms.find(p => p.id === selectedPlatform)

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* 헤더 */}
      <div className="flex items-center space-x-4">
        <Link href="/stores">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold brand-text">매장 추가</h1>
          <p className="text-muted-foreground">플랫폼 계정을 연결하여 매장을 자동으로 등록하세요</p>
        </div>
      </div>

      {/* 진행 단계 */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium
                  ${currentStep >= step.id 
                    ? 'bg-brand-600 text-white' 
                    : 'bg-gray-100 text-gray-500'
                  }`}>
                  {step.id}
                </div>
                <div className="ml-3">
                  <p className={`text-sm font-medium ${
                    currentStep >= step.id ? 'text-brand-600' : 'text-gray-500'
                  }`}>
                    {step.title}
                  </p>
                  <p className="text-xs text-muted-foreground">{step.description}</p>
                </div>
                {index < steps.length - 1 && (
                  <div className={`w-12 h-0.5 mx-4 ${
                    currentStep > step.id ? 'bg-brand-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Step 1: 플랫폼 선택 */}
      {currentStep === 1 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">플랫폼 선택</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {platforms.map((platform) => (
              <Card 
                key={platform.id}
                className={`cursor-pointer transition-all duration-200 ${platform.bgColor}
                  ${selectedPlatform === platform.id ? 'ring-2 ring-brand-500' : ''}
                `}
                onClick={() => handlePlatformSelect(platform.id)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start space-x-4">
                    <div className="text-3xl">{platform.icon}</div>
                    <div className="flex-1">
                      <h3 className={`text-lg font-semibold ${platform.color}`}>
                        {platform.name}
                      </h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        {platform.description}
                      </p>
                      <div className="mt-3">
                        <Badge variant="outline" className="text-xs">
                          자동 매장 수집
                        </Badge>
                      </div>
                    </div>
                    <Globe className={`w-5 h-5 ${platform.color}`} />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: 계정 연결 */}
      {currentStep === 2 && currentPlatform && (
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold">계정 연결</h2>
            <p className="text-muted-foreground">
              {currentPlatform.name} 로그인 정보를 입력하세요
            </p>
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center space-x-3">
                <div className="text-2xl">{currentPlatform.icon}</div>
                <div>
                  <CardTitle className={currentPlatform.color}>
                    {currentPlatform.name}
                  </CardTitle>
                  <CardDescription>
                    안전하게 암호화되어 저장됩니다
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="platform_id">
                  계정 아이디 {currentPlatform.id === 'naver' ? '(이메일)' : ''}
                </Label>
                <Input
                  id="platform_id"
                  type={currentPlatform.id === 'naver' ? 'email' : 'text'}
                  placeholder={
                    currentPlatform.id === 'naver' 
                      ? 'example@naver.com' 
                      : '로그인 아이디를 입력하세요'
                  }
                  value={formData.platform_id}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    platform_id: e.target.value
                  }))}
                  error={!!errors.platform_id}
                  helpText={errors.platform_id}
                />
              </div>

              <div>
                <Label htmlFor="platform_password">비밀번호</Label>
                <div className="relative">
                  <Input
                    id="platform_password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="비밀번호를 입력하세요"
                    value={formData.platform_password}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      platform_password: e.target.value
                    }))}
                    error={!!errors.platform_password}
                    helpText={errors.platform_password}
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

              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
                <div className="flex items-start space-x-2">
                  <AlertCircle className="w-4 h-4 text-blue-600 mt-0.5" />
                  <div className="text-sm text-blue-800">
                    <p className="font-medium">보안 안내</p>
                    <p>계정 정보는 암호화되어 안전하게 저장되며, 매장 정보 수집 목적으로만 사용됩니다.</p>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-md p-3">
                <div className="flex items-start space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5" />
                  <div className="text-sm text-green-800">
                    <p className="font-medium">크롤링 시각화</p>
                    <p>매장 추가 시 브라우저 창이 열려서 실제 로그인 및 크롤링 과정을 확인할 수 있습니다.</p>
                    <p className="text-xs mt-1">헤드리스 모드가 비활성화되어 있어 모든 과정이 실시간으로 표시됩니다.</p>
                  </div>
                </div>
              </div>

              <div className="flex space-x-3 pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setCurrentStep(1)}
                  className="flex-1"
                >
                  이전
                </Button>
                <Button 
                  variant="brand"
                  onClick={handleConnect}
                  disabled={!formData.platform_id || !formData.platform_password}
                  className="flex-1"
                >
                  연결하기
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Step 3: 매장 수집 */}
      {currentStep === 3 && currentPlatform && (
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold">매장 수집</h2>
            <p className="text-muted-foreground">
              {currentPlatform.name}에서 매장 정보를 수집하고 있습니다
            </p>
          </div>

          <Card>
            <CardContent className="p-8">
              {isConnecting ? (
                <div className="text-center space-y-4">
                  <div className="flex items-center justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
                  </div>
                  <div>
                    <p className="font-medium">매장 정보 수집 중...</p>
                    <p className="text-sm text-muted-foreground">
                      {currentPlatform.name}에 로그인하여 매장 목록을 가져오고 있습니다
                    </p>
                    <p className="text-xs text-green-600 mt-2">
                      🌐 브라우저 창이 열려서 실제 크롤링 과정을 확인할 수 있습니다
                    </p>
                  </div>
                </div>
              ) : connectionResult === 'success' ? (
                <div className="space-y-6">
                  <div className="text-center">
                    <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-green-800">연결 성공!</h3>
                    <p className="text-sm text-green-600">
                      {discoveredStores.length}개의 매장을 발견했습니다
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">등록할 매장 선택</h4>
                      <div className="flex space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={handleSelectAll}
                          disabled={selectedStores.length === discoveredStores.length}
                        >
                          전체 선택
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={handleSelectNone}
                          disabled={selectedStores.length === 0}
                        >
                          선택 해제
                        </Button>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {discoveredStores.map((store) => {
                        const storeKey = store.platform_store_id || store.id;
                        return (
                          <div key={storeKey} className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200 hover:bg-blue-100 transition-colors">
                            <Checkbox
                              checked={selectedStores.includes(storeKey)}
                              onCheckedChange={(checked) => handleStoreSelection(storeKey, checked as boolean)}
                            />
                            <Store className="w-5 h-5 text-blue-600" />
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <p className="font-semibold text-lg">{store.store_name || store.name}</p>
                                <Badge variant="secondary" className="text-xs">
                                  ID: {store.platform_store_id}
                                </Badge>
                              </div>
                              <p className="text-sm text-gray-600 mt-1">
                                {currentPlatform?.name} 매장
                              </p>
                            </div>
                            {selectedStores.includes(storeKey) && (
                              <Badge className="bg-green-100 text-green-800 border-green-200">
                                ✓ 선택됨
                              </Badge>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    <div className="bg-gray-50 p-3 rounded-lg">
                      <p className="text-sm text-gray-600">
                        선택된 매장: <span className="font-medium">{selectedStores.length}개</span> / {discoveredStores.length}개
                      </p>
                    </div>
                  </div>

                  <div className="flex space-x-3">
                    <Button 
                      variant="outline" 
                      onClick={handleFinish}
                      className="flex-1"
                    >
                      나중에 등록
                    </Button>
                    <Button 
                      variant="brand" 
                      onClick={handleRegisterSelectedStores}
                      disabled={selectedStores.length === 0 || isRegistering}
                      className="flex-1"
                    >
                      {isRegistering ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          등록 중...
                        </>
                      ) : (
                        `${selectedStores.length}개 매장 등록`
                      )}
                    </Button>
                  </div>
                </div>
              ) : connectionResult === 'error' ? (
                <div className="text-center space-y-4">
                  <AlertCircle className="w-12 h-12 text-red-600 mx-auto" />
                  <div>
                    <h3 className="text-lg font-semibold text-red-800">연결 실패</h3>
                    <p className="text-sm text-red-600">
                      ID / PW를 확인하고 다시 시도해주세요
                    </p>
                  </div>
                  <Button 
                    variant="outline" 
                    onClick={() => setCurrentStep(2)}
                  >
                    다시 시도
                  </Button>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}