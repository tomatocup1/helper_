"use client"

import { ReactNode } from 'react'
import { useAuth } from '@/store/auth-store-supabase'
import AppHeader from './AppHeader'

interface AppLayoutProps {
  children: ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const { user, loading, isInitialLoad } = useAuth()

  // 초기 로드일 때만 로딩 화면을 보여줌
  // 탭 전환이나 백그라운드 새로고침 시에는 기존 UI를 유지
  if (loading && isInitialLoad) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50/30">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
          <p className="text-gray-600">앱을 불러오는 중...</p>
          <p className="text-sm text-gray-400">잠시만 기다려주세요</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <>{children}</>
  }

  return (
    <div className="min-h-screen bg-gray-50/30">
      <AppHeader />
      <main className="container mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}