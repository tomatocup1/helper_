"use client"

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { 
  Upload, 
  Camera, 
  Copy, 
  Check, 
  Star, 
  Sparkles, 
  Heart,
  MessageSquare,
  Share2
} from 'lucide-react'

interface StoreInfo {
  id: string
  name: string
  address: string
  customerMessage: string
  photoAnalysisPrompt: string
  naverReviewUrl: string
  minTextLength: number
  maxTextLength: number
  defaultTone: string
  positiveKeywords: string[]
  menuKeywords: string[]
  serviceKeywords: string[]
  atmosphereKeywords: string[]
}

interface GeneratedReview {
  text: string
  rating: number
  keywords: string[]
  analysis: {
    atmosphere: string
    food: string
    service: string
  }
}

export default function CustomerReviewPage() {
  const params = useParams()
  const storeId = params['store-id'] as string
  
  const [storeInfo, setStoreInfo] = useState<StoreInfo | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [previewUrls, setPreviewUrls] = useState<string[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedReview, setGeneratedReview] = useState<GeneratedReview | null>(null)
  const [copied, setCopied] = useState(false)
  const [currentStep, setCurrentStep] = useState<'upload' | 'generate' | 'result'>('upload')

  // 저장된 설정에서 매장 정보 불러오기
  useEffect(() => {
    // 로컬 스토리지에서 설정 불러오기
    const loadStoreSettings = () => {
      let savedSettings = null
      if (typeof window !== 'undefined') {
        const saved = localStorage.getItem('reviewDraftSettings')
        if (saved) {
          try {
            savedSettings = JSON.parse(saved)
          } catch (error) {
            console.error('설정 불러오기 실패:', error)
          }
        }
      }

      // 저장된 설정이 있으면 사용, 없으면 기본값
      setStoreInfo({
        id: storeId,
        name: '맛있는 한식당',
        address: '서울시 강남구 테헤란로 123',
        customerMessage: savedSettings?.customerMessage || '안녕하세요! 저희 매장을 방문해 주셔서 감사합니다. 리뷰 작성을 도와드리겠습니다.',
        photoAnalysisPrompt: savedSettings?.photoAnalysisPrompt || '이 사진들을 분석하여 음식점의 분위기, 음식, 서비스를 파악하고 긍정적인 리뷰를 작성해주세요.',
        naverReviewUrl: savedSettings?.naverReviewUrl || '',
        minTextLength: savedSettings?.minTextLength || 50,
        maxTextLength: savedSettings?.maxTextLength || 200,
        defaultTone: savedSettings?.defaultTone || 'friendly',
        positiveKeywords: savedSettings?.positiveKeywords || savedSettings?.businessKeywords || ['맛있다', '친절하다', '깔끔하다', '좋다'],
        menuKeywords: savedSettings?.menuKeywords || ['음식', '메뉴', '요리', '맛', '식사'],
        serviceKeywords: savedSettings?.serviceKeywords || ['서비스', '직원', '친절', '응대', '배려'],
        atmosphereKeywords: savedSettings?.atmosphereKeywords || ['분위기', '인테리어', '공간', '조용', '아늑']
      })
    }

    loadStoreSettings()
  }, [storeId])

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    if (files.length + uploadedFiles.length > 3) {
      alert('최대 3장까지 업로드 가능합니다.')
      return
    }

    setUploadedFiles(prev => [...prev, ...files])
    
    // 미리보기 URL 생성
    files.forEach(file => {
      const url = URL.createObjectURL(file)
      setPreviewUrls(prev => [...prev, url])
    })
  }

  const removeImage = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
    setPreviewUrls(prev => {
      const newUrls = prev.filter((_, i) => i !== index)
      // 제거된 URL 해제
      URL.revokeObjectURL(prev[index])
      return newUrls
    })
  }

  const generateReview = async () => {
    if (uploadedFiles.length === 0) {
      alert('사진을 먼저 업로드해주세요.')
      return
    }

    setIsGenerating(true)
    setCurrentStep('generate')

    try {
      // 이미지를 base64로 변환
      const imagePromises = uploadedFiles.map(file => {
        return new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            const base64 = reader.result as string
            // data:image/jpeg;base64, 부분 제거하고 base64 데이터만 추출
            const base64Data = base64.split(',')[1]
            resolve(base64Data)
          }
          reader.onerror = reject
          reader.readAsDataURL(file)
        })
      })

      const base64Images = await Promise.all(imagePromises)

      // API 호출
      const response = await fetch('/api/customer-review/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          storeId: storeId,
          images: base64Images,
          customPrompt: storeInfo?.photoAnalysisPrompt,
          reviewRules: {
            targetRating: 5,
            minTextLength: storeInfo?.minTextLength || 50,
            maxTextLength: storeInfo?.maxTextLength || 200,
            positiveKeywords: storeInfo?.positiveKeywords || ['맛있다', '친절하다', '깔끔하다', '좋다'],
            menuKeywords: storeInfo?.menuKeywords || ['음식', '메뉴', '요리'],
            serviceKeywords: storeInfo?.serviceKeywords || ['서비스', '직원', '친절'],
            atmosphereKeywords: storeInfo?.atmosphereKeywords || ['분위기', '인테리어', '공간']
          }
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || '리뷰 생성에 실패했습니다.')
      }

      const result = await response.json()
      
      // 응답 데이터 안전성 검증
      if (result && result.success === true && result.data && typeof result.data === 'object') {
        const generatedReview: GeneratedReview = {
          text: result.data.reviewText || '',
          rating: result.data.rating || 5,
          keywords: Array.isArray(result.data.keywords) ? result.data.keywords : [],
          analysis: result.data.analysis || ''
        }
        
        setGeneratedReview(generatedReview)
        setCurrentStep('result')
      } else {
        throw new Error('리뷰 생성 결과가 올바르지 않습니다.')
      }
    } catch (error: any) {
      console.error('리뷰 생성 실패:', error)
      
      // 개발 환경에서는 목 데이터로 폴백
      if (process.env.NODE_ENV === 'development') {
        console.log('개발 환경 - 목 데이터 사용')
        const mockReview: GeneratedReview = {
          text: '오늘 점심에 방문했는데 정말 만족스러운 식사였습니다! 음식이 맛있고 직원분들도 정말 친절하시더라고요. 특히 김치찌개가 진짜 맛있었어요. 분위기도 깔끔하고 아늑해서 편안하게 식사할 수 있었습니다. 다음에도 꼭 재방문하고 싶은 맛집이에요!',
          rating: 5,
          keywords: ['맛있다', '친절하다', '깔끔하다', '재방문'],
          analysis: {
            atmosphere: '깔끔하고 아늑한 분위기',
            food: '김치찌개가 특히 맛있음',
            service: '직원들이 매우 친절함'
          }
        }
        setGeneratedReview(mockReview)
        setCurrentStep('result')
      } else {
        alert(`리뷰 생성 중 오류가 발생했습니다: ${error.message}`)
        setCurrentStep('upload')
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const copyReview = async () => {
    if (!generatedReview) return
    
    try {
      await navigator.clipboard.writeText(generatedReview.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('복사 실패:', error)
      alert('복사에 실패했습니다. 직접 선택하여 복사해주세요.')
    }
  }

  const copyAndNavigate = async () => {
    if (!generatedReview || !storeInfo?.naverReviewUrl) return
    
    try {
      // 리뷰 텍스트 복사
      await navigator.clipboard.writeText(generatedReview.text)
      setCopied(true)
      
      // 네이버 리뷰 페이지로 이동
      window.open(storeInfo.naverReviewUrl, '_blank')
      
      // 성공 메시지 표시
      setTimeout(() => {
        alert('리뷰가 복사되었습니다! 네이버 페이지에서 붙여넣기(Ctrl+V)로 리뷰를 작성해주세요.')
        setCopied(false)
      }, 500)
    } catch (error) {
      console.error('복사 + 이동 실패:', error)
      alert('복사에 실패했습니다. 직접 선택하여 복사해주세요.')
    }
  }

  if (!storeInfo) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p>매장 정보를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100 p-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 brand-gradient rounded-2xl flex items-center justify-center">
            <Heart className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold brand-text">{storeInfo.name}</h1>
            <p className="text-muted-foreground mt-2">{storeInfo.address}</p>
          </div>
        </div>

        {/* 환영 메시지 */}
        <Card className="border-0 shadow-xl">
          <CardContent className="p-6">
            <div className="flex items-start space-x-3">
              <MessageSquare className="w-6 h-6 text-brand-600 mt-1" />
              <div>
                <p className="text-lg font-medium mb-2">매장에서 드리는 말씀</p>
                <p className="text-muted-foreground leading-relaxed">
                  {storeInfo.customerMessage}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 사진 업로드 섹션 */}
        {currentStep === 'upload' && (
          <Card className="border-0 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Camera className="w-5 h-5 mr-2" />
                매장 사진 업로드
              </CardTitle>
              <CardDescription>
                매장의 음식, 분위기, 인테리어 사진을 올려주세요 (최대 3장)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 파일 업로드 영역 */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-lg font-medium text-gray-700 mb-2">
                    사진을 업로드하세요
                  </p>
                  <p className="text-sm text-gray-500">
                    클릭하거나 파일을 드래그하여 업로드 (JPG, PNG)
                  </p>
                </label>
              </div>

              {/* 업로드된 이미지 미리보기 */}
              {previewUrls.length > 0 && (
                <div className="space-y-3">
                  <p className="font-medium">업로드된 사진 ({uploadedFiles.length}/3)</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {previewUrls.map((url, index) => (
                      <div key={index} className="relative">
                        <img
                          src={url}
                          alt={`업로드된 이미지 ${index + 1}`}
                          className="w-full h-32 object-cover rounded-lg"
                        />
                        <button
                          onClick={() => removeImage(index)}
                          className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {uploadedFiles.length > 0 && (
                <Button 
                  onClick={generateReview}
                  className="w-full"
                  size="lg"
                  disabled={isGenerating}
                >
                  <Sparkles className="w-5 h-5 mr-2" />
                  AI 리뷰 생성하기
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        {/* 생성 중 */}
        {currentStep === 'generate' && (
          <Card className="border-0 shadow-xl">
            <CardContent className="p-8 text-center">
              <div className="w-16 h-16 border-4 border-brand-600 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
              <h3 className="text-xl font-semibold mb-3">AI가 리뷰를 생성하고 있어요</h3>
              <p className="text-muted-foreground">
                업로드하신 사진을 분석하여 맞춤형 리뷰를 작성하고 있습니다...
              </p>
            </CardContent>
          </Card>
        )}

        {/* 생성된 리뷰 결과 */}
        {currentStep === 'result' && generatedReview && (
          <div className="space-y-6">
            {/* 분석 결과 */}
            <Card className="border-0 shadow-xl">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Sparkles className="w-5 h-5 mr-2" />
                  AI 분석 결과
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="font-medium text-blue-800 mb-2">분위기</h4>
                    <p className="text-sm text-blue-600">{generatedReview.analysis.atmosphere}</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h4 className="font-medium text-green-800 mb-2">음식</h4>
                    <p className="text-sm text-green-600">{generatedReview.analysis.food}</p>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <h4 className="font-medium text-purple-800 mb-2">서비스</h4>
                    <p className="text-sm text-purple-600">{generatedReview.analysis.service}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {generatedReview.keywords.map((keyword) => (
                    <Badge key={keyword} variant="secondary">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 생성된 리뷰 */}
            <Card className="border-0 shadow-xl">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center">
                    <MessageSquare className="w-5 h-5 mr-2" />
                    생성된 리뷰
                  </div>
                  <div className="flex items-center">
                    {[...Array(generatedReview.rating)].map((_, i) => (
                      <Star key={i} className="w-4 h-4 text-yellow-400 fill-current" />
                    ))}
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  value={generatedReview.text}
                  onChange={(e) => 
                    setGeneratedReview(prev => prev ? {...prev, text: e.target.value} : null)
                  }
                  rows={6}
                  className="resize-none"
                />
                
                <div className="space-y-3">
                  {/* 메인 액션 버튼 - 복사 + 이동 */}
                  {storeInfo?.naverReviewUrl ? (
                    <Button 
                      onClick={copyAndNavigate}
                      className="w-full"
                      size="lg"
                      variant="brand"
                      disabled={copied}
                    >
                      {copied ? (
                        <>
                          <Check className="w-5 h-5 mr-2" />
                          복사됨! 네이버로 이동 중...
                        </>
                      ) : (
                        <>
                          <Share2 className="w-5 h-5 mr-2" />
                          리뷰 복사하고 네이버로 이동
                        </>
                      )}
                    </Button>
                  ) : (
                    <Button 
                      onClick={copyReview}
                      className="w-full"
                      size="lg"
                      variant="brand"
                      disabled={copied}
                    >
                      {copied ? (
                        <>
                          <Check className="w-5 h-5 mr-2" />
                          복사됨!
                        </>
                      ) : (
                        <>
                          <Copy className="w-5 h-5 mr-2" />
                          리뷰 복사하기
                        </>
                      )}
                    </Button>
                  )}
                  
                  {/* 서브 액션 버튼들 */}
                  <div className="flex space-x-3">
                    <Button 
                      onClick={copyReview}
                      className="flex-1"
                      variant="outline"
                      disabled={copied}
                    >
                      <Copy className="w-4 h-4 mr-2" />
                      복사만 하기
                    </Button>
                    
                    <Button 
                      onClick={() => {
                        setCurrentStep('upload')
                        setGeneratedReview(null)
                        setUploadedFiles([])
                        setPreviewUrls([])
                      }}
                      variant="outline"
                    >
                      다시 생성
                    </Button>
                  </div>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex">
                    <Share2 className="w-5 h-5 text-yellow-600 mr-3 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-yellow-800">네이버에 리뷰 작성하기</h4>
                      <p className="text-sm text-yellow-600 mt-1">
                        위 리뷰를 복사한 후, 네이버 지도나 스마트플레이스에서 매장을 검색하여 리뷰를 작성해주세요.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}