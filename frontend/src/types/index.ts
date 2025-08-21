// User & Authentication Types
export interface User {
  id: string
  email: string
  name: string
  phone?: string
  business_number?: string
  subscription_tier: 'free' | 'basic' | 'premium' | 'enterprise'
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface LoginRequest {
  email: string
  password: string
  remember_me?: boolean
}

export interface RegisterRequest {
  email: string
  password: string
  name: string
  phone?: string
  business_number?: string
}

// Store Types
export interface Store {
  id: string
  user_id: string
  name: string
  platform: 'naver' | 'kakao' | 'google'
  platform_store_id: string
  address?: string
  category?: string
  phone?: string
  status: 'pending' | 'active' | 'inactive' | 'error'
  menu_items?: MenuItem[]
  keywords?: string[]
  operating_hours?: OperatingHours
  is_crawling_enabled: boolean
  is_auto_reply_enabled: boolean
  settings?: StoreSettings
  stats?: StoreStats
  last_crawled_at?: string
  created_at: string
  updated_at: string
}

export interface MenuItem {
  name: string
  price: number
  description?: string
}

export interface OperatingHours {
  [key: string]: {
    open: string
    close: string
    is_closed?: boolean
  }
}

export interface StoreSettings {
  auto_reply_enabled: boolean
  reply_delay_minutes: number
  notification_enabled: boolean
  keywords: string[]
  reply_rules?: ReplyRule[]
}

export interface StoreStats {
  total_reviews: number
  average_rating: number
  reply_rate: number
  this_month_reviews: number
  this_week_reviews: number
}

// Review Types
export interface Review {
  id: string
  store_id: string
  platform_review_id: string
  reviewer_name: string
  rating: number
  content: string
  images?: string[]
  sentiment: 'positive' | 'negative' | 'neutral'
  sentiment_score: number
  keywords: string[]
  reply_content?: string
  reply_status: 'pending' | 'generated' | 'replied' | 'requires_review'
  requires_owner_check: boolean
  review_date: string
  created_at: string
  crawled_at: string
}

export interface ReviewReply {
  id: string
  review_id: string
  content: string
  reply_type: 'manual' | 'ai_generated'
  status: 'draft' | 'pending' | 'posted' | 'failed'
  is_posted_to_platform: boolean
  created_at: string
  posted_at?: string
}

export interface ReplyRule {
  id: string
  store_id: string
  condition_type: 'sentiment' | 'keyword' | 'rating'
  condition_value: string | number
  template: string
  is_active: boolean
  priority: number
}

// Analytics Types
export interface AnalyticsDashboard {
  overview: AnalyticsOverview
  recent_trends: TrendData
  top_keywords: KeywordData[]
  recommendations: Recommendation[]
  alerts: Alert[]
}

export interface AnalyticsOverview {
  total_reviews: number
  new_reviews: number
  average_rating: number
  rating_distribution: Record<string, number>
  sentiment_distribution: Record<string, number>
  reply_rate: number
  average_reply_time_hours: number
}

export interface TrendData {
  period: string
  data_points: {
    date: string
    value: number
    count: number
  }[]
  trend_direction: 'up' | 'down' | 'stable'
  growth_rate: number
}

export interface KeywordData {
  keyword: string
  count: number
  sentiment: 'positive' | 'negative' | 'neutral'
  growth?: number
}

export interface Recommendation {
  priority: 'high' | 'medium' | 'low'
  category: 'service' | 'quality' | 'marketing' | 'operational'
  title: string
  description: string
  expected_impact: string
  implementation_difficulty: 'easy' | 'medium' | 'hard'
}

export interface Alert {
  type: 'info' | 'warning' | 'error' | 'success'
  message: string
  action?: string
  created_at: string
}

// Payment & Subscription Types
export interface SubscriptionPlan {
  tier: 'free' | 'basic' | 'premium' | 'enterprise'
  name: string
  description: string
  monthly_price: number
  yearly_price: number
  features: string[]
  limits: SubscriptionLimits
  popular?: boolean
}

export interface SubscriptionLimits {
  max_stores: number
  monthly_reviews: number
  monthly_replies: number
  analytics_history_days: number
}

export interface Subscription {
  tier: string
  name: string
  start_date: string
  end_date: string
  auto_renewal: boolean
  payment_method: string
  next_billing_date: string
  remaining_days: number
  usage: SubscriptionUsage
  limits: SubscriptionLimits
}

export interface SubscriptionUsage {
  stores: number
  monthly_reviews: number
  monthly_replies: number
}

export interface Payment {
  id: string
  amount: number
  currency: string
  description: string
  status: 'pending' | 'completed' | 'failed' | 'refunded'
  payment_method: string
  transaction_id: string
  billing_period_start: string
  billing_period_end: string
  created_at: string
  completed_at?: string
  receipt_url?: string
}

// API Types
export interface ApiResponse<T = any> {
  data?: T
  error?: ApiError
  message?: string
  timestamp: string
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  path?: string
  request_id?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  has_next: boolean
  has_prev: boolean
}

// Form Types
export interface FormField {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'tel' | 'select' | 'textarea' | 'checkbox'
  placeholder?: string
  required?: boolean
  validation?: ValidationRule[]
  options?: SelectOption[]
}

export interface ValidationRule {
  type: 'required' | 'email' | 'minLength' | 'maxLength' | 'pattern'
  value?: any
  message: string
}

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

// UI State Types
export interface LoadingState {
  isLoading: boolean
  message?: string
}

export interface ErrorState {
  hasError: boolean
  message?: string
  details?: any
}

// Chart Data Types
export interface ChartDataPoint {
  date: string
  value: number
  label?: string
  color?: string
}