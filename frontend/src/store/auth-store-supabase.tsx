'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { createClient } from '@/lib/supabase/client'
import type { User as SupabaseUser } from '@supabase/supabase-js'
import type { Database } from '@/types/database'

type UserProfile = Database['public']['Tables']['users']['Row']

interface AuthState {
  user: UserProfile | null
  supabaseUser: SupabaseUser | null
  access_token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  loading: boolean
  isInitialLoad: boolean
  lastAuthCheck: number | null
  error: string | null
  
  // Actions
  login: (email: string, password: string) => Promise<boolean>
  register: (data: RegisterData) => Promise<boolean>
  logout: () => Promise<void>
  signOut: () => Promise<void>
  refreshSession: () => Promise<void>
  updateProfile: (data: Partial<UserProfile>) => Promise<boolean>
  checkAuth: (force?: boolean) => Promise<void>
  checkAuthSilently: () => Promise<void>
  clearError: () => void
  shouldSkipAuthCheck: () => boolean
}

interface RegisterData {
  email: string
  password: string
  name: string
  phone?: string
  terms_agreed: boolean
  privacy_agreed: boolean
  marketing_agreed?: boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      supabaseUser: null,
      access_token: null,
      isAuthenticated: false,
      isLoading: false,
      loading: false,
      isInitialLoad: true,
      lastAuthCheck: null,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, loading: true, error: null })
        const supabase = createClient()

        // 30초 타임아웃 설정
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('로그인 요청 시간이 초과되었습니다. 다시 시도해주세요.')), 30000)
        )

        try {
          // Supabase 로그인 (타임아웃과 함께)
          const loginPromise = supabase.auth.signInWithPassword({
            email,
            password,
          })
          
          const { data: authData, error: authError } = await Promise.race([
            loginPromise,
            timeoutPromise
          ]) as any

          if (authError) {
            console.error('Auth error details:', authError)
            // 로그인 실패 시 기존 세션도 정리
            await supabase.auth.signOut()
            throw authError
          }

          if (authData.user) {
            if (process.env.NODE_ENV === 'development') {
              console.log('Login successful, fetching profile for user:', authData.user.id)
              console.log('AuthData structure:', { 
                hasUser: !!authData.user, 
                hasSession: !!authData.session,
                sessionAccessToken: authData.session?.access_token ? 'present' : 'missing'
              })
            }
            
            // 사용자 프로필 가져오기
            let { data: profile, error: profileError } = await supabase
              .from('users')
              .select('*')
              .eq('id', authData.user.id)
              .single()

            // 프로필이 없는 경우 새로 생성
            if (profileError && profileError.code === 'PGRST116') {
              if (process.env.NODE_ENV === 'development') console.log('Profile not found, creating new profile...')
              
              // 기본 프로필 생성
              const { error: createError } = await supabase
                .from('users')
                .upsert({
                  id: authData.user.id,
                  email: authData.user.email,
                  name: authData.user.email?.split('@')[0] || 'Unknown User',
                  phone: null,
                  subscription_plan: 'free',
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                })

              if (createError) {
                console.error('Failed to create profile:', createError)
                throw createError
              }

              // 새로 생성된 프로필 가져오기
              const { data: newProfile, error: newProfileError } = await supabase
                .from('users')
                .select('*')
                .eq('id', authData.user.id)
                .single()

              if (newProfileError) throw newProfileError
              profile = newProfile
              
              if (process.env.NODE_ENV === 'development') console.log('New profile created:', profile)
            } else if (profileError) {
              console.error('Profile fetch error:', profileError)
              throw profileError
            }

            // 마지막 로그인 시간 업데이트
            if (profile) {
              await supabase
                .from('users')
                .update({ 
                  last_login_at: new Date().toISOString(),
                  updated_at: new Date().toISOString() 
                })
                .eq('id', authData.user.id)
            }

            set({
              user: profile,
              supabaseUser: authData.user,
              access_token: authData.session?.access_token || null,
              isAuthenticated: true,
              isLoading: false, 
              loading: false,
              isInitialLoad: false,
              lastAuthCheck: Date.now(),
              error: null,
            })

            if (process.env.NODE_ENV === 'development') {
              console.log('Login completed successfully')
              console.log('Access token available:', authData.session?.access_token ? 'YES' : 'NO')
            }
            return true
          }

          return false
        } catch (error: any) {
          console.error('Login error:', error)
          
          // 개발 환경에서 데모 로그인 허용
          if (process.env.NODE_ENV === 'development' && email === 'demo@example.com' && password === 'demo123') {
            if (process.env.NODE_ENV === 'development') console.log('Demo mode login')
            const mockUser = {
              id: 'demo-user-id',
              email: 'demo@example.com',
              name: 'Demo User',
              phone: '010-1234-5678',
              kakao_id: null,
              kakao_nickname: null,
              profile_image_url: null,
              subscription_plan: 'premium' as const,
              subscription_start_date: null,
              subscription_end_date: null,
              monthly_review_count: 0,
              total_review_count: 0,
              monthly_store_limit: 10,
              monthly_ai_reply_limit: 1000,
              monthly_draft_limit: 500,
              current_month_stores: 0,
              current_month_ai_replies: 0,
              current_month_drafts: 0,
              api_key: null,
              api_key_created_at: null,
              usage_reset_date: new Date().toISOString(),
              business_type: null,
              referral_code: null,
              referred_by: null,
              two_factor_enabled: false,
              last_login: new Date().toISOString(),
              is_active: true,
              marketing_agreed: false,
              privacy_agreed: true,
              service_agreed: true,
              terms_agreed: true,
              agreement_timestamp: new Date().toISOString(),
              last_login_at: new Date().toISOString(),
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              deleted_at: null,
              notes: null,
              tags: [],
              metadata: null,
            }
            
            set({
              user: mockUser,
              supabaseUser: null,
              isAuthenticated: true,
              isLoading: false,
              loading: false,
              isInitialLoad: false,
              lastAuthCheck: Date.now(),
              error: null,
            })
            
            return true
          }
          
          // 로그인 오류 메시지 개선
          let errorMessage = '로그인 중 오류가 발생했습니다.'
          if (error.message === 'Invalid login credentials') {
            errorMessage = '이메일 또는 비밀번호가 올바르지 않습니다. 회원가입을 먼저 진행해주세요.'
          } else if (error.message === 'Email not confirmed') {
            errorMessage = '이메일 인증이 필요합니다. 이메일을 확인해주세요.'
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({
            error: errorMessage,
            isLoading: false, loading: false,
            isAuthenticated: false,
          })
          return false
        }
      },

      register: async (data) => {
        set({ isLoading: true, loading: true, error: null })
        const supabase = createClient()

        try {
          // Supabase 회원가입
          if (process.env.NODE_ENV === 'development') console.log('Attempting signup with:', { email: data.email, name: data.name })
          const { data: authData, error: authError } = await supabase.auth.signUp({
            email: data.email,
            password: data.password,
            options: {
              data: {
                name: data.name,
                phone: data.phone,
              },
            },
          })

          if (process.env.NODE_ENV === 'development') console.log('Signup result:', { authData, authError })

          if (authError) throw authError

          if (authData.user) {
            if (process.env.NODE_ENV === 'development') console.log('User created:', authData.user)
            if (process.env.NODE_ENV === 'development') console.log('Email confirmed:', authData.user.email_confirmed_at)
            
            // 이메일 확인이 필요한 경우
            if (!authData.user.email_confirmed_at && authData.session === null) {
              set({
                isLoading: false, loading: false,
                error: '회원가입이 완료되었습니다. 하지만 이메일 확인이 필요할 수 있습니다. 로그인을 시도해보세요.',
                isAuthenticated: false,
              })
              return true // 회원가입은 성공으로 처리
            }

            // users 테이블에 사용자 정보 삽입 (INSERT 대신 UPSERT 사용)
            if (process.env.NODE_ENV === 'development') console.log('Inserting user profile...')
            const { error: profileError } = await supabase
              .from('users')
              .upsert({
                id: authData.user.id,
                email: authData.user.email,
                name: data.name,
                phone: data.phone || null,
                subscription_plan: 'free',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              })

            if (profileError) {
              console.error('Profile update error:', profileError)
              // 프로필 업데이트 실패해도 회원가입은 성공으로 처리
            } else {
              if (process.env.NODE_ENV === 'development') console.log('Profile created successfully')
            }

            // 프로필 정보 가져오기
            const { data: profile } = await supabase
              .from('users')
              .select('*')
              .eq('id', authData.user.id)
              .single()

            if (process.env.NODE_ENV === 'development') console.log('Profile retrieved:', profile)

            set({
              user: profile || null,
              supabaseUser: authData.user,
              access_token: authData.session?.access_token || null,
              isAuthenticated: authData.session !== null,
              isLoading: false, loading: false,
              error: null,
            })

            return true
          }

          return false
        } catch (error: any) {
          console.error('Register error:', error)
          
          // 회원가입 오류 메시지 개선
          let errorMessage = '회원가입 중 오류가 발생했습니다.'
          if (error.message === 'User already registered') {
            errorMessage = '이미 가입된 이메일입니다. 로그인을 시도해주세요.'
          } else if (error.message?.includes('Password')) {
            errorMessage = '비밀번호는 최소 6자 이상이어야 합니다.'
          } else if (error.message?.includes('Email')) {
            errorMessage = '올바른 이메일 형식을 입력해주세요.'
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({
            error: errorMessage,
            isLoading: false, loading: false,
            isAuthenticated: false,
          })
          return false
        }
      },

      logout: async () => {
        set({ isLoading: true, loading: true })
        const supabase = createClient()

        try {
          const { error } = await supabase.auth.signOut()
          if (error) throw error

          set({
            user: null,
            supabaseUser: null,
            isAuthenticated: false,
            isLoading: false, loading: false,
            error: null,
          })
        } catch (error: any) {
          console.error('Logout error:', error)
          set({
            error: error.message || '로그아웃 중 오류가 발생했습니다.',
            isLoading: false, loading: false,
          })
        }
      },

      signOut: async () => {
        await get().logout()
      },

      refreshSession: async () => {
        const supabase = createClient()

        try {
          const { data: { session }, error } = await supabase.auth.getSession()
          
          if (error) throw error

          if (session?.user) {
            // 사용자 프로필 가져오기
            const { data: profile, error: profileError } = await supabase
              .from('users')
              .select('*')
              .eq('id', session.user.id)
              .single()

            if (profileError) throw profileError

            set({
              user: profile,
              supabaseUser: session.user,
              access_token: session.access_token || null,
              isAuthenticated: true,
              error: null,
            })
          } else {
            set({
              user: null,
              supabaseUser: null,
              access_token: null,
              isAuthenticated: false,
            })
          }
        } catch (error: any) {
          console.error('Session refresh error:', error)
          set({
            user: null,
            supabaseUser: null,
            access_token: null,
            isAuthenticated: false,
            error: error.message,
          })
        }
      },

      updateProfile: async (data) => {
        set({ isLoading: true, loading: true, error: null })
        const supabase = createClient()
        const currentUser = get().supabaseUser

        if (!currentUser) {
          set({ error: '로그인이 필요합니다.', isLoading: false, loading: false })
          return false
        }

        try {
          const { error } = await supabase
            .from('users')
            .update(data)
            .eq('id', currentUser.id)

          if (error) throw error

          // 업데이트된 프로필 가져오기
          const { data: profile, error: profileError } = await supabase
            .from('users')
            .select('*')
            .eq('id', currentUser.id)
            .single()

          if (profileError) throw profileError

          set({
            user: profile,
            isLoading: false, loading: false,
            error: null,
          })

          return true
        } catch (error: any) {
          console.error('Profile update error:', error)
          set({
            error: error.message || '프로필 업데이트 중 오류가 발생했습니다.',
            isLoading: false, loading: false,
          })
          return false
        }
      },

      shouldSkipAuthCheck: () => {
        const state = get()
        
        // 초기 로드가 아니고, 최근에 확인했다면 스킵
        if (!state.isInitialLoad && state.lastAuthCheck) {
          const now = Date.now()
          const timeSinceLastCheck = now - state.lastAuthCheck
          const CACHE_DURATION = 5 * 60 * 1000 // 5분
          
          if (timeSinceLastCheck < CACHE_DURATION) {
            if (process.env.NODE_ENV === 'development') {
              console.log('Skipping auth check - recent check:', Math.round(timeSinceLastCheck / 1000), 'seconds ago')
            }
            return true
          }
        }
        
        return false
      },

      checkAuthSilently: async () => {
        const state = get()
        
        // 이미 로딩 중이면 중복 실행 방지
        if (state.isLoading) return
        
        // 캐시된 결과가 있으면 스킵
        if (state.shouldSkipAuthCheck()) return
        
        const supabase = createClient()
        
        try {
          const { data: { session }, error } = await supabase.auth.getSession()
          
          if (!error && session?.user) {
            // 조용히 lastAuthCheck만 업데이트
            set({ lastAuthCheck: Date.now() })
          }
        } catch (error) {
          // 조용히 실패 - 사용자에게 알리지 않음
          if (process.env.NODE_ENV === 'development') {
            console.log('Silent auth check failed:', error)
          }
        }
      },

      checkAuth: async (force = false) => {
        const currentState = get()
        
        // 이미 체크 중이면 중복 실행 방지
        if (currentState.isLoading) {
          if (process.env.NODE_ENV === 'development') console.log('checkAuth already in progress, skipping...')
          return
        }
        
        // force가 아니고 캐시된 결과가 있으면 스킵
        if (!force && currentState.shouldSkipAuthCheck()) {
          return
        }
        
        // 초기 로드가 아닌 경우에는 loading UI를 보여주지 않음
        const shouldShowLoading = currentState.isInitialLoad || force
        
        set({ 
          isLoading: shouldShowLoading, 
          loading: shouldShowLoading 
        })
        
        const supabase = createClient()
        if (process.env.NODE_ENV === 'development') {
          console.log('Starting checkAuth...', { 
            force, 
            isInitialLoad: currentState.isInitialLoad,
            showLoading: shouldShowLoading 
          })
        }

        try {
          // 먼저 세션 확인
          const { data: { session }, error: sessionError } = await supabase.auth.getSession()

          if (sessionError) {
            console.error('Session error:', sessionError)
            set({
              user: null,
              supabaseUser: null,
              access_token: null,
              isAuthenticated: false,
              isLoading: false, 
              loading: false,
              isInitialLoad: false,
              lastAuthCheck: Date.now(),
              error: null,
            })
            return
          }

          if (session?.user) {
            if (process.env.NODE_ENV === 'development') console.log('Session found, fetching profile for user:', session.user.id)
            
            // 사용자 프로필 가져오기
            let { data: profile, error: profileError } = await supabase
              .from('users')
              .select('*')
              .eq('id', session.user.id)
              .single()

            // 프로필이 없는 경우 새로 생성
            if (profileError && profileError.code === 'PGRST116') {
              if (process.env.NODE_ENV === 'development') console.log('Profile not found during checkAuth, creating new profile...')
              
              // 먼저 INSERT 시도
              const { error: insertError } = await supabase
                .from('users')
                .insert({
                  id: session.user.id,
                  email: session.user.email,
                  name: session.user.email?.split('@')[0] || 'Unknown User',
                  phone: null,
                  subscription_plan: 'free',
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                })
              
              // INSERT 실패 시 UPSERT 시도
              if (insertError) {
                if (process.env.NODE_ENV === 'development') console.log('INSERT failed, trying UPSERT:', insertError)
                const { error: upsertError } = await supabase
                  .from('users')
                  .upsert({
                    id: session.user.id,
                    email: session.user.email,
                    name: session.user.email?.split('@')[0] || 'Unknown User',
                    phone: null,
                    subscription_plan: 'free',
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                  })
                
                if (upsertError) {
                  console.error('Both INSERT and UPSERT failed:', upsertError)
                  console.error('Error details:', {
                    message: upsertError.message,
                    details: upsertError.details,
                    hint: upsertError.hint,
                    code: upsertError.code
                  })
                  // 프로필 생성 실패해도 세션은 유지
                  set({
                    user: null,
                    supabaseUser: session.user,
                    access_token: session.access_token || null,
                    isAuthenticated: true,
                    isLoading: false, 
                    loading: false,
                    isInitialLoad: false,
                    lastAuthCheck: Date.now(),
                    error: null,
                  })
                  return
                }
              }


              // 새로 생성된 프로필 가져오기
              const { data: newProfile, error: newProfileError } = await supabase
                .from('users')
                .select('*')
                .eq('id', session.user.id)
                .single()

              if (newProfileError) {
                console.error('Failed to fetch new profile:', newProfileError)
                set({
                  user: null,
                  supabaseUser: session.user,
                  access_token: session.access_token || null,
                  isAuthenticated: true,
                  isLoading: false, 
                  loading: false,
                  isInitialLoad: false,
                  lastAuthCheck: Date.now(),
                  error: null,
                })
                return
              }

              profile = newProfile
              if (process.env.NODE_ENV === 'development') console.log('New profile created during checkAuth:', profile)
            } else if (profileError) {
              console.error('Profile error during checkAuth:', profileError)
              // 다른 프로필 오류의 경우 세션은 유지하되 프로필은 null
              set({
                user: null,
                supabaseUser: session.user,
                access_token: session.access_token || null,
                isAuthenticated: true,
                isLoading: false, 
                loading: false,
                isInitialLoad: false,
                lastAuthCheck: Date.now(),
                error: null,
              })
              return
            }

            set({
              user: profile,
              supabaseUser: session.user,
              access_token: session.access_token || null,
              isAuthenticated: true,
              isLoading: false, 
              loading: false,
              isInitialLoad: false,
              lastAuthCheck: Date.now(),
              error: null,
            })
          } else {
            set({
              user: null,
              supabaseUser: null,
              access_token: null,
              isAuthenticated: false,
              isLoading: false, 
              loading: false,
              isInitialLoad: false,
              lastAuthCheck: Date.now(),
              error: null,
            })
          }
        } catch (error: any) {
          console.error('Auth check error:', error)
          set({
            user: null,
            supabaseUser: null,
            access_token: null,
            isAuthenticated: false,
            isLoading: false, 
            loading: false,
            isInitialLoad: false,
            lastAuthCheck: Date.now(),
            error: null, // 에러를 표시하지 않음 (초기 로드 시)
          })
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        // Supabase가 세션을 관리하므로 로컬 스토리지에는 최소한의 정보만 저장
        isAuthenticated: state.isAuthenticated,
        lastAuthCheck: state.lastAuthCheck,
      }),
    }
  )
)

