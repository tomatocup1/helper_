import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'
import { 
  ApiResponse, 
  AuthResponse, 
  LoginRequest, 
  RegisterRequest,
  User,
  Store,
  Review,
  AnalyticsDashboard,
  SubscriptionPlan,
  Subscription,
  Payment,
  PaginatedResponse
} from '@/types'

// API 클라이언트 설정
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request 인터셉터 - 토큰 자동 추가
    this.client.interceptors.request.use(
      (config) => {
        if (typeof window !== 'undefined') {
          const authStorage = localStorage.getItem('auth-storage')
          if (authStorage) {
            try {
              const { state } = JSON.parse(authStorage)
              if (state?.token) {
                config.headers.Authorization = `Bearer ${state.token}`
              }
            } catch (error) {
              console.error('Error parsing auth storage:', error)
            }
          }
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response 인터셉터 - 에러 처리 및 토큰 갱신
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          // 토큰 갱신 시도
          try {
            if (typeof window !== 'undefined') {
              const authStorage = localStorage.getItem('auth-storage')
              if (authStorage) {
                const { state } = JSON.parse(authStorage)
                if (state?.refreshToken) {
                  const response = await this.refreshToken(state.refreshToken)
                  if (response.data?.access_token) {
                    // 새 토큰으로 원래 요청 재시도
                    originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
                    return this.client(originalRequest)
                  }
                }
              }
            }
          } catch (refreshError) {
            // 토큰 갱신 실패 시 로그아웃 처리
            if (typeof window !== 'undefined') {
              localStorage.removeItem('auth-storage')
              window.location.href = '/login'
            }
          }
        }

        return Promise.reject(error)
      }
    )
  }

  private async refreshToken(refreshToken: string): Promise<AxiosResponse<AuthResponse>> {
    return this.client.post('/auth/refresh', { refresh_token: refreshToken })
  }

  // 일반적인 API 호출 메서드
  async get<T>(url: string, params?: any): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.get(url, { params })
      return {
        data: response.data,
        timestamp: new Date().toISOString(),
      }
    } catch (error) {
      return this.handleError(error as AxiosError)
    }
  }

  async post<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.post(url, data)
      return {
        data: response.data,
        timestamp: new Date().toISOString(),
      }
    } catch (error) {
      return this.handleError(error as AxiosError)
    }
  }

  async put<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.put(url, data)
      return {
        data: response.data,
        timestamp: new Date().toISOString(),
      }
    } catch (error) {
      return this.handleError(error as AxiosError)
    }
  }

  async delete<T>(url: string): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.delete(url)
      return {
        data: response.data,
        timestamp: new Date().toISOString(),
      }
    } catch (error) {
      return this.handleError(error as AxiosError)
    }
  }

  private handleError(error: AxiosError): ApiResponse {
    const timestamp = new Date().toISOString()

    if (error.response) {
      // 서버 응답이 있는 경우
      const responseData = error.response.data as any
      return {
        error: {
          code: responseData?.error?.code || 'SERVER_ERROR',
          message: responseData?.error?.message || '서버 오류가 발생했습니다.',
          details: responseData?.error?.details,
          path: error.config?.url,
        },
        timestamp,
      }
    } else if (error.request) {
      // 네트워크 오류
      return {
        error: {
          code: 'NETWORK_ERROR',
          message: '네트워크 연결을 확인해주세요.',
          details: { originalError: error.message },
        },
        timestamp,
      }
    } else {
      // 기타 오류
      return {
        error: {
          code: 'UNKNOWN_ERROR',
          message: '알 수 없는 오류가 발생했습니다.',
          details: { originalError: error.message },
        },
        timestamp,
      }
    }
  }
}

// API 클라이언트 인스턴스
const apiClient = new ApiClient()

// 인증 관련 API
export const authApi = {
  login: (data: LoginRequest) => 
    apiClient.post<AuthResponse>('/auth/login', data),
  
  register: (data: RegisterRequest) => 
    apiClient.post<AuthResponse>('/auth/register', data),
  
  refresh: (refreshToken: string) => 
    apiClient.post<AuthResponse>('/auth/refresh', { refresh_token: refreshToken }),
  
  logout: () => 
    apiClient.post('/auth/logout'),
}

// 사용자 관리 API
export const userApi = {
  getMe: () => 
    apiClient.get<User>('/users/me'),
  
  updateMe: (data: Partial<User>) => 
    apiClient.put<User>('/users/me', data),
  
  updateSettings: (settings: any) => 
    apiClient.put('/users/settings', settings),
}

// 매장 관리 API
export const storeApi = {
  getStores: (params?: { skip?: number; limit?: number }) => 
    apiClient.get<Store[]>('/stores', params),
  
  getStore: (id: string) => 
    apiClient.get<Store>(`/stores/${id}`),
  
  createStore: (data: Partial<Store>) => 
    apiClient.post<Store>('/stores', data),
  
  updateStore: (id: string, data: Partial<Store>) => 
    apiClient.put<Store>(`/stores/${id}`, data),
  
  deleteStore: (id: string) => 
    apiClient.delete(`/stores/${id}`),
  
  crawlStore: (id: string) => 
    apiClient.post(`/stores/${id}/crawl`),
}

// 리뷰 관리 API
export const reviewApi = {
  getReviews: (params?: {
    store_id?: string
    sentiment?: string
    has_reply?: boolean
    requires_check?: boolean
    date_from?: string
    date_to?: string
    skip?: number
    limit?: number
  }) => 
    apiClient.get<PaginatedResponse<Review>>('/reviews', params),
  
  getReview: (id: string) => 
    apiClient.get<Review>(`/reviews/${id}`),
  
  replyToReview: (id: string, data: { content: string; auto_post: boolean }) => 
    apiClient.post(`/reviews/${id}/reply`, data),
  
  markReviewChecked: (id: string) => 
    apiClient.post(`/reviews/${id}/check-complete`),
}

// 분석 API
export const analyticsApi = {
  getDashboard: (params?: { store_id?: string; period?: string }) => 
    apiClient.get<AnalyticsDashboard>('/analytics/dashboard', params),
  
  getRatingTrends: (params?: { store_id?: string; period?: string; interval?: string }) => 
    apiClient.get('/analytics/trends/rating', params),
  
  getKeywords: (params?: { store_id?: string; period?: string; limit?: number }) => 
    apiClient.get('/analytics/keywords', params),
}

// 결제 및 구독 API
export const paymentApi = {
  getPlans: () => 
    apiClient.get<SubscriptionPlan[]>('/payments/plans'),
  
  getSubscription: () => 
    apiClient.get<Subscription>('/payments/subscription'),
  
  changeSubscription: (data: { 
    target_tier: string; 
    billing_cycle: string; 
    payment_method: string; 
    auto_renewal: boolean 
  }) => 
    apiClient.post('/payments/subscription/change', data),
  
  getPaymentHistory: (params?: { skip?: number; limit?: number }) => 
    apiClient.get<PaginatedResponse<Payment>>('/payments/history', params),
}

export default apiClient