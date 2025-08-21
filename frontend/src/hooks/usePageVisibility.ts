'use client'

import { useState, useEffect } from 'react'

/**
 * 페이지 가시성을 감지하는 커스텀 훅
 * 탭 전환, 윈도우 포커스 변경을 추적하여 불필요한 API 호출을 방지
 */
export function usePageVisibility() {
  const [isVisible, setIsVisible] = useState<boolean>(() => {
    // SSR 환경에서는 기본값을 true로 설정
    if (typeof document === 'undefined') return true
    return !document.hidden
  })

  const [isWindowFocused, setIsWindowFocused] = useState<boolean>(() => {
    if (typeof document === 'undefined') return true
    return document.hasFocus()
  })

  useEffect(() => {
    if (typeof document === 'undefined' || typeof window === 'undefined') return

    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden)
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Page visibility changed:', !document.hidden ? 'visible' : 'hidden')
      }
    }

    const handleFocus = () => {
      setIsWindowFocused(true)
      if (process.env.NODE_ENV === 'development') {
        console.log('Window focused')
      }
    }

    const handleBlur = () => {
      setIsWindowFocused(false)
      if (process.env.NODE_ENV === 'development') {
        console.log('Window blurred')
      }
    }

    // Page Visibility API 이벤트 리스너
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    // Window focus/blur 이벤트 리스너
    window.addEventListener('focus', handleFocus)
    window.addEventListener('blur', handleBlur)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('focus', handleFocus)
      window.removeEventListener('blur', handleBlur)
    }
  }, [])

  return {
    isVisible,
    isWindowFocused,
    // 페이지가 완전히 활성화된 상태 (visible + focused)
    isActive: isVisible && isWindowFocused,
    // 백그라운드에서 실행되고 있는 상태
    isBackground: !isVisible || !isWindowFocused
  }
}

/**
 * 페이지가 백그라운드에서 활성화될 때 콜백을 실행하는 훅
 */
export function usePageActivation(callback: () => void, deps?: React.DependencyList) {
  const { isActive } = usePageVisibility()
  const [wasActive, setWasActive] = useState(isActive)

  useEffect(() => {
    // 페이지가 백그라운드에서 다시 활성화될 때만 콜백 실행
    if (isActive && !wasActive) {
      callback()
    }
    setWasActive(isActive)
  }, [isActive, wasActive, callback, ...(deps || [])])
}