import { NextRequest, NextResponse } from 'next/server'
import OpenAI from 'openai'

// OpenAI 클라이언트 초기화
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
})

interface ReviewGenerationRequest {
  storeId: string
  images: string[] // base64 encoded images
  customPrompt?: string
  reviewRules?: {
    targetRating: number
    minTextLength: number
    maxTextLength: number
    positiveKeywords: string[]
    menuKeywords: string[]
    serviceKeywords: string[]
    atmosphereKeywords: string[]
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: ReviewGenerationRequest = await request.json()
    const { storeId, images, customPrompt, reviewRules } = body

    if (!images || images.length === 0) {
      return NextResponse.json(
        { error: '이미지가 제공되지 않았습니다.' },
        { status: 400 }
      )
    }

    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json(
        { error: 'OpenAI API 키가 설정되지 않았습니다.' },
        { status: 500 }
      )
    }

    // 시스템 프롬프트 구성
    const systemPrompt = `당신은 음식점 리뷰 전문 작성자입니다. 제공된 사진들을 분석하여 고객 관점에서 진솔하고 도움이 되는 리뷰를 작성해주세요.

리뷰 작성 가이드라인:
- 목표 평점: ${reviewRules?.targetRating || 5}점
- 리뷰 길이: ${reviewRules?.minTextLength || 50}자 이상 ${reviewRules?.maxTextLength || 300}자 이하
- 톤: 친근하고 자연스럽게, 실제 고객이 작성한 것처럼

키워드 가이드:
- 긍정 키워드: ${reviewRules?.positiveKeywords?.join(', ') || '맛있다, 친절하다, 깔끔하다'}
- 메뉴 키워드: ${reviewRules?.menuKeywords?.join(', ') || '음식, 메뉴, 요리'}
- 서비스 키워드: ${reviewRules?.serviceKeywords?.join(', ') || '서비스, 직원, 친절'}
- 분위기 키워드: ${reviewRules?.atmosphereKeywords?.join(', ') || '분위기, 인테리어, 공간'}

분석할 요소:
1. 음식의 외관과 추정 맛
2. 매장 분위기와 인테리어
3. 청결도와 전반적인 느낌

응답은 다음 JSON 형식으로 제공해주세요:
{
  "reviewText": "생성된 리뷰 텍스트",
  "rating": 평점(1-5),
  "analysis": {
    "atmosphere": "분위기 분석",
    "food": "음식 분석", 
    "service": "서비스 추정"
  },
  "keywords": ["추출된", "키워드", "목록"]
}`

    // 사용자 프롬프트 (매장별 커스터마이징 적용)
    const userPrompt = customPrompt || '이 사진들을 분석하여 음식점의 분위기, 음식, 서비스를 파악하고 긍정적인 리뷰를 작성해주세요.'

    // OpenAI API 호출을 위한 메시지 구성
    const messages: any[] = [
      {
        role: 'system',
        content: systemPrompt
      },
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: userPrompt
          },
          ...images.map(image => ({
            type: 'image_url',
            image_url: {
              url: `data:image/jpeg;base64,${image}`,
              detail: 'low' // 비용 절약을 위해 low detail 사용
            }
          }))
        ]
      }
    ]

    console.log('OpenAI API 호출 시작...')
    
    // GPT-4o-mini Vision API 호출
    const response = await openai.chat.completions.create({
      model: 'gpt-4o-mini', // GPT-4o-mini 모델 사용
      messages,
      max_tokens: 1000,
      temperature: 0.7,
    })

    const aiResponse = response.choices[0]?.message?.content

    if (!aiResponse) {
      throw new Error('AI로부터 응답을 받지 못했습니다.')
    }

    console.log('AI 응답:', aiResponse)

    // JSON 응답 파싱 시도
    let parsedResponse
    try {
      // JSON 형태로 응답이 오지 않을 수도 있으므로 안전하게 처리
      const jsonMatch = aiResponse.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        parsedResponse = JSON.parse(jsonMatch[0])
      } else {
        // JSON이 아닌 경우 기본 구조로 래핑
        parsedResponse = {
          reviewText: aiResponse,
          rating: reviewRules?.targetRating || 5,
          analysis: {
            atmosphere: '분석 중...',
            food: '분석 중...',
            service: '분석 중...'
          },
          keywords: [
            ...(reviewRules?.positiveKeywords || ['맛있다', '좋다']),
            ...(reviewRules?.menuKeywords || []).slice(0, 2),
            ...(reviewRules?.serviceKeywords || []).slice(0, 1),
            ...(reviewRules?.atmosphereKeywords || []).slice(0, 1)
          ].slice(0, 6)
        }
      }
    } catch (parseError) {
      console.error('JSON 파싱 오류:', parseError)
      parsedResponse = {
        reviewText: aiResponse,
        rating: reviewRules?.targetRating || 5,
        analysis: {
          atmosphere: '분석 중...',
          food: '분석 중...',
          service: '분석 중...'
        },
        keywords: [
          ...(reviewRules?.positiveKeywords || ['맛있다', '좋다']),
          ...(reviewRules?.menuKeywords || []).slice(0, 2),
          ...(reviewRules?.serviceKeywords || []).slice(0, 1),
          ...(reviewRules?.atmosphereKeywords || []).slice(0, 1)
        ].slice(0, 6)
      }
    }

    // 향후 구현: 데이터베이스에 생성된 리뷰 저장
    // const reviewDraft = await saveReviewDraft({
    //   storeId,
    //   reviewText: parsedResponse.reviewText,
    //   rating: parsedResponse.rating,
    //   analysis: parsedResponse.analysis,
    //   keywords: parsedResponse.keywords,
    //   uploadedPhotos: images.map((img, index) => ({ 
    //     index, 
    //     size: img.length 
    //   }))
    // })

    return NextResponse.json({
      success: true,
      data: parsedResponse
    })

  } catch (error: any) {
    console.error('리뷰 생성 오류:', error)
    
    // OpenAI API 에러 처리
    if (error.code === 'insufficient_quota') {
      return NextResponse.json(
        { error: 'API 사용량이 초과되었습니다. 관리자에게 문의해주세요.' },
        { status: 429 }
      )
    }
    
    if (error.code === 'invalid_api_key') {
      return NextResponse.json(
        { error: 'API 키가 올바르지 않습니다.' },
        { status: 401 }
      )
    }

    return NextResponse.json(
      { 
        error: '리뷰 생성 중 오류가 발생했습니다.',
        details: process.env.NODE_ENV === 'development' ? error.message : undefined
      },
      { status: 500 }
    )
  }
}