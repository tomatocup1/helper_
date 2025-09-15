"use client"

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Shield, 
  Lock, 
  CheckCircle, 
  Star,
  Globe
} from 'lucide-react'


const certifications = [
  {
    title: 'ISO 27001',
    subtitle: '정보보안관리',
    icon: Shield,
    color: 'bg-blue-100 text-blue-600'
  },
  {
    title: 'KISA 인증',
    subtitle: '개인정보보호',
    icon: Lock,
    color: 'bg-green-100 text-green-600'
  },
  {
    title: 'AWS 보안',
    subtitle: '클라우드 보안',
    icon: CheckCircle,
    color: 'bg-orange-100 text-orange-600'
  },
  {
    title: 'SSL 인증서',
    subtitle: '데이터 암호화',
    icon: Globe,
    color: 'bg-purple-100 text-purple-600'
  }
]

const testimonials = [
  {
    name: '김영수',
    business: '청담동 맛집',
    rating: 5,
    content: '답글 작성 시간이 90% 줄었어요. 이제 요리에만 집중할 수 있습니다.',
    platform: '네이버 플레이스',
    improvement: '답글률 85% 증가'
  },
  {
    name: '박민지',
    business: '홍대 카페',
    rating: 5,
    content: '자동으로 우리 매장 톤에 맞춰 답글을 작성해줘서 너무 만족해요.',
    platform: '배달의민족',
    improvement: '평점 0.4점 상승'
  },
  {
    name: '이성호',
    business: '강남 치킨집',
    rating: 5,
    content: '4개 플랫폼을 한 번에 관리할 수 있어서 정말 편해졌습니다.',
    platform: '멀티플랫폼',
    improvement: '관리시간 70% 절약'
  }
]


export default function TrustIndicators() {
  return (
    <div className="bg-white py-16">
      <div className="container mx-auto px-4">

        {/* 보안 인증 */}
        <div className="mb-16">
          <h3 className="text-2xl font-bold text-center mb-8">보안 & 인증</h3>
          
          <div className="grid md:grid-cols-4 gap-6 max-w-3xl mx-auto">
            {certifications.map((cert, index) => {
              const Icon = cert.icon
              return (
                <div key={index} className="text-center">
                  <div className={`${cert.color} rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3`}>
                    <Icon className="h-8 w-8" />
                  </div>
                  <h4 className="font-semibold text-gray-900">{cert.title}</h4>
                  <p className="text-sm text-gray-600">{cert.subtitle}</p>
                </div>
              )
            })}
          </div>

          <div className="text-center mt-8">
            <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 px-4 py-2 rounded-full text-sm font-medium">
              <Shield className="h-4 w-4" />
              은행급 보안 시스템으로 고객 데이터를 안전하게 보호합니다
            </div>
          </div>
        </div>

        {/* 고객 후기 */}
        <div className="mb-16">
          <h3 className="text-2xl font-bold text-center mb-8">고객 성공 사례</h3>
          
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center gap-1 mb-3">
                    {Array.from({ length: testimonial.rating }).map((_, i) => (
                      <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                    ))}
                  </div>
                  
                  <p className="text-gray-700 mb-4 leading-relaxed">
                    "{testimonial.content}"
                  </p>
                  
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="font-semibold text-gray-900">{testimonial.name}</p>
                        <p className="text-sm text-gray-600">{testimonial.business}</p>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {testimonial.platform}
                      </Badge>
                    </div>
                    
                    <div className="bg-blue-50 rounded-lg p-3 text-center">
                      <p className="text-sm font-medium text-blue-700">
                        성과: {testimonial.improvement}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>


        {/* 서비스 가동 상태 */}
        <div className="mt-12 text-center">
          <div className="inline-flex items-center gap-3 bg-green-50 text-green-700 px-6 py-3 rounded-full">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="font-medium">시스템 정상 가동 중</span>
            <Badge variant="outline" className="bg-white text-green-700 border-green-200">
              99.9% 가동률
            </Badge>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            마지막 업데이트: {new Date().toLocaleString('ko-KR')}
          </p>
        </div>
      </div>
    </div>
  )
}