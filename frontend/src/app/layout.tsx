import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/store/auth-store-supabase'
import { initSupabaseConfigCheck } from '@/lib/validation/env-validator'

// 개발 환경에서 Supabase 설정 검사 초기화
if (process.env.NODE_ENV === 'development') {
  initSupabaseConfigCheck()
}

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '우리가게 도우미 - 소상공인을 위한 스마트 리뷰 관리',
  description: '소상공인들의 온라인 리뷰 관리와 고객 소통을 AI로 자동화하여 매출 증대를 돕는 서비스입니다.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}