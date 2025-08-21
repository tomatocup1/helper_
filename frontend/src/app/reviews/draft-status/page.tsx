"use client"

import { useState, useEffect } from 'react'
import { useAuth } from '@/store/auth-store-supabase'
import AppLayout from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  MoreHorizontal,
  Search,
  Filter,
  Download,
  Eye,
  Edit,
  Trash2,
  MessageSquare,
  User,
  Calendar,
  TrendingUp
} from 'lucide-react'

interface ReviewDraft {
  id: string
  customerName: string
  customerPhone: string
  storeName: string
  content: string
  status: 'pending' | 'approved' | 'rejected' | 'used'
  createdAt: string
  approvedAt?: string
  usedAt?: string
  template: string
  tone: 'friendly' | 'professional' | 'casual' | 'enthusiastic'
  keywords: string[]
  rating?: number
  platform: 'naver' | 'google' | 'kakao'
}

const mockDrafts: ReviewDraft[] = [
  {
    id: '1',
    customerName: '김*수',
    customerPhone: '010-****-1234',
    storeName: '맛있는 김치찌개집',
    content: '정말 맛있게 잘 먹었습니다! 김치찌개가 정말 깊은 맛이 나고 친절한 서비스에 감사드려요. 다음에도 꼭 방문하겠습니다.',
    status: 'used',
    createdAt: '2024-01-15T10:30:00',
    approvedAt: '2024-01-15T10:32:00',
    usedAt: '2024-01-15T11:45:00',
    template: '일반 칭찬 템플릿',
    tone: 'friendly',
    keywords: ['맛있다', '친절', '재방문'],
    rating: 5,
    platform: 'naver'
  },
  {
    id: '2',
    customerName: '이*영',
    customerPhone: '010-****-5678',
    storeName: '맛있는 김치찌개집',
    content: '분위기가 정말 좋네요! 깔끔하고 아늑한 공간에서 편안하게 식사할 수 있어서 좋았습니다. 음식도 맛있고 직원분들도 친절해요.',
    status: 'approved',
    createdAt: '2024-01-15T14:20:00',
    approvedAt: '2024-01-15T14:25:00',
    template: '분위기 칭찬 템플릿',
    tone: 'professional',
    keywords: ['분위기', '깔끔', '친절'],
    platform: 'google'
  },
  {
    id: '3',
    customerName: '박*민',
    customerPhone: '010-****-9012',
    storeName: '행복한 치킨집',
    content: '치킨이 정말 바삭바삭하고 맛있어요! 양념도 딱 좋고 배달도 빨라서 만족합니다.',
    status: 'pending',
    createdAt: '2024-01-15T16:45:00',
    template: '음식 품질 템플릿',
    tone: 'enthusiastic',
    keywords: ['바삭', '맛있다', '배달'],
    platform: 'naver'
  },
  {
    id: '4',
    customerName: '최*희',
    customerPhone: '010-****-3456',
    storeName: '행복한 치킨집',
    content: '가격 대비 양이 많고 맛도 좋네요. 치킨 소스가 특히 인상적이었습니다.',
    status: 'rejected',
    createdAt: '2024-01-15T18:30:00',
    template: '가성비 템플릿',
    tone: 'casual',
    keywords: ['가성비', '양', '소스'],
    platform: 'kakao'
  }
]

