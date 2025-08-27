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
import { 
  Settings, 
  Save, 
  Plus, 
  X, 
  MessageSquare,
  Bot,
  Clock,
  AlertTriangle,
  CheckCircle,
  Store,
  Loader2,
  RefreshCw
} from 'lucide-react'

interface Store {
  id: string
  store_name: string
  platform: string
  platform_store_id: string
  autoReplyEnabled: boolean
  replyTone: string
  minReplyLength: number
  maxReplyLength: number
  brandVoice: string
  greetingTemplate: string
  closingTemplate: string
  seoKeywords: string[]
  autoApprovalDelayHours: number
}

interface ReplySettings {
  autoReplyEnabled: boolean
  replyTone: 'friendly' | 'formal' | 'casual'
  minReplyLength: number
  maxReplyLength: number
  brandVoice: string
  greetingTemplate: string
  closingTemplate: string
  seoKeywords: string[]
  autoApprovalDelayHours: number
}

export default function ReplySettingsPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)
  const [loadingStores, setLoadingStores] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [stores, setStores] = useState<Store[]>([])
  const [selectedStore, setSelectedStore] = useState<Store | null>(null)
  const [newKeyword, setNewKeyword] = useState('')
  
  const [settings, setSettings] = useState<ReplySettings>({
    autoReplyEnabled: false,
    replyTone: 'friendly',
    minReplyLength: 50,
    maxReplyLength: 200,
    brandVoice: '',
    greetingTemplate: '',
    closingTemplate: '',
    seoKeywords: [],
    autoApprovalDelayHours: 48
  })

  // 사용자의 매장 목록 로드
  const loadStores = async () => {
    if (!user?.id) return
    
    setLoadingStores(true)
    try {
      const response = await fetch(`http://localhost:8002/api/user-stores/${user.id}`)
      const data = await response.json()
      
      if (data.success && data.stores) {
        setStores(data.stores)
        // 첫 번째 매장을 자동 선택
        if (data.stores.length > 0) {
          selectStore(data.stores[0])
        }
      }
    } catch (error) {
      console.error('매장 목록 로드 실패:', error)
    } finally {
      setLoadingStores(false)
    }
  }

  // 매장 선택 및 설정 로드
  const selectStore = async (store: Store) => {
    setSelectedStore(store)
    setLoading(true)
    
    try {
      const response = await fetch(`http://localhost:8002/api/reply-settings/${store.id}`)
      const data = await response.json()
      
      if (data.success && data.settings) {
        setSettings(data.settings)
      }
    } catch (error) {
      console.error('매장 설정 로드 실패:', error)
      // 매장 데이터에서 기본값 설정
      setSettings({
        autoReplyEnabled: store.autoReplyEnabled,
        replyTone: store.replyTone as 'friendly' | 'formal' | 'casual',
        minReplyLength: store.minReplyLength,
        maxReplyLength: store.maxReplyLength,
        brandVoice: store.brandVoice,
        greetingTemplate: store.greetingTemplate,
        closingTemplate: store.closingTemplate,
        seoKeywords: store.seoKeywords,
        autoApprovalDelayHours: store.autoApprovalDelayHours
      })
    } finally {
      setLoading(false)
    }
  }

  // 설정 저장
  const handleSave = async () => {
    if (!selectedStore) return
    
    setSaving(true)
    try {
      const response = await fetch(`http://localhost:8002/api/reply-settings/${selectedStore.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
      })
      
      const data = await response.json()
      
      if (data.success) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
        // 매장 목록 새로고침
        loadStores()
      } else {
        alert('설정 저장에 실패했습니다.')
      }
    } catch (error) {
      console.error('설정 저장 실패:', error)
      alert('설정 저장 중 오류가 발생했습니다.')
    } finally {
      setSaving(false)
    }
  }

  // 키워드 추가
  const addKeyword = () => {
    if (newKeyword.trim() && !settings.seoKeywords.includes(newKeyword.trim())) {
      setSettings(prev => ({
        ...prev,
        seoKeywords: [...prev.seoKeywords, newKeyword.trim()]
      }))
      setNewKeyword('')
    }
  }

  // 키워드 제거
  const removeKeyword = (keyword: string) => {
    setSettings(prev => ({
      ...prev,
      seoKeywords: prev.seoKeywords.filter(k => k !== keyword)
    }))
  }

  // 플랫폼 아이콘
  const getPlatformBadge = (platform: string) => {
    const colors = {
      naver: 'bg-green-100 text-green-800',
      baemin: 'bg-blue-100 text-blue-800', 
      yogiyo: 'bg-orange-100 text-orange-800',
      coupangeats: 'bg-purple-100 text-purple-800'
    }
    
    const names = {
      naver: '네이버',
      baemin: '배민',
      yogiyo: '요기요', 
      coupangeats: '쿠팡이츠'
    }
    
    return (
      <Badge className={colors[platform as keyof typeof colors] || 'bg-gray-100 text-gray-800'}>
        {names[platform as keyof typeof names] || platform}
      </Badge>
    )
  }

  // 답글 톤 예시
  const getToneExample = (tone: string) => {
    const examples = {
      friendly: '안녕하세요! 소중한 리뷰 남겨주셔서 정말 감사합니다 😊 앞으로도 더욱 맛있는 음식과 친절한 서비스로 보답하겠습니다!',
      formal: '안녕하세요. 귀하의 소중한 리뷰에 깊이 감사드립니다. 앞으로도 품질 높은 서비스를 제공하도록 최선을 다하겠습니다.',
      casual: '와! 리뷰 고마워요~ 다음에도 또 놀러와 주세요! 더 맛있게 해드릴게요 ㅎㅎ'
    }
    return examples[tone as keyof typeof examples] || ''
  }

  useEffect(() => {
    loadStores()
  }, [user])

  if (loadingStores) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto p-6">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
              <p>매장 목록을 불러오는 중...</p>
            </div>
          </div>
        </div>
      </AppLayout>
    )
  }

  if (stores.length === 0) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto p-6">
          <div className="text-center py-12">
            <Store className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h2 className="text-xl font-semibold mb-2">등록된 매장이 없습니다</h2>
            <p className="text-gray-600 mb-4">먼저 플랫폼 연결을 통해 매장을 등록해 주세요.</p>
            <Button>플랫폼 연결하기</Button>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold brand-text">매장별 답글 설정</h1>
            <p className="text-muted-foreground">
              각 매장별로 AI 답글 설정을 관리하세요
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              onClick={loadStores}
              disabled={loadingStores}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              새로고침
            </Button>
            <Button 
              onClick={handleSave} 
              disabled={saving || !selectedStore}
              className="relative"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              {saving ? '저장 중...' : '설정 저장'}
              {saved && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-ping" />
              )}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* 매장 목록 (왼쪽) */}
          <div className="col-span-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Store className="w-5 h-5 mr-2" />
                  내 매장 목록
                </CardTitle>
                <CardDescription>
                  설정을 변경할 매장을 선택하세요
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="space-y-1">
                  {stores.map((store) => (
                    <div
                      key={store.id}
                      className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors border-l-4 ${
                        selectedStore?.id === store.id 
                          ? 'bg-blue-50 border-l-blue-500' 
                          : 'border-l-transparent'
                      }`}
                      onClick={() => selectStore(store)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium">{store.store_name}</h3>
                        {getPlatformBadge(store.platform)}
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        ID: {store.platform_store_id}
                      </p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">
                          AI 답글
                        </span>
                        <Badge variant={store.autoReplyEnabled ? "default" : "secondary"}>
                          {store.autoReplyEnabled ? "ON" : "OFF"}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 설정 패널 (오른쪽) */}
          <div className="col-span-8">
            {selectedStore ? (
              <div className="space-y-6">
                {loading ? (
                  <Card>
                    <CardContent className="p-12">
                      <div className="text-center">
                        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
                        <p>설정을 불러오는 중...</p>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <>
                    {/* 기본 설정 */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center">
                          <Bot className="w-5 h-5 mr-2" />
                          {selectedStore.store_name} 기본 설정
                        </CardTitle>
                        <CardDescription>
                          AI 답글 자동화 및 기본 동작 설정
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>AI 답글 자동화 활성화</Label>
                            <p className="text-sm text-muted-foreground">
                              새로운 리뷰에 대해 AI가 자동으로 답글을 생성합니다
                            </p>
                          </div>
                          <Switch
                            checked={settings.autoReplyEnabled}
                            onCheckedChange={(checked) => 
                              setSettings(prev => ({ ...prev, autoReplyEnabled: checked }))
                            }
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>답글 톤앤매너</Label>
                            <Select
                              value={settings.replyTone}
                              onValueChange={(value: any) => 
                                setSettings(prev => ({ ...prev, replyTone: value }))
                              }
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="friendly">친근함</SelectItem>
                                <SelectItem value="formal">정중함</SelectItem>
                                <SelectItem value="casual">캐주얼</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>자동 승인 대기 시간</Label>
                            <Select
                              value={settings.autoApprovalDelayHours.toString()}
                              onValueChange={(value) => 
                                setSettings(prev => ({ 
                                  ...prev, 
                                  autoApprovalDelayHours: parseInt(value) 
                                }))
                              }
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="24">24시간</SelectItem>
                                <SelectItem value="48">48시간</SelectItem>
                                <SelectItem value="72">72시간</SelectItem>
                                <SelectItem value="168">1주일</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>최소 답글 길이 (글자수)</Label>
                            <Input
                              type="number"
                              value={settings.minReplyLength}
                              onChange={(e) => 
                                setSettings(prev => ({ 
                                  ...prev, 
                                  minReplyLength: parseInt(e.target.value) || 0 
                                }))
                              }
                              min="10"
                              max="500"
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>최대 답글 길이 (글자수)</Label>
                            <Input
                              type="number"
                              value={settings.maxReplyLength}
                              onChange={(e) => 
                                setSettings(prev => ({ 
                                  ...prev, 
                                  maxReplyLength: parseInt(e.target.value) || 0 
                                }))
                              }
                              min="50"
                              max="1000"
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* 답글 톤 미리보기 */}
                    <Card>
                      <CardHeader>
                        <CardTitle>답글 톤 미리보기</CardTitle>
                        <CardDescription>
                          선택한 톤에 따른 답글 예시를 확인하세요
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <p className="text-sm leading-relaxed">
                            {getToneExample(settings.replyTone)}
                          </p>
                        </div>
                      </CardContent>
                    </Card>

                    {/* 브랜드 보이스 및 템플릿 */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center">
                          <MessageSquare className="w-5 h-5 mr-2" />
                          브랜드 보이스 및 인사말 설정
                        </CardTitle>
                        <CardDescription>
                          매장의 특색과 개성이 드러나는 답글을 위한 설정
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        <div className="space-y-2">
                          <Label>브랜드 보이스</Label>
                          <Textarea
                            value={settings.brandVoice}
                            onChange={(e) => 
                              setSettings(prev => ({ ...prev, brandVoice: e.target.value }))
                            }
                            placeholder="예: 20년 전통의 정성 담긴 가정식 맛집으로, 손님을 가족처럼 대하는 따뜻한 서비스..."
                            rows={3}
                          />
                          <p className="text-sm text-muted-foreground">
                            매장의 특징과 개성을 설명해 주세요. AI가 이를 바탕으로 자연스러운 답글을 생성합니다.
                          </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>첫인사 템플릿 (선택사항)</Label>
                            <Input
                              value={settings.greetingTemplate}
                              onChange={(e) => 
                                setSettings(prev => ({ ...prev, greetingTemplate: e.target.value }))
                              }
                              placeholder="예: 안녕하세요! {store_name}입니다 😊"
                            />
                            <p className="text-sm text-muted-foreground">
                              비워두면 AI가 자연스럽게 생성합니다
                            </p>
                          </div>

                          <div className="space-y-2">
                            <Label>마무리인사 템플릿 (선택사항)</Label>
                            <Input
                              value={settings.closingTemplate}
                              onChange={(e) => 
                                setSettings(prev => ({ ...prev, closingTemplate: e.target.value }))
                              }
                              placeholder="예: 감사합니다. 또 방문해주세요! 🙏"
                            />
                            <p className="text-sm text-muted-foreground">
                              비워두면 AI가 자연스럽게 생성합니다
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* SEO 키워드 */}
                    <Card>
                      <CardHeader>
                        <CardTitle>SEO 키워드 관리</CardTitle>
                        <CardDescription>
                          답글에 자연스럽게 포함할 키워드를 관리하세요
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex items-center space-x-2">
                          <Input
                            value={newKeyword}
                            onChange={(e) => setNewKeyword(e.target.value)}
                            placeholder="키워드 입력"
                            onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
                            className="flex-1"
                          />
                          <Button onClick={addKeyword}>
                            <Plus className="w-4 h-4" />
                          </Button>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {settings.seoKeywords.map((keyword) => (
                            <Badge 
                              key={keyword} 
                              variant="secondary"
                              className="cursor-pointer"
                            >
                              {keyword}
                              <X 
                                className="w-3 h-3 ml-1"
                                onClick={() => removeKeyword(keyword)}
                              />
                            </Badge>
                          ))}
                        </div>

                        {settings.seoKeywords.length === 0 && (
                          <p className="text-sm text-gray-500">
                            아직 등록된 키워드가 없습니다. 매장의 특징을 나타내는 키워드를 추가해 보세요.
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  </>
                )}
              </div>
            ) : (
              <Card>
                <CardContent className="p-12">
                  <div className="text-center">
                    <Settings className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                    <h2 className="text-xl font-semibold mb-2">매장을 선택해 주세요</h2>
                    <p className="text-gray-600">
                      왼쪽에서 설정을 변경할 매장을 선택하세요.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}