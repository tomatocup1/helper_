"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Eye, EyeOff, Loader2, Settings } from 'lucide-react'

interface PlatformStore {
  id: string
  store_name: string
  platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
  platform_store_id: string
  platform_id?: string
  business_type?: string
  address?: string
  phone?: string
  is_active: boolean
}

interface StoreSettingsModalProps {
  store: PlatformStore | null
  isOpen: boolean
  onClose: () => void
  onSave: (storeId: string, data: UpdateStoreData) => Promise<void>
}

interface UpdateStoreData {
  business_type?: string
  address?: string
  phone?: string
  platform_id: string
  platform_pw: string
}

const businessTypes = [
  { value: '음식점', label: '음식점' },
  { value: '카페', label: '카페' },
  { value: '배달업', label: '배달업' },
  { value: '패스트푸드', label: '패스트푸드' },
  { value: '치킨', label: '치킨' },
  { value: '피자', label: '피자' },
  { value: '중국음식', label: '중국음식' },
  { value: '한식', label: '한식' },
  { value: '일식', label: '일식' },
  { value: '양식', label: '양식' },
  { value: '기타', label: '기타' }
]

export default function StoreSettingsModal({ 
  store, 
  isOpen, 
  onClose, 
  onSave 
}: StoreSettingsModalProps) {
  const [formData, setFormData] = useState<UpdateStoreData>({
    business_type: '',
    address: '',
    phone: '',
    platform_id: '',
    platform_pw: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [errors, setErrors] = useState<{[key: string]: string}>({})

  // 매장 정보가 변경될 때 폼 데이터 초기화
  useEffect(() => {
    if (store && isOpen) {
      setFormData({
        business_type: store.business_type || '',
        address: store.address || '',
        phone: store.phone || '',
        platform_id: store.platform_id || '',
        platform_pw: '' // 보안상 비워둠
      })
      setErrors({})
      
      // 암호화된 비밀번호 복호화해서 가져오기
      if (store.id) {
        fetchDecryptedPassword(store.id)
      }
    }
  }, [store, isOpen])

  const fetchDecryptedPassword = async (storeId: string) => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/v1/stores/${storeId}/password`)
      if (response.ok) {
        const data = await response.json()
        // 안전한 데이터 접근
        if (data && typeof data === 'object') {
          setFormData(prev => ({
            ...prev,
            platform_pw: data.password || ''
          }))
        }
      }
    } catch (error) {
      console.error('Failed to fetch password:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {}
    
    if (!formData.platform_id.trim()) {
      newErrors.platform_id = '플랫폼 아이디를 입력해주세요'
    }
    
    if (!formData.platform_pw.trim()) {
      newErrors.platform_pw = '비밀번호를 입력해주세요'
    }

    if (formData.phone && !/^[\d-+\s()]+$/.test(formData.phone)) {
      newErrors.phone = '올바른 전화번호 형식이 아닙니다'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSave = async () => {
    if (!store || !validateForm()) return

    setIsSaving(true)
    try {
      await onSave(store.id, formData)
      onClose()
    } catch (error) {
      console.error('Failed to save store settings:', error)
      setErrors({ general: '저장 중 오류가 발생했습니다.' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleClose = () => {
    setFormData({
      business_type: '',
      address: '',
      phone: '',
      platform_id: '',
      platform_pw: ''
    })
    setErrors({})
    setShowPassword(false)
    onClose()
  }

  if (!store) return null

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Settings className="w-5 h-5" />
            <span>매장 설정</span>
          </DialogTitle>
          <DialogDescription>
            {store.store_name}의 정보를 수정하세요
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* 업종 */}
          <div className="grid gap-2">
            <Label htmlFor="business_type">업종</Label>
            <Select
              value={formData.business_type}
              onValueChange={(value) => setFormData(prev => ({ ...prev, business_type: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="업종을 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {businessTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 주소 */}
          <div className="grid gap-2">
            <Label htmlFor="address">주소 (선택사항)</Label>
            <Input
              id="address"
              placeholder="매장 주소를 입력하세요"
              value={formData.address}
              onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
            />
          </div>

          {/* 전화번호 */}
          <div className="grid gap-2">
            <Label htmlFor="phone">전화번호 (선택사항)</Label>
            <Input
              id="phone"
              placeholder="010-1234-5678"
              value={formData.phone}
              onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
              error={!!errors.phone}
              helpText={errors.phone}
            />
          </div>

          {/* 플랫폼 아이디 */}
          <div className="grid gap-2">
            <Label htmlFor="platform_id">플랫폼 아이디</Label>
            <Input
              id="platform_id"
              placeholder="로그인 아이디 또는 이메일"
              value={formData.platform_id}
              onChange={(e) => setFormData(prev => ({ ...prev, platform_id: e.target.value }))}
              error={!!errors.platform_id}
              helpText={errors.platform_id}
            />
          </div>

          {/* 플랫폼 비밀번호 */}
          <div className="grid gap-2">
            <Label htmlFor="platform_pw">플랫폼 비밀번호</Label>
            <div className="relative">
              <Input
                id="platform_pw"
                type={showPassword ? 'text' : 'password'}
                placeholder="비밀번호"
                value={isLoading ? '로딩 중...' : formData.platform_pw}
                onChange={(e) => setFormData(prev => ({ ...prev, platform_pw: e.target.value }))}
                disabled={isLoading}
                error={!!errors.platform_pw}
                helpText={errors.platform_pw}
                className="pr-10"
              />
              <button
                type="button"
                className="absolute right-3 top-2 text-muted-foreground hover:text-foreground"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {errors.general && (
            <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
              {errors.general}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSaving}>
            취소
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                저장 중...
              </>
            ) : (
              '저장'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}