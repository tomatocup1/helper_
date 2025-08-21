"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { AlertTriangle, Loader2 } from 'lucide-react'

interface PlatformStore {
  id: string
  store_name: string
  platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
  platform_store_id: string
}

interface DeleteConfirmDialogProps {
  store: PlatformStore | null
  isOpen: boolean
  onClose: () => void
  onConfirm: (storeId: string) => Promise<void>
}

const platformNames = {
  naver: '네이버 플레이스',
  baemin: '배달의민족',
  yogiyo: '요기요',
  coupangeats: '쿠팡이츠'
}

export default function DeleteConfirmDialog({ 
  store, 
  isOpen, 
  onClose, 
  onConfirm 
}: DeleteConfirmDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false)

  const handleConfirm = async () => {
    if (!store) return

    setIsDeleting(true)
    try {
      await onConfirm(store.id)
      onClose()
    } catch (error) {
      console.error('Failed to delete store:', error)
      // 오류 처리는 부모 컴포넌트에서 처리
    } finally {
      setIsDeleting(false)
    }
  }

  const handleClose = () => {
    if (!isDeleting) {
      onClose()
    }
  }

  if (!store) return null

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <DialogTitle className="text-red-900">매장 삭제 확인</DialogTitle>
          </div>
          <DialogDescription className="text-left">
            정말로 이 매장을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
            <div className="font-medium text-red-900">삭제될 매장 정보:</div>
            <div className="text-sm text-red-800">
              <p><span className="font-medium">매장명:</span> {store.store_name}</p>
              <p><span className="font-medium">플랫폼:</span> {platformNames[store.platform]}</p>
              <p><span className="font-medium">매장 ID:</span> {store.platform_store_id}</p>
            </div>
          </div>

          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-medium">삭제 시 함께 제거되는 데이터:</p>
                <ul className="mt-1 list-disc list-inside text-xs space-y-1">
                  <li>매장의 모든 리뷰 데이터</li>
                  <li>AI 답글 및 초안</li>
                  <li>크롤링 이력</li>
                  <li>통계 및 분석 데이터</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button 
            variant="outline" 
            onClick={handleClose} 
            disabled={isDeleting}
          >
            취소
          </Button>
          <Button 
            variant="destructive" 
            onClick={handleConfirm} 
            disabled={isDeleting}
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                삭제 중...
              </>
            ) : (
              '삭제'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}