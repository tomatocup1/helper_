"use client"

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/store/auth-store-supabase'
import { createClient } from '@/lib/supabase/client'
import StoreSettingsModal from '@/components/stores/StoreSettingsModal'
import AppLayout from '@/components/layout/AppLayout'
import DeleteConfirmDialog from '@/components/stores/DeleteConfirmDialog'
import {
  Store,
  Plus,
  Settings,
  Activity,
  BarChart,
  Trash2,
  ExternalLink,
  Globe,
  User,
  MoreVertical
} from 'lucide-react'

// 플랫폼별 매장 데이터 인터페이스
interface PlatformStore {
  id: string
  store_name: string
  platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
  platform_store_id: string
  platform_id?: string
  is_active: boolean
  last_crawled_at?: string
  crawling_enabled: boolean
  created_at: string
  total_reviews?: number
  average_rating?: number
}

// Mock data - 실제 구현 시 API에서 가져올 데이터
const mockStores: PlatformStore[] = [
  {
    id: '1',
    store_name: '맛있는 치킨집',
    platform: 'naver',
    platform_store_id: '123456',
    platform_id: 'chicken@naver.com',
    is_active: true,
    crawling_enabled: true,
    last_crawled_at: '2024-01-15T10:30:00Z',
    created_at: '2024-01-01T00:00:00Z',
    total_reviews: 89,
    average_rating: 4.5
  },
  {
    id: '2', 
    store_name: '행복한 카페',
    platform: 'baemin',
    platform_store_id: '789012',
    platform_id: 'cafe@example.com',
    is_active: true,
    crawling_enabled: false,
    created_at: '2024-01-02T00:00:00Z',
    total_reviews: 67,
    average_rating: 4.2
  },
  {
    id: '3',
    store_name: '빠른 배달집',
    platform: 'yogiyo', 
    platform_store_id: '345678',
    platform_id: 'delivery@yogiyo.com',
    is_active: true,
    crawling_enabled: true,
    last_crawled_at: '2024-01-16T14:20:00Z',
    created_at: '2024-01-03T00:00:00Z',
    total_reviews: 142,
    average_rating: 4.7
  }
]

const platformNames = {
  naver: '네이버 플레이스',
  baemin: '배달의민족',
  yogiyo: '요기요',
  coupangeats: '쿠팡이츠'
}

const platformColors = {
  naver: 'bg-green-500',
  baemin: 'bg-blue-500', 
  yogiyo: 'bg-orange-500',
  coupangeats: 'bg-purple-500'
}

