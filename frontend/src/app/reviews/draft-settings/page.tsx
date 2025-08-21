"use client"

import { useState, useEffect } from 'react'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Settings, 
  Save, 
  Plus, 
  X, 
  Lightbulb, 
  MessageSquare,
  Target,
  Palette,
  Globe,
  Copy,
  Check,
  ExternalLink,
  Heart
} from 'lucide-react'

interface ReviewTemplate {
  id: string
  name: string
  content: string
  tone: 'friendly' | 'professional' | 'casual' | 'enthusiastic'
  minLength: number
  maxLength: number
  keywords: string[]
  isActive: boolean
}

interface DraftSettings {
  enabled: boolean
  defaultTone: string
  minTextLength: number
  maxTextLength: number
  includeKeywords: boolean
  autoApprove: boolean
  templates: ReviewTemplate[]
  // 키워드를 카테고리별로 분류
  positiveKeywords: string[]
  menuKeywords: string[]
  serviceKeywords: string[]
  atmosphereKeywords: string[]
  excludeWords: string[]
  customerMessage: string
  photoAnalysisPrompt: string
  naverReviewUrl: string
}

export default function ReviewDraftSettingsPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [newKeyword, setNewKeyword] = useState('')
  const [newMenuKeyword, setNewMenuKeyword] = useState('')
  const [newServiceKeyword, setNewServiceKeyword] = useState('')
  const [newAtmosphereKeyword, setNewAtmosphereKeyword] = useState('')
  const [newExcludeWord, setNewExcludeWord] = useState('')
  const [urlCopied, setUrlCopied] = useState(false)
  const [urlError, setUrlError] = useState('')
  const [isClient, setIsClient] = useState(false)
  
  // 로컬 스토리지에서 설정 불러오기
  const loadSettingsFromStorage = (): DraftSettings => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('reviewDraftSettings')
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch (error) {
          console.error('설정 불러오기 실패:', error)
        }
      }
    }
    
    // 기본 설정값
    return {
      enabled: true,
      defaultTone: 'friendly',
      minTextLength: 50,
      maxTextLength: 200,
      includeKeywords: true,
      autoApprove: false,
      templates: [
        {
          id: '1',
          name: '일반 칭찬 템플릿',
          content: '정말 맛있게 잘 먹었습니다! 친절한 서비스에 감사드려요. 다음에도 꼭 방문하겠습니다.',
          tone: 'friendly',
          minLength: 50,
          maxLength: 150,
          keywords: ['맛있다', '친절하다', '재방문'],
          isActive: true
        },
        {
          id: '2',
          name: '분위기 칭찬 템플릿',
          content: '분위기가 정말 좋네요! 깔끔하고 아늑한 공간에서 편안하게 식사할 수 있어서 좋았습니다.',
          tone: 'professional',
          minLength: 60,
          maxLength: 180,
          keywords: ['분위기', '깔끔하다', '편안하다'],
          isActive: true
        }
      ],
      positiveKeywords: ['맛집', '친절', '깔끔', '맛있다', '추천'],
      menuKeywords: ['음식', '메뉴', '요리', '맛', '식사'],
      serviceKeywords: ['서비스', '직원', '친절', '응대', '배려'],
      atmosphereKeywords: ['분위기', '인테리어', '공간', '조용', '아늑'],
      excludeWords: ['별로', '실망', '불친절'],
      customerMessage: '안녕하세요! 저희 매장을 방문해 주셔서 감사합니다. 리뷰 작성을 도와드리겠습니다.',
      photoAnalysisPrompt: '이 사진들을 분석하여 음식점의 분위기, 음식, 서비스를 파악하고 긍정적인 리뷰를 작성해주세요. 매장의 특색과 좋은 점들을 중심으로 따뜻하고 친근한 톤으로 리뷰를 작성해주세요.',
      naverReviewUrl: ''
    }
  }

  const [settings, setSettings] = useState<DraftSettings>(() => {
    // 기본값으로 초기화 (서버 사이드에서도 안전)
    return {
      enabled: true,
      defaultTone: 'friendly',
      minTextLength: 50,
      maxTextLength: 200,
      includeKeywords: true,
      autoApprove: false,
      templates: [],
      positiveKeywords: [],
      menuKeywords: [],
      serviceKeywords: [],
      atmosphereKeywords: [],
      excludeWords: [],
      customerMessage: '',
      photoAnalysisPrompt: '',
      naverReviewUrl: ''
    }
  })

  // 클라이언트 마운트 확인
  useEffect(() => {
    setIsClient(true)
    // 클라이언트에서만 localStorage에서 설정 로드
    setSettings(loadSettingsFromStorage())
  }, [])

  // 설정값 변경시 자동 저장
  useEffect(() => {
    if (isClient && typeof window !== 'undefined') {
      localStorage.setItem('reviewDraftSettings', JSON.stringify(settings))
    }
  }, [settings, isClient])

  const handleSave = async () => {
    // 네이버 URL 유효성 검증
    if (settings.naverReviewUrl && !validateNaverUrl(settings.naverReviewUrl)) {
      alert('네이버 리뷰 URL을 올바르게 입력해주세요.')
      return
    }

    setLoading(true)
    try {
      // 로컬 스토리지에 설정 저장
      if (typeof window !== 'undefined') {
        localStorage.setItem('reviewDraftSettings', JSON.stringify(settings))
      }
      
      // API 호출 로직 (나중에 실제 API로 교체)
      await new Promise(resolve => setTimeout(resolve, 1000)) // 시뮬레이션
      
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('설정 저장 실패:', error)
      alert('설정 저장에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const addPositiveKeyword = () => {
    if (newKeyword.trim() && !settings.positiveKeywords.includes(newKeyword.trim())) {
      setSettings(prev => ({
        ...prev,
        positiveKeywords: [...prev.positiveKeywords, newKeyword.trim()]
      }))
      setNewKeyword('')
    }
  }

  const removePositiveKeyword = (keyword: string) => {
    setSettings(prev => ({
      ...prev,
      positiveKeywords: prev.positiveKeywords.filter(k => k !== keyword)
    }))
  }

  const addMenuKeyword = () => {
    if (newMenuKeyword.trim() && !settings.menuKeywords.includes(newMenuKeyword.trim())) {
      setSettings(prev => ({
        ...prev,
        menuKeywords: [...prev.menuKeywords, newMenuKeyword.trim()]
      }))
      setNewMenuKeyword('')
    }
  }

  const removeMenuKeyword = (keyword: string) => {
    setSettings(prev => ({
      ...prev,
      menuKeywords: prev.menuKeywords.filter(k => k !== keyword)
    }))
  }

  const addServiceKeyword = () => {
    if (newServiceKeyword.trim() && !settings.serviceKeywords.includes(newServiceKeyword.trim())) {
      setSettings(prev => ({
        ...prev,
        serviceKeywords: [...prev.serviceKeywords, newServiceKeyword.trim()]
      }))
      setNewServiceKeyword('')
    }
  }

  const removeServiceKeyword = (keyword: string) => {
    setSettings(prev => ({
      ...prev,
      serviceKeywords: prev.serviceKeywords.filter(k => k !== keyword)
    }))
  }

  const addAtmosphereKeyword = () => {
    if (newAtmosphereKeyword.trim() && !settings.atmosphereKeywords.includes(newAtmosphereKeyword.trim())) {
      setSettings(prev => ({
        ...prev,
        atmosphereKeywords: [...prev.atmosphereKeywords, newAtmosphereKeyword.trim()]
      }))
      setNewAtmosphereKeyword('')
    }
  }

  const removeAtmosphereKeyword = (keyword: string) => {
    setSettings(prev => ({
      ...prev,
      atmosphereKeywords: prev.atmosphereKeywords.filter(k => k !== keyword)
    }))
  }

  const addExcludeWord = () => {
    if (newExcludeWord.trim() && !settings.excludeWords.includes(newExcludeWord.trim())) {
      setSettings(prev => ({
        ...prev,
        excludeWords: [...prev.excludeWords, newExcludeWord.trim()]
      }))
      setNewExcludeWord('')
    }
  }

  const removeExcludeWord = (word: string) => {
    setSettings(prev => ({
      ...prev,
      excludeWords: prev.excludeWords.filter(w => w !== word)
    }))
  }

  const addTemplate = () => {
    const newTemplate: ReviewTemplate = {
      id: Date.now().toString(),
      name: '새 템플릿',
      content: '',
      tone: 'friendly',
      minLength: settings.minTextLength,
      maxLength: settings.maxTextLength,
      keywords: [],
      isActive: true
    }
    setSettings(prev => ({
      ...prev,
      templates: [...prev.templates, newTemplate]
    }))
  }

  const updateTemplate = (id: string, updates: Partial<ReviewTemplate>) => {
    setSettings(prev => ({
      ...prev,
      templates: prev.templates.map(template => 
        template.id === id ? { ...template, ...updates } : template
      )
    }))
  }

  const removeTemplate = (id: string) => {
    setSettings(prev => ({
      ...prev,
      templates: prev.templates.filter(template => template.id !== id)
    }))
  }

  const validateNaverUrl = (url: string): boolean => {
    if (!url) return true // 빈 URL은 허용 (선택사항)
    
    try {
      const urlObj = new URL(url)
      // 네이버 도메인인지 확인
      const validDomains = ['naver.com', 'm.place.naver.com', 'place.naver.com']
      const isValidDomain = validDomains.some(domain => 
        urlObj.hostname === domain || urlObj.hostname.endsWith('.' + domain)
      )
      
      if (!isValidDomain) {
        setUrlError('네이버 도메인의 URL만 입력 가능합니다.')
        return false
      }
      
      setUrlError('')
      return true
    } catch (error) {
      setUrlError('올바른 URL 형식을 입력해주세요.')
      return false
    }
  }

  const copyCustomerUrl = async () => {
    const customerUrl = `${window.location.origin}/customer-review/demo-store-123`
    try {
      await navigator.clipboard.writeText(customerUrl)
      setUrlCopied(true)
      setTimeout(() => setUrlCopied(false), 2000)
    } catch (error) {
      console.error('URL 복사 실패:', error)
      alert('URL 복사에 실패했습니다. 직접 복사해주세요.')
    }
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold brand-text">고객님 리뷰 생성 설정</h1>
            <p className="text-muted-foreground">
              고객이 사진을 업로드하여 AI 리뷰 초안을 생성할 수 있도록 설정하세요
            </p>
          </div>
          <Button 
            onClick={handleSave} 
            disabled={loading}
            className="relative"
          >
            <Save className="w-4 h-4 mr-2" />
            {loading ? '저장 중...' : '설정 저장'}
            {saved && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-ping" />
            )}
          </Button>
        </div>

        <Tabs defaultValue="basic" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="basic">기본 설정</TabsTrigger>
            <TabsTrigger value="customer">고객 설정</TabsTrigger>
            <TabsTrigger value="templates">템플릿 관리</TabsTrigger>
            <TabsTrigger value="keywords">키워드 설정</TabsTrigger>
            <TabsTrigger value="advanced">고급 설정</TabsTrigger>
          </TabsList>

          {/* 기본 설정 */}
          <TabsContent value="basic" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Settings className="w-5 h-5 mr-2" />
                  기본 설정
                </CardTitle>
                <CardDescription>
                  리뷰 초안 생성의 기본 동작을 설정합니다
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>리뷰 초안 생성 활성화</Label>
                    <p className="text-sm text-muted-foreground">
                      고객이 QR 코드를 스캔했을 때 리뷰 초안을 자동으로 생성합니다
                    </p>
                  </div>
                  <Switch
                    checked={settings.enabled}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({ ...prev, enabled: checked }))
                    }
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-2">
                    <Label>기본 톤 스타일</Label>
                    <Select
                      value={settings.defaultTone}
                      onValueChange={(value) => 
                        setSettings(prev => ({ ...prev, defaultTone: value }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="friendly">친근한 톤</SelectItem>
                        <SelectItem value="professional">전문적인 톤</SelectItem>
                        <SelectItem value="casual">캐주얼한 톤</SelectItem>
                        <SelectItem value="enthusiastic">열정적인 톤</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>최소 글자 수</Label>
                    <Input
                      type="text"
                      value={settings.minTextLength}
                      onChange={(e) => {
                        const value = e.target.value
                        // 숫자만 허용
                        if (value === '' || /^\d+$/.test(value)) {
                          const numValue = value === '' ? 0 : parseInt(value)
                          if (numValue <= 500) {
                            setSettings(prev => ({ 
                              ...prev, 
                              minTextLength: numValue
                            }))
                          }
                        }
                      }}
                      onBlur={(e) => {
                        // 포커스 해제 시 최소값 보정
                        const value = parseInt(e.target.value) || 10
                        if (value < 10) {
                          setSettings(prev => ({ 
                            ...prev, 
                            minTextLength: 10
                          }))
                        }
                      }}
                      placeholder="10"
                    />
                    <p className="text-xs text-muted-foreground">
                      10자 ~ 500자 (권장: 50-100자)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>최대 글자 수</Label>
                    <Input
                      type="text"
                      value={settings.maxTextLength}
                      onChange={(e) => {
                        const value = e.target.value
                        // 숫자만 허용
                        if (value === '' || /^\d+$/.test(value)) {
                          const numValue = value === '' ? 0 : parseInt(value)
                          if (numValue <= 1000) {
                            setSettings(prev => ({ 
                              ...prev, 
                              maxTextLength: numValue
                            }))
                          }
                        }
                      }}
                      onBlur={(e) => {
                        // 포커스 해제 시 최소값 보정
                        const value = parseInt(e.target.value) || 200
                        const minRequired = Math.max(settings.minTextLength + 10, 50)
                        if (value < minRequired) {
                          setSettings(prev => ({ 
                            ...prev, 
                            maxTextLength: minRequired
                          }))
                        }
                      }}
                      placeholder="200"
                    />
                    <p className="text-xs text-muted-foreground">
                      {isClient ? `${Math.max(settings.minTextLength + 10, 50)}자 ~ 1000자 (권장: 150-300자)` : '50자 ~ 1000자 (권장: 150-300자)'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>키워드 자동 포함</Label>
                    <p className="text-sm text-muted-foreground">
                      설정된 비즈니스 키워드를 리뷰에 자동으로 포함합니다
                    </p>
                  </div>
                  <Switch
                    checked={settings.includeKeywords}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({ ...prev, includeKeywords: checked }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>초안 자동 승인</Label>
                    <p className="text-sm text-muted-foreground">
                      생성된 초안을 사장님 검토 없이 고객에게 바로 제공합니다
                    </p>
                  </div>
                  <Switch
                    checked={settings.autoApprove}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({ ...prev, autoApprove: checked }))
                    }
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 고객 설정 */}
          <TabsContent value="customer" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MessageSquare className="w-5 h-5 mr-2" />
                  고객 페이지 설정
                </CardTitle>
                <CardDescription>
                  고객이 리뷰 작성 시 보게 될 메시지와 AI 분석 설정을 관리하세요
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label className="text-base font-medium">고객 환영 메시지</Label>
                  <Textarea
                    value={settings.customerMessage}
                    onChange={(e) => 
                      setSettings(prev => ({ ...prev, customerMessage: e.target.value }))
                    }
                    placeholder="고객이 페이지를 방문했을 때 보여줄 환영 메시지를 입력하세요..."
                    rows={3}
                    className="resize-none"
                  />
                  <p className="text-sm text-muted-foreground">
                    고객용 페이지 상단에 표시되는 환영 메시지입니다.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label className="text-base font-medium">AI 사진 분석 프롬프트</Label>
                  <Textarea
                    value={settings.photoAnalysisPrompt}
                    onChange={(e) => 
                      setSettings(prev => ({ ...prev, photoAnalysisPrompt: e.target.value }))
                    }
                    placeholder="GPT-4o-mini가 사진을 분석할 때 사용할 프롬프트를 입력하세요..."
                    rows={4}
                    className="resize-none"
                  />
                  <p className="text-sm text-muted-foreground">
                    AI가 고객의 사진을 분석하여 리뷰를 생성할 때 사용하는 지침입니다. 매장의 특색과 원하는 리뷰 스타일을 반영하여 작성하세요.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label className="text-base font-medium">네이버 리뷰 작성 페이지 URL</Label>
                  <Input
                    value={settings.naverReviewUrl}
                    onChange={(e) => {
                      const newUrl = e.target.value
                      setSettings(prev => ({ ...prev, naverReviewUrl: newUrl }))
                      if (newUrl) {
                        validateNaverUrl(newUrl)
                      } else {
                        setUrlError('')
                      }
                    }}
                    placeholder="https://m.place.naver.com/restaurant/..."
                    type="url"
                    className={urlError ? "border-red-500 focus-visible:ring-red-500" : ""}
                  />
                  {urlError && (
                    <p className="text-sm text-red-600 flex items-center">
                      <X className="w-4 h-4 mr-1" />
                      {urlError}
                    </p>
                  )}
                  <p className="text-sm text-muted-foreground">
                    고객이 리뷰를 복사한 후 이동할 네이버 스마트플레이스 리뷰 작성 페이지 URL을 입력하세요. 모바일 URL을 권장합니다.
                  </p>
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <p className="text-sm text-amber-800">
                      <strong>💡 URL 찾는 방법:</strong><br/>
                      1. 네이버에서 매장 검색 → 매장 페이지 접속<br/>
                      2. "리뷰 쓰기" 버튼 클릭<br/>
                      3. 주소창의 URL 복사하여 붙여넣기
                    </p>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex">
                      <Globe className="w-5 h-5 text-blue-600 mr-3 mt-0.5" />
                      <div>
                        <h4 className="font-medium text-blue-800 mb-2">고객용 페이지 URL</h4>
                        <p className="text-sm text-blue-600 mb-3">
                          고객들이 리뷰를 작성할 수 있는 페이지 주소입니다. 이 URL을 고객들과 공유하세요.
                        </p>
                        <div className="bg-white border border-blue-200 rounded p-3 mb-3">
                          <code className="text-blue-800 text-sm break-all">
                            {typeof window !== 'undefined' ? `${window.location.origin}/customer-review/demo-store-123` : '/customer-review/demo-store-123'}
                          </code>
                        </div>
                        <div className="flex space-x-2">
                          <Button
                            size="sm"
                            onClick={copyCustomerUrl}
                            variant={urlCopied ? "default" : "outline"}
                            disabled={urlCopied}
                          >
                            {urlCopied ? (
                              <>
                                <Check className="w-4 h-4 mr-1" />
                                복사됨!
                              </>
                            ) : (
                              <>
                                <Copy className="w-4 h-4 mr-1" />
                                URL 복사
                              </>
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              const url = `${window.location.origin}/customer-review/demo-store-123`
                              window.open(url, '_blank')
                            }}
                          >
                            <ExternalLink className="w-4 h-4 mr-1" />
                            페이지 열기
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 템플릿 관리 */}
          <TabsContent value="templates" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">리뷰 템플릿</h3>
                <p className="text-sm text-muted-foreground">
                  다양한 상황에 맞는 리뷰 템플릿을 관리하세요
                </p>
              </div>
              <Button onClick={addTemplate}>
                <Plus className="w-4 h-4 mr-2" />
                템플릿 추가
              </Button>
            </div>

            <div className="space-y-4">
              {(settings.templates || []).map((template) => (
                <Card key={template.id}>
                  <CardContent className="p-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Input
                          value={template.name}
                          onChange={(e) => updateTemplate(template.id, { name: e.target.value })}
                          className="font-medium"
                          placeholder="템플릿 이름"
                        />
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={template.isActive}
                            onCheckedChange={(checked) => 
                              updateTemplate(template.id, { isActive: checked })
                            }
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeTemplate(template.id)}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>

                      <Textarea
                        value={template.content}
                        onChange={(e) => updateTemplate(template.id, { content: e.target.value })}
                        placeholder="리뷰 템플릿 내용을 입력하세요..."
                        rows={3}
                      />

                      <div className="grid grid-cols-3 gap-4">
                        <Select
                          value={template.tone}
                          onValueChange={(value: any) => 
                            updateTemplate(template.id, { tone: value })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="friendly">친근한 톤</SelectItem>
                            <SelectItem value="professional">전문적인 톤</SelectItem>
                            <SelectItem value="casual">캐주얼한 톤</SelectItem>
                            <SelectItem value="enthusiastic">열정적인 톤</SelectItem>
                          </SelectContent>
                        </Select>

                        <div className="space-y-1">
                          <Label className="text-xs">최소 글자</Label>
                          <Input
                            type="text"
                            value={template.minLength}
                            onChange={(e) => {
                              const value = e.target.value
                              if (value === '' || /^\d+$/.test(value)) {
                                const numValue = value === '' ? 0 : parseInt(value)
                                if (numValue <= 500) {
                                  updateTemplate(template.id, { minLength: numValue })
                                }
                              }
                            }}
                            onBlur={(e) => {
                              const value = parseInt(e.target.value) || 10
                              if (value < 10) {
                                updateTemplate(template.id, { minLength: 10 })
                              }
                            }}
                            placeholder="10"
                          />
                        </div>

                        <div className="space-y-1">
                          <Label className="text-xs">최대 글자</Label>
                          <Input
                            type="text"
                            value={template.maxLength}
                            onChange={(e) => {
                              const value = e.target.value
                              if (value === '' || /^\d+$/.test(value)) {
                                const numValue = value === '' ? 0 : parseInt(value)
                                if (numValue <= 1000) {
                                  updateTemplate(template.id, { maxLength: numValue })
                                }
                              }
                            }}
                            onBlur={(e) => {
                              const value = parseInt(e.target.value) || template.minLength + 10
                              const minRequired = Math.max(template.minLength + 10, 50)
                              if (value < minRequired) {
                                updateTemplate(template.id, { maxLength: minRequired })
                              }
                            }}
                            placeholder="200"
                          />
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {(template.keywords || []).map((keyword) => (
                          <Badge key={keyword} variant="secondary">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* 키워드 설정 */}
          <TabsContent value="keywords" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 긍정 키워드 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Target className="w-5 h-5 mr-2 text-green-600" />
                    긍정 키워드
                  </CardTitle>
                  <CardDescription>
                    전반적인 긍정적 평가에 사용할 키워드
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex space-x-2">
                    <Input
                      value={newKeyword}
                      onChange={(e) => setNewKeyword(e.target.value)}
                      placeholder="긍정 키워드 입력 (예: 맛있다, 좋다)"
                      onKeyPress={(e) => e.key === 'Enter' && addPositiveKeyword()}
                    />
                    <Button onClick={addPositiveKeyword} size="icon">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(settings.positiveKeywords || []).map((keyword) => (
                      <Badge key={keyword} variant="default" className="cursor-pointer bg-green-100 text-green-800 hover:bg-green-200">
                        {keyword}
                        <X 
                          className="w-3 h-3 ml-1"
                          onClick={() => removePositiveKeyword(keyword)}
                        />
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 메뉴 키워드 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <MessageSquare className="w-5 h-5 mr-2 text-orange-600" />
                    메뉴 키워드
                  </CardTitle>
                  <CardDescription>
                    음식과 메뉴 관련 키워드
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex space-x-2">
                    <Input
                      value={newMenuKeyword}
                      onChange={(e) => setNewMenuKeyword(e.target.value)}
                      placeholder="메뉴 키워드 입력 (예: 음식, 맛)"
                      onKeyPress={(e) => e.key === 'Enter' && addMenuKeyword()}
                    />
                    <Button onClick={addMenuKeyword} size="icon">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(settings.menuKeywords || []).map((keyword) => (
                      <Badge key={keyword} variant="secondary" className="cursor-pointer bg-orange-100 text-orange-800 hover:bg-orange-200">
                        {keyword}
                        <X 
                          className="w-3 h-3 ml-1"
                          onClick={() => removeMenuKeyword(keyword)}
                        />
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 서비스 키워드 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Heart className="w-5 h-5 mr-2 text-blue-600" />
                    서비스 키워드
                  </CardTitle>
                  <CardDescription>
                    직원 서비스와 응대 관련 키워드
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex space-x-2">
                    <Input
                      value={newServiceKeyword}
                      onChange={(e) => setNewServiceKeyword(e.target.value)}
                      placeholder="서비스 키워드 입력 (예: 친절, 응대)"
                      onKeyPress={(e) => e.key === 'Enter' && addServiceKeyword()}
                    />
                    <Button onClick={addServiceKeyword} size="icon">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(settings.serviceKeywords || []).map((keyword) => (
                      <Badge key={keyword} variant="secondary" className="cursor-pointer bg-blue-100 text-blue-800 hover:bg-blue-200">
                        {keyword}
                        <X 
                          className="w-3 h-3 ml-1"
                          onClick={() => removeServiceKeyword(keyword)}
                        />
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 분위기 키워드 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Palette className="w-5 h-5 mr-2 text-purple-600" />
                    분위기 키워드
                  </CardTitle>
                  <CardDescription>
                    매장 분위기와 인테리어 관련 키워드
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex space-x-2">
                    <Input
                      value={newAtmosphereKeyword}
                      onChange={(e) => setNewAtmosphereKeyword(e.target.value)}
                      placeholder="분위기 키워드 입력 (예: 분위기, 인테리어)"
                      onKeyPress={(e) => e.key === 'Enter' && addAtmosphereKeyword()}
                    />
                    <Button onClick={addAtmosphereKeyword} size="icon">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(settings.atmosphereKeywords || []).map((keyword) => (
                      <Badge key={keyword} variant="secondary" className="cursor-pointer bg-purple-100 text-purple-800 hover:bg-purple-200">
                        {keyword}
                        <X 
                          className="w-3 h-3 ml-1"
                          onClick={() => removeAtmosphereKeyword(keyword)}
                        />
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* 제외 단어 섹션 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <X className="w-5 h-5 mr-2 text-red-600" />
                  제외 단어
                </CardTitle>
                <CardDescription>
                  리뷰에서 피해야 할 단어를 설정하세요
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex space-x-2">
                  <Input
                    value={newExcludeWord}
                    onChange={(e) => setNewExcludeWord(e.target.value)}
                    placeholder="제외할 단어 입력 (예: 별로, 실망)"
                    onKeyPress={(e) => e.key === 'Enter' && addExcludeWord()}
                  />
                  <Button onClick={addExcludeWord} size="icon">
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(settings.excludeWords || []).map((word) => (
                    <Badge key={word} variant="destructive" className="cursor-pointer">
                      {word}
                      <X 
                        className="w-3 h-3 ml-1"
                        onClick={() => removeExcludeWord(word)}
                      />
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 고급 설정 */}
          <TabsContent value="advanced" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>고급 설정</CardTitle>
                <CardDescription>
                  세부적인 리뷰 생성 옵션을 설정합니다
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex">
                    <Lightbulb className="w-5 h-5 text-blue-600 mr-3 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-blue-800">AI 학습 기능</h4>
                      <p className="text-sm text-blue-600 mt-1">
                        고객이 실제로 선택한 리뷰와 수정 내용을 분석하여 더 나은 초안을 생성합니다.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <Label className="text-base font-medium">개인정보 수집 동의 문구</Label>
                  <Textarea
                    placeholder="고객에게 표시할 개인정보 수집 동의 문구를 입력하세요..."
                    rows={4}
                    defaultValue="리뷰 초안 생성을 위해 카카오톡 정보 수집에 동의합니다. 수집된 정보는 마케팅 목적으로만 사용되며, 언제든지 철회할 수 있습니다."
                  />
                </div>

                <div className="space-y-4">
                  <Label className="text-base font-medium">QR 코드 랜딩 페이지 메시지</Label>
                  <Textarea
                    placeholder="고객이 QR 코드를 스캔했을 때 보여줄 환영 메시지를 입력하세요..."
                    rows={3}
                    defaultValue="안녕하세요! 저희 매장을 방문해 주셔서 감사합니다. 리뷰 작성을 도와드리겠습니다."
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  )
}