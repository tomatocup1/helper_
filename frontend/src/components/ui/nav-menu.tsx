"use client"

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/store/auth-store-supabase'
import {
  Store,
  BarChart3,
  MessageSquare,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
  User
} from 'lucide-react'

interface NavItem {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  description?: string
}

const navigation: NavItem[] = [
  {
    title: '대시보드',
    href: '/dashboard',
    icon: BarChart3,
    description: '전체 현황 요약'
  },
  {
    title: '매장 관리',
    href: '/stores',
    icon: Store,
    description: '매장 정보 및 설정'
  },
  {
    title: '리뷰 관리',
    href: '/reviews',
    icon: MessageSquare,
    description: '리뷰 및 답글 관리'
  },
  {
    title: '분석 리포트',
    href: '/analytics',
    icon: BarChart3,
    description: '상세 분석 및 인사이트'
  },
  {
    title: '설정',
    href: '/settings',
    icon: Settings,
    description: '계정 및 서비스 설정'
  }
]

export function NavMenu() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    setIsMobileMenuOpen(false)
  }

  return (
    <div className="border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/95">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="w-8 h-8 brand-gradient rounded-lg flex items-center justify-center">
              <Store className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg brand-text">우리가게 도우미</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href || 
                (item.href !== '/dashboard' && pathname.startsWith(item.href))
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    isActive
                      ? "bg-brand-100 text-brand-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  )}
                >
                  <div className="flex items-center space-x-2">
                    <item.icon className="w-4 h-4" />
                    <span>{item.title}</span>
                  </div>
                </Link>
              )
            })}
          </nav>

          {/* User Menu */}
          <div className="hidden md:flex items-center space-x-4">
            {/* Notifications */}
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full text-xs"></span>
            </Button>

            {/* User Profile */}
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-gray-600" />
              </div>
              <div className="text-sm">
                <div className="font-medium">{user?.name}</div>
                <div className="text-gray-500 capitalize">{user?.subscription_plan}</div>
              </div>
            </div>

            {/* Logout */}
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? (
              <X className="w-5 h-5" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </Button>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t">
            <nav className="space-y-2">
              {navigation.map((item) => {
                const isActive = pathname === item.href || 
                  (item.href !== '/dashboard' && pathname.startsWith(item.href))
                
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                      isActive
                        ? "bg-brand-100 text-brand-700"
                        : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                    )}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <item.icon className="w-5 h-5" />
                    <div>
                      <div>{item.title}</div>
                      {item.description && (
                        <div className="text-xs text-gray-500">{item.description}</div>
                      )}
                    </div>
                  </Link>
                )
              })}
            </nav>

            {/* Mobile User Info */}
            <div className="mt-4 pt-4 border-t">
              <div className="flex items-center space-x-3 px-3 py-2">
                <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                  <User className="w-5 h-5 text-gray-600" />
                </div>
                <div>
                  <div className="font-medium">{user?.name}</div>
                  <div className="text-sm text-gray-500">{user?.email}</div>
                  <div className="text-xs text-gray-400 capitalize">{user?.subscription_plan} 플랜</div>
                </div>
              </div>
              
              <div className="px-3 mt-2">
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={handleLogout}
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  로그아웃
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}