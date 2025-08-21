'use client'

import { useState, useEffect } from 'react'

/**
 * 네트워크 연결 상태를 감지하는 커스텀 훅
 * 오프라인일 때 불필요한 API 호출을 방지하고 사용자에게 상태를 알림
 */
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    // SSR 환경에서는 기본값을 true로 설정
    if (typeof navigator === 'undefined') return true
    return navigator.onLine
  })

  const [wasOffline, setWasOffline] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleOnline = () => {
      setIsOnline(true)
      if (wasOffline) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Network connection restored')
        }
      }
      setWasOffline(false)
    }

    const handleOffline = () => {
      setIsOnline(false)
      setWasOffline(true)
      if (process.env.NODE_ENV === 'development') {
        console.log('Network connection lost')
      }
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [wasOffline])

  return {
    isOnline,
    isOffline: !isOnline,
    wasOffline,
    // 네트워크가 복구된 직후인지 확인
    justCameOnline: isOnline && wasOffline
  }
}

/**
 * 네트워크 연결이 복구될 때 콜백을 실행하는 훅
 */
export function useNetworkReconnection(callback: () => void, deps?: React.DependencyList) {
  const { justCameOnline } = useOnlineStatus()

  useEffect(() => {
    if (justCameOnline) {
      // 약간의 지연을 두고 실행하여 연결 안정화 대기
      const timer = setTimeout(() => {
        callback()
      }, 1000)

      return () => clearTimeout(timer)
    }
  }, [justCameOnline, callback, ...(deps || [])])
}