export default function StoresPage() {
  const { user, isAuthenticated } = useAuth()
  const [stores, setStores] = useState<PlatformStore[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedStore, setSelectedStore] = useState<PlatformStore | null>(null)
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [storeToDelete, setStoreToDelete] = useState<PlatformStore | null>(null)
  const supabase = createClient()

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchStores()
    }
  }, [isAuthenticated, user])

  const fetchStores = async () => {
    try {
      setIsLoading(true)
      const { data: storesData, error } = await supabase
        .from('platform_stores')
        .select('*')
        .eq('user_id', user?.id)
        .order('created_at', { ascending: false })

      if (error) {
        console.error('Error fetching stores:', error)
        // Fallback to mock data on error
        setStores(mockStores)
      } else {
        // 데이터베이스 구조를 인터페이스에 맞게 변환
        const transformedStores: PlatformStore[] = storesData.map(store => ({
          id: store.id,
          store_name: store.store_name,
          platform: store.platform,
          platform_store_id: store.platform_store_id,
          platform_id: store.platform_id,
          is_active: store.is_active,
          last_crawled_at: store.last_crawled_at,
          crawling_enabled: store.crawling_enabled,
          created_at: store.created_at,
          total_reviews: store.total_reviews || 0,
          average_rating: store.average_rating || 0
        }))
        setStores(transformedStores)
      }
    } catch (error) {
      console.error('Error fetching stores:', error)
      // Fallback to mock data on error
      setStores(mockStores)
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const handleOpenSettings = (store: PlatformStore) => {
    setSelectedStore(store)
    setIsSettingsModalOpen(true)
  }

  const handleSaveStoreSettings = async (storeId: string, data: any) => {
    try {
      const response = await fetch(`/api/v1/stores/${storeId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      })

      if (!response.ok) {
        throw new Error('Failed to update store')
      }

      // 매장 목록 새로고침
      await fetchStores()
    } catch (error) {
      console.error('Error updating store:', error)
      throw error
    }
  }

  const handleOpenDeleteDialog = (store: PlatformStore) => {
    setStoreToDelete(store)
    setIsDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async (storeId: string) => {
    try {
      const response = await fetch(`/api/v1/stores/${storeId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error('Failed to delete store')
      }

      // 매장 목록 새로고침
      await fetchStores()
    } catch (error) {
      console.error('Error deleting store:', error)
      throw error
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto"></div>
          <p className="text-gray-600">매장 정보를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold brand-text">내 매장 관리</h1>
          <p className="text-muted-foreground mt-1">
            플랫폼별 매장을 등록하고 리뷰를 관리하세요
          </p>
        </div>
        <Link href="/stores/add">
          <Button variant="brand" className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            매장 추가
          </Button>
        </Link>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Store className="w-5 h-5 text-brand-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">총 매장</p>
                <p className="text-2xl font-bold">{stores.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-green-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">활성 매장</p>
                <p className="text-2xl font-bold">
                  {stores.filter(s => s.is_active).length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Settings className="w-5 h-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">크롤링 활성</p>
                <p className="text-2xl font-bold">
                  {stores.filter(s => s.crawling_enabled).length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Globe className="w-5 h-5 text-purple-600" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">플랫폼</p>
                <p className="text-2xl font-bold">
                  {new Set(stores.map(s => s.platform)).size}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 매장 목록 */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">등록된 매장</h2>
        
        {stores.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <Store className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">등록된 매장이 없습니다</h3>
              <p className="text-muted-foreground mb-4">
                첫 번째 매장을 등록하여 리뷰 관리를 시작하세요
              </p>
              <Link href="/stores/add">
                <Button variant="brand">
                  <Plus className="w-4 h-4 mr-2" />
                  매장 추가
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stores.map((store) => (
              <Card key={store.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{store.store_name}</CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        ID: {store.platform_store_id}
                      </p>
                    </div>
                    <Badge 
                      variant={store.is_active ? "default" : "secondary"}
                      className={store.is_active ? "bg-green-100 text-green-800" : ""}
                    >
                      {store.is_active ? "활성" : "비활성"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* 플랫폼 정보 */}
                    <div className="flex items-center space-x-2">
                      <div className={`w-3 h-3 rounded-full ${platformColors[store.platform]}`}></div>
                      <span className="text-sm font-medium">
                        {platformNames[store.platform]}
                      </span>
                    </div>

                    {/* 계정 정보 */}
                    {store.platform_id && (
                      <div>
                        <p className="text-sm text-muted-foreground">계정</p>
                        <p className="text-sm font-mono">{store.platform_id}</p>
                      </div>
                    )}

                    {/* 크롤링 상태 */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">자동 크롤링</span>
                      <Badge 
                        variant={store.crawling_enabled ? "default" : "secondary"}
                        className={store.crawling_enabled ? "bg-blue-100 text-blue-800" : ""}
                      >
                        {store.crawling_enabled ? "활성" : "비활성"}
                      </Badge>
                    </div>

                    {/* 통계 정보 */}
                    {(store.total_reviews || store.average_rating) && (
                      <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                        {store.average_rating && (
                          <div className="text-center">
                            <p className="text-lg font-bold">{store.average_rating.toFixed(1)}</p>
                            <p className="text-xs text-muted-foreground">평점</p>
                          </div>
                        )}
                        {store.total_reviews && (
                          <div className="text-center">
                            <p className="text-lg font-bold">{store.total_reviews}</p>
                            <p className="text-xs text-muted-foreground">리뷰</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* 마지막 크롤링 */}
                    {store.last_crawled_at && (
                      <div>
                        <p className="text-sm text-muted-foreground">마지막 크롤링</p>
                        <p className="text-sm">
                          {new Date(store.last_crawled_at).toLocaleDateString('ko-KR', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </p>
                      </div>
                    )}

                    {/* 액션 버튼 */}
                    <div className="space-y-2 pt-2">
                      <div className="flex space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="flex-1"
                          onClick={() => handleOpenSettings(store)}
                        >
                          <Settings className="w-3 h-3 mr-1" />
                          설정
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="flex-1"
                          asChild
                        >
                          <Link href={`/stores/${store.id}/dashboard`}>
                            <BarChart className="w-3 h-3 mr-1" />
                            대시보드
                          </Link>
                        </Button>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="w-full text-red-600 hover:text-red-700 hover:bg-red-50"
                        onClick={() => handleOpenDeleteDialog(store)}
                      >
                        <Trash2 className="w-3 h-3 mr-1" />
                        삭제
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* 매장 설정 모달 */}
      <StoreSettingsModal
        store={selectedStore}
        isOpen={isSettingsModalOpen}
        onClose={() => {
          setIsSettingsModalOpen(false)
          setSelectedStore(null)
        }}
        onSave={handleSaveStoreSettings}
      />

      {/* 매장 삭제 확인 대화상자 */}
      <DeleteConfirmDialog
        store={storeToDelete}
        isOpen={isDeleteDialogOpen}
        onClose={() => {
          setIsDeleteDialogOpen(false)
          setStoreToDelete(null)
        }}
        onConfirm={handleConfirmDelete}
      />
      </div>
    </AppLayout>
  )
}