const statusConfig = {
  pending: { label: '승인 대기', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  approved: { label: '승인됨', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  rejected: { label: '거부됨', color: 'bg-red-100 text-red-800', icon: XCircle },
  used: { label: '사용됨', color: 'bg-blue-100 text-blue-800', icon: MessageSquare }
}

const platformConfig = {
  naver: { label: '네이버', color: 'bg-green-100 text-green-800' },
  google: { label: '구글', color: 'bg-blue-100 text-blue-800' },
  kakao: { label: '카카오', color: 'bg-yellow-100 text-yellow-800' }
}

export default function ReviewDraftStatusPage() {
  const { user } = useAuth()
  const [drafts, setDrafts] = useState<ReviewDraft[]>(mockDrafts)
  const [filteredDrafts, setFilteredDrafts] = useState<ReviewDraft[]>(mockDrafts)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedDraft, setSelectedDraft] = useState<ReviewDraft | null>(null)

  // 필터링 로직
  useEffect(() => {
    let filtered = drafts

    if (searchTerm) {
      filtered = filtered.filter(draft => 
        draft.customerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        draft.storeName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        draft.content.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(draft => draft.status === statusFilter)
    }

    setFilteredDrafts(filtered)
  }, [drafts, searchTerm, statusFilter])

  const handleApprove = (id: string) => {
    setDrafts(prev => prev.map(draft => 
      draft.id === id 
        ? { ...draft, status: 'approved' as const, approvedAt: new Date().toISOString() }
        : draft
    ))
  }

  const handleReject = (id: string) => {
    setDrafts(prev => prev.map(draft => 
      draft.id === id 
        ? { ...draft, status: 'rejected' as const }
        : draft
    ))
  }

  const handleDelete = (id: string) => {
    setDrafts(prev => prev.filter(draft => draft.id !== id))
  }

  const getStatusCounts = () => {
    return {
      total: drafts.length,
      pending: drafts.filter(d => d.status === 'pending').length,
      approved: drafts.filter(d => d.status === 'approved').length,
      used: drafts.filter(d => d.status === 'used').length,
      rejected: drafts.filter(d => d.status === 'rejected').length
    }
  }

  const statusCounts = getStatusCounts()

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold brand-text">리뷰 초안 현황</h1>
            <p className="text-muted-foreground">
              생성된 리뷰 초안을 관리하고 승인하세요
            </p>
          </div>
          <div className="flex space-x-2">
            <Button variant="outline">
              <Download className="w-4 h-4 mr-2" />
              내보내기
            </Button>
          </div>
        </div>

        {/* 통계 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <MessageSquare className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">전체 초안</p>
                  <p className="text-2xl font-bold">{statusCounts.total}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <Clock className="h-8 w-8 text-yellow-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">승인 대기</p>
                  <p className="text-2xl font-bold">{statusCounts.pending}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <CheckCircle className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">승인됨</p>
                  <p className="text-2xl font-bold">{statusCounts.approved}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <TrendingUp className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">사용됨</p>
                  <p className="text-2xl font-bold">{statusCounts.used}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center">
                <XCircle className="h-8 w-8 text-red-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">거부됨</p>
                  <p className="text-2xl font-bold">{statusCounts.rejected}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 필터 및 검색 */}
        <Card>
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                  <Input
                    placeholder="고객명, 매장명, 리뷰 내용으로 검색..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline">
                    <Filter className="w-4 h-4 mr-2" />
                    상태 필터
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setStatusFilter('all')}>
                    전체
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setStatusFilter('pending')}>
                    승인 대기
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setStatusFilter('approved')}>
                    승인됨
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setStatusFilter('used')}>
                    사용됨
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setStatusFilter('rejected')}>
                    거부됨
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </CardContent>
        </Card>

        {/* 리뷰 초안 목록 */}
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>고객 정보</TableHead>
                <TableHead>매장</TableHead>
                <TableHead>리뷰 내용</TableHead>
                <TableHead>상태</TableHead>
                <TableHead>플랫폼</TableHead>
                <TableHead>생성일</TableHead>
                <TableHead className="text-right">작업</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDrafts.map((draft) => {
                const statusInfo = statusConfig[draft.status]
                const StatusIcon = statusInfo.icon
                const platformInfo = platformConfig[draft.platform]
                
                return (
                  <TableRow key={draft.id}>
                    <TableCell>
                      <div>
                        <div className="flex items-center">
                          <User className="w-4 h-4 mr-2 text-muted-foreground" />
                          <span className="font-medium">{draft.customerName}</span>
                        </div>
                        <p className="text-sm text-muted-foreground">{draft.customerPhone}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="font-medium">{draft.storeName}</span>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-xs">
                        <p className="text-sm truncate">{draft.content}</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {draft.keywords.slice(0, 2).map((keyword) => (
                            <Badge key={keyword} variant="secondary" className="text-xs">
                              {keyword}
                            </Badge>
                          ))}
                          {draft.keywords.length > 2 && (
                            <Badge variant="secondary" className="text-xs">
                              +{draft.keywords.length - 2}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={statusInfo.color}>
                        <StatusIcon className="w-3 h-3 mr-1" />
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={platformInfo.color}>
                        {platformInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center text-sm text-muted-foreground">
                        <Calendar className="w-4 h-4 mr-1" />
                        {new Date(draft.createdAt).toLocaleDateString('ko-KR')}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setSelectedDraft(draft)}>
                            <Eye className="w-4 h-4 mr-2" />
                            자세히 보기
                          </DropdownMenuItem>
                          {draft.status === 'pending' && (
                            <>
                              <DropdownMenuItem onClick={() => handleApprove(draft.id)}>
                                <CheckCircle className="w-4 h-4 mr-2" />
                                승인
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleReject(draft.id)}>
                                <XCircle className="w-4 h-4 mr-2" />
                                거부
                              </DropdownMenuItem>
                            </>
                          )}
                          <DropdownMenuItem>
                            <Edit className="w-4 h-4 mr-2" />
                            수정
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDelete(draft.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            삭제
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>

        {/* 선택된 초안 상세보기 모달 */}
        {selectedDraft && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>리뷰 초안 상세</CardTitle>
                  <Button 
                    variant="ghost" 
                    size="icon"
                    onClick={() => setSelectedDraft(null)}
                  >
                    <XCircle className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">고객명</Label>
                    <p className="font-medium">{selectedDraft.customerName}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">연락처</Label>
                    <p className="font-medium">{selectedDraft.customerPhone}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">매장명</Label>
                    <p className="font-medium">{selectedDraft.storeName}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">플랫폼</Label>
                    <Badge className={platformConfig[selectedDraft.platform].color}>
                      {platformConfig[selectedDraft.platform].label}
                    </Badge>
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-medium text-muted-foreground">리뷰 내용</Label>
                  <div className="mt-2 p-4 bg-gray-50 rounded-lg">
                    <p className="whitespace-pre-wrap">{selectedDraft.content}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">템플릿</Label>
                    <p className="font-medium">{selectedDraft.template}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">톤</Label>
                    <p className="font-medium">{selectedDraft.tone}</p>
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-medium text-muted-foreground">키워드</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedDraft.keywords.map((keyword) => (
                      <Badge key={keyword} variant="secondary">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </div>

                {selectedDraft.status === 'pending' && (
                  <div className="flex space-x-2 pt-4">
                    <Button 
                      onClick={() => {
                        handleApprove(selectedDraft.id)
                        setSelectedDraft(null)
                      }}
                      className="flex-1"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      승인
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={() => {
                        handleReject(selectedDraft.id)
                        setSelectedDraft(null)
                      }}
                      className="flex-1"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      거부
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </AppLayout>
  )
}