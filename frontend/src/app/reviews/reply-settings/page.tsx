"use client"

import { useState } from 'react'
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
  MessageSquare,
  Bot,
  Clock,
  AlertTriangle,
  CheckCircle,
  Eye,
  Trash2,
  Edit3
} from 'lucide-react'

interface ReplyTemplate {
  id: string
  name: string
  content: string
  sentiment: 'positive' | 'negative' | 'neutral'
  rating: number[]
  isActive: boolean
  useFrequency: number
}

interface AutoReplySettings {
  enabled: boolean
  businessHours: {
    start: string
    end: string
  }
  delayMinutes: number
  requireApproval: {
    negative: boolean
    complaints: boolean
    questions: boolean
  }
  waitingPeriod: number // 사장님 확인 대기 기간 (시간)
  notificationEnabled: boolean
  templates: ReplyTemplate[]
  keywords: {
    positive: string[]
    negative: string[]
    neutral: string[]
    questions: string[]
    complaints: string[]
  }
}

export default function ReplySettingsPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [newKeyword, setNewKeyword] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<keyof typeof settings.keywords>('positive')
  
  const [settings, setSettings] = useState<AutoReplySettings>({
    enabled: true,
    businessHours: {
      start: '08:00',
      end: '22:00'
    },
    delayMinutes: 30,
    requireApproval: {
      negative: true,
      complaints: true,
      questions: true
    },
    waitingPeriod: 48,
    notificationEnabled: true,
    templates: [
      {
        id: '1',
        name: '긍정 리뷰 기본 답글',
        content: '소중한 리뷰 남겨주셔서 감사합니다! 앞으로도 더 좋은 서비스로 보답하겠습니다. 언제든 다시 방문해주세요!',
        sentiment: 'positive',
        rating: [4, 5],
        isActive: true,
        useFrequency: 85
      },
      {
        id: '2',
        name: '보통 리뷰 답글',
        content: '방문해주셔서 감사합니다. 고객님의 소중한 의견을 반영하여 더 나은 서비스를 제공하도록 노력하겠습니다.',
        sentiment: 'neutral',
        rating: [3],
        isActive: true,
        useFrequency: 45
      },
      {
        id: '3',
        name: '부정 리뷰 답글',
        content: '불편을 끼쳐드려 죄송합니다. 고객님의 소중한 의견을 바탕으로 개선하겠습니다. 언제든 연락 주시면 성심성의껏 도움드리겠습니다.',
        sentiment: 'negative',
        rating: [1, 2],
        isActive: true,
        useFrequency: 20
      }
    ],
    keywords: {
      positive: ['맛있다', '친절하다', '깔끔하다', '좋다', '추천', '만족'],
      negative: ['별로', '실망', '불친절', '더럽다', '비싸다', '늦다'],
      neutral: ['보통', '괜찮다', '그럭저럭', '적당하다'],
      questions: ['문의', '질문', '언제', '어디서', '얼마', '?'],
      complaints: ['환불', '취소', '클레임', '불만', '신고', '항의']
    }
  })

  const handleSave = async () => {
    setLoading(true)
    try {
      // API 호출 로직
      await new Promise(resolve => setTimeout(resolve, 1000))
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('설정 저장 실패:', error)
    } finally {
      setLoading(false)
    }
  }

  const addKeyword = () => {
    if (newKeyword.trim() && !settings.keywords[selectedCategory].includes(newKeyword.trim())) {
      setSettings(prev => ({
        ...prev,
        keywords: {
          ...prev.keywords,
          [selectedCategory]: [...prev.keywords[selectedCategory], newKeyword.trim()]
        }
      }))
      setNewKeyword('')
    }
  }

  const removeKeyword = (category: keyof typeof settings.keywords, keyword: string) => {
    setSettings(prev => ({
      ...prev,
      keywords: {
        ...prev.keywords,
        [category]: prev.keywords[category].filter(k => k !== keyword)
      }
    }))
  }

  const addTemplate = () => {
    const newTemplate: ReplyTemplate = {
      id: Date.now().toString(),
      name: '새 템플릿',
      content: '',
      sentiment: 'positive',
      rating: [5],
      isActive: true,
      useFrequency: 0
    }
    setSettings(prev => ({
      ...prev,
      templates: [...prev.templates, newTemplate]
    }))
  }

  const updateTemplate = (id: string, updates: Partial<ReplyTemplate>) => {
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

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'bg-green-100 text-green-800'
      case 'negative': return 'bg-red-100 text-red-800'
      case 'neutral': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getSentimentLabel = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return '긍정'
      case 'negative': return '부정'
      case 'neutral': return '중립'
      default: return '기타'
    }
  }

  const getKeywordCategoryColor = (category: string) => {
    switch (category) {
      case 'positive': return 'bg-green-100 text-green-800'
      case 'negative': return 'bg-red-100 text-red-800'
      case 'neutral': return 'bg-gray-100 text-gray-800'
      case 'questions': return 'bg-blue-100 text-blue-800'
      case 'complaints': return 'bg-orange-100 text-orange-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold brand-text">사장님 답글 설정</h1>
            <p className="text-muted-foreground">
              AI가 자동으로 생성할 답글의 규칙과 템플릿을 설정하세요
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
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="basic">기본 설정</TabsTrigger>
            <TabsTrigger value="templates">답글 템플릿</TabsTrigger>
            <TabsTrigger value="keywords">키워드 관리</TabsTrigger>
            <TabsTrigger value="automation">자동화 규칙</TabsTrigger>
          </TabsList>

          {/* 기본 설정 */}
          <TabsContent value="basic" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Bot className="w-5 h-5 mr-2" />
                  AI 답글 자동화
                </CardTitle>
                <CardDescription>
                  AI가 자동으로 답글을 생성하고 게시하는 기본 설정입니다
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>AI 답글 자동화 활성화</Label>
                    <p className="text-sm text-muted-foreground">
                      새로운 리뷰에 대해 AI가 자동으로 답글을 생성하고 게시합니다
                    </p>
                  </div>
                  <Switch
                    checked={settings.enabled}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({ ...prev, enabled: checked }))
                    }
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label>운영 시간 - 시작</Label>
                    <Input
                      type="time"
                      value={settings.businessHours.start}
                      onChange={(e) => 
                        setSettings(prev => ({
                          ...prev,
                          businessHours: { ...prev.businessHours, start: e.target.value }
                        }))
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>운영 시간 - 종료</Label>
                    <Input
                      type="time"
                      value={settings.businessHours.end}
                      onChange={(e) => 
                        setSettings(prev => ({
                          ...prev,
                          businessHours: { ...prev.businessHours, end: e.target.value }
                        }))
                      }
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>답글 생성 지연 시간 (분)</Label>
                  <Select
                    value={settings.delayMinutes.toString()}
                    onValueChange={(value) => 
                      setSettings(prev => ({ ...prev, delayMinutes: parseInt(value) }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">즉시</SelectItem>
                      <SelectItem value="15">15분</SelectItem>
                      <SelectItem value="30">30분</SelectItem>
                      <SelectItem value="60">1시간</SelectItem>
                      <SelectItem value="120">2시간</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground">
                    리뷰가 등록된 후 답글을 생성하기까지의 지연 시간을 설정합니다
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>사장님 확인 대기 시간 (시간)</Label>
                  <Select
                    value={settings.waitingPeriod.toString()}
                    onValueChange={(value) => 
                      setSettings(prev => ({ ...prev, waitingPeriod: parseInt(value) }))
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
                  <p className="text-sm text-muted-foreground">
                    승인이 필요한 답글을 사장님이 확인할 수 있는 시간입니다. 이 시간이 지나면 자동으로 게시됩니다.
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>알림 메시지 활성화</Label>
                    <p className="text-sm text-muted-foreground">
                      중요한 리뷰나 답글 승인이 필요할 때 알림톡을 보냅니다
                    </p>
                  </div>
                  <Switch
                    checked={settings.notificationEnabled}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({ ...prev, notificationEnabled: checked }))
                    }
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 답글 템플릿 */}
          <TabsContent value="templates" className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">답글 템플릿 관리</h3>
                <p className="text-sm text-muted-foreground">
                  다양한 상황에 맞는 답글 템플릿을 관리하세요
                </p>
              </div>
              <Button onClick={addTemplate}>
                <Plus className="w-4 h-4 mr-2" />
                템플릿 추가
              </Button>
            </div>

            <div className="space-y-4">
              {settings.templates.map((template) => (
                <Card key={template.id}>
                  <CardContent className="p-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <Input
                            value={template.name}
                            onChange={(e) => updateTemplate(template.id, { name: e.target.value })}
                            className="font-medium"
                            placeholder="템플릿 이름"
                          />
                          <Badge className={getSentimentColor(template.sentiment)}>
                            {getSentimentLabel(template.sentiment)}
                          </Badge>
                          <Badge variant="outline">
                            사용률 {template.useFrequency}%
                          </Badge>
                        </div>
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
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>

                      <Textarea
                        value={template.content}
                        onChange={(e) => updateTemplate(template.id, { content: e.target.value })}
                        placeholder="답글 템플릿 내용을 입력하세요..."
                        rows={3}
                      />

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>감정 분류</Label>
                          <Select
                            value={template.sentiment}
                            onValueChange={(value: any) => 
                              updateTemplate(template.id, { sentiment: value })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="positive">긍정</SelectItem>
                              <SelectItem value="neutral">중립</SelectItem>
                              <SelectItem value="negative">부정</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label>적용할 별점</Label>
                          <div className="flex space-x-1">
                            {[1, 2, 3, 4, 5].map((rating) => (
                              <Button
                                key={rating}
                                variant={template.rating.includes(rating) ? "default" : "outline"}
                                size="sm"
                                onClick={() => {
                                  const newRating = template.rating.includes(rating)
                                    ? template.rating.filter(r => r !== rating)
                                    : [...template.rating, rating]
                                  updateTemplate(template.id, { rating: newRating })
                                }}
                              >
                                {rating}★
                              </Button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* 키워드 관리 */}
          <TabsContent value="keywords" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>키워드 기반 답글 분류</CardTitle>
                <CardDescription>
                  리뷰 내용의 키워드를 분석하여 적절한 답글 템플릿을 선택합니다
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center space-x-4">
                  <div className="flex-1">
                    <Select value={selectedCategory} onValueChange={(value: any) => setSelectedCategory(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="positive">긍정 키워드</SelectItem>
                        <SelectItem value="negative">부정 키워드</SelectItem>
                        <SelectItem value="neutral">중립 키워드</SelectItem>
                        <SelectItem value="questions">질문 키워드</SelectItem>
                        <SelectItem value="complaints">클레임 키워드</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
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

                <div className="space-y-4">
                  {Object.entries(settings.keywords).map(([category, keywords]) => (
                    <div key={category} className="space-y-2">
                      <Label className="capitalize">{category} 키워드</Label>
                      <div className="flex flex-wrap gap-2">
                        {keywords.map((keyword) => (
                          <Badge 
                            key={keyword} 
                            className={`cursor-pointer ${getKeywordCategoryColor(category)}`}
                          >
                            {keyword}
                            <X 
                              className="w-3 h-3 ml-1"
                              onClick={() => removeKeyword(category as keyof typeof settings.keywords, keyword)}
                            />
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 자동화 규칙 */}
          <TabsContent value="automation" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <AlertTriangle className="w-5 h-5 mr-2" />
                  사장님 승인 필요 조건
                </CardTitle>
                <CardDescription>
                  어떤 상황에서 사장님의 승인을 받을지 설정합니다
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>부정적인 리뷰</Label>
                    <p className="text-sm text-muted-foreground">
                      1-2점 리뷰나 부정 키워드가 포함된 리뷰
                    </p>
                  </div>
                  <Switch
                    checked={settings.requireApproval.negative}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({
                        ...prev,
                        requireApproval: { ...prev.requireApproval, negative: checked }
                      }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>클레임성 리뷰</Label>
                    <p className="text-sm text-muted-foreground">
                      환불, 취소, 불만 등의 키워드가 포함된 리뷰
                    </p>
                  </div>
                  <Switch
                    checked={settings.requireApproval.complaints}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({
                        ...prev,
                        requireApproval: { ...prev.requireApproval, complaints: checked }
                      }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>질문이 포함된 리뷰</Label>
                    <p className="text-sm text-muted-foreground">
                      고객이 직접적인 질문을 한 리뷰
                    </p>
                  </div>
                  <Switch
                    checked={settings.requireApproval.questions}
                    onCheckedChange={(checked) => 
                      setSettings(prev => ({
                        ...prev,
                        requireApproval: { ...prev.requireApproval, questions: checked }
                      }))
                    }
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Clock className="w-5 h-5 mr-2" />
                  운영 시간 및 지연 설정
                </CardTitle>
                <CardDescription>
                  답글 자동화의 시간 관련 설정을 관리합니다
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex">
                    <MessageSquare className="w-5 h-5 text-blue-600 mr-3 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-blue-800">자동화 운영 시간</h4>
                      <p className="text-sm text-blue-600 mt-1">
                        설정한 운영 시간 ({settings.businessHours.start} - {settings.businessHours.end}) 내에서만 
                        답글이 자동으로 게시됩니다. 운영 시간 외에는 답글이 생성되어 대기 상태가 됩니다.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <div className="flex">
                    <Clock className="w-5 h-5 text-orange-600 mr-3 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-orange-800">답글 지연 시간</h4>
                      <p className="text-sm text-orange-600 mt-1">
                        현재 {settings.delayMinutes}분 지연으로 설정되어 있습니다. 
                        즉시 답글이 달리는 것을 방지하여 더 자연스러운 답글 타이밍을 제공합니다.
                      </p>
                    </div>
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