// Auth context provider component
import { useEffect } from 'react'
import { usePageVisibility } from '@/hooks/usePageVisibility'
import { useOnlineStatus } from '@/hooks/useOnlineStatus'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const checkAuth = useAuthStore((state) => state.checkAuth)
  const checkAuthSilently = useAuthStore((state) => state.checkAuthSilently)
  const { isActive, isBackground } = usePageVisibility()
  const { isOnline, justCameOnline } = useOnlineStatus()

  // 초기 인증 확인
  useEffect(() => {
    let mounted = true

    const initAuth = async () => {
      if (mounted && isOnline) {
        if (process.env.NODE_ENV === 'development') {
          console.log('AuthProvider: Starting initial auth check')
        }
        
        try {
          // 10초 타임아웃 설정
          await Promise.race([
            checkAuth(true), // force = true for initial load
            new Promise((_, reject) => 
              setTimeout(() => reject(new Error('Auth check timeout')), 10000)
            )
          ])
          if (process.env.NODE_ENV === 'development') {
            console.log('AuthProvider: Initial auth check completed')
          }
        } catch (error) {
          console.error('Auth check failed or timed out:', error)
          // 타임아웃 시 로딩 상태 해제
          useAuthStore.setState({
            isLoading: false,
            loading: false,
            isInitialLoad: false,
            lastAuthCheck: Date.now(),
            isAuthenticated: false,
            user: null,
            supabaseUser: null,
            access_token: null,
            error: null
          })
        }
      }
    }

    initAuth()

    return () => {
      mounted = false
    }
  }, []) // 초기 로드 시에만 실행

  // 페이지 활성화 시 조용한 인증 확인
  useEffect(() => {
    if (isActive && isOnline) {
      // 백그라운드에서 돌아왔을 때 조용히 인증 상태 확인
      const timer = setTimeout(() => {
        checkAuthSilently()
      }, 500) // 500ms 지연으로 탭 전환 완료 후 실행

      return () => clearTimeout(timer)
    }
  }, [isActive, isOnline])

  // 네트워크 연결 복구 시 인증 상태 확인
  useEffect(() => {
    if (justCameOnline) {
      checkAuthSilently()
    }
  }, [justCameOnline])

  // Supabase auth 상태 변경 리스너 
  useEffect(() => {
    const supabase = createClient()
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (process.env.NODE_ENV === 'development') {
        console.log('Auth state change:', event, session?.user?.email)
      }
      
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        // 페이지가 활성화되어 있을 때만 즉시 확인
        if (isActive && isOnline) {
          const currentState = useAuthStore.getState()
          if (!currentState.isLoading) {
            await checkAuthSilently()
          }
        }
      } else if (event === 'SIGNED_OUT') {
        useAuthStore.setState({
          user: null,
          supabaseUser: null,
          access_token: null,
          isAuthenticated: false,
          isLoading: false, 
          loading: false,
          isInitialLoad: false,
          lastAuthCheck: Date.now(),
          error: null,
        })
      }
    })

    return () => {
      subscription.unsubscribe()
    }
  }, []) // checkAuth 의존성 제거

  return <>{children}</>
}

// Export hook for backward compatibility
export const useAuth = useAuthStore