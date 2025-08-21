// Supabase Database Types
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string
          email: string
          name: string
          phone: string | null
          kakao_id: string | null
          kakao_nickname: string | null
          profile_image_url: string | null
          subscription_plan: 'free' | 'basic' | 'premium' | 'enterprise'
          subscription_start_date: string | null
          subscription_end_date: string | null
          monthly_store_limit: number
          monthly_ai_reply_limit: number
          monthly_draft_limit: number
          current_month_stores: number
          current_month_ai_replies: number
          current_month_drafts: number
          usage_reset_date: string | null
          business_type: string | null
          referral_code: string | null
          referred_by: string | null
          terms_agreed: boolean
          privacy_agreed: boolean
          marketing_agreed: boolean
          agreement_timestamp: string | null
          is_active: boolean
          last_login_at: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          email: string
          name: string
          phone?: string | null
          kakao_id?: string | null
          kakao_nickname?: string | null
          profile_image_url?: string | null
          subscription_plan?: 'free' | 'basic' | 'premium' | 'enterprise'
          subscription_start_date?: string | null
          subscription_end_date?: string | null
          monthly_store_limit?: number
          monthly_ai_reply_limit?: number
          monthly_draft_limit?: number
          current_month_stores?: number
          current_month_ai_replies?: number
          current_month_drafts?: number
          usage_reset_date?: string | null
          business_type?: string | null
          referral_code?: string | null
          referred_by?: string | null
          terms_agreed?: boolean
          privacy_agreed?: boolean
          marketing_agreed?: boolean
          agreement_timestamp?: string | null
          is_active?: boolean
          last_login_at?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          email?: string
          name?: string
          phone?: string | null
          kakao_id?: string | null
          kakao_nickname?: string | null
          profile_image_url?: string | null
          subscription_plan?: 'free' | 'basic' | 'premium' | 'enterprise'
          subscription_start_date?: string | null
          subscription_end_date?: string | null
          monthly_store_limit?: number
          monthly_ai_reply_limit?: number
          monthly_draft_limit?: number
          current_month_stores?: number
          current_month_ai_replies?: number
          current_month_drafts?: number
          usage_reset_date?: string | null
          business_type?: string | null
          referral_code?: string | null
          referred_by?: string | null
          terms_agreed?: boolean
          privacy_agreed?: boolean
          marketing_agreed?: boolean
          agreement_timestamp?: string | null
          is_active?: boolean
          last_login_at?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      platform_stores: {
        Row: {
          id: string
          user_id: string
          store_name: string
          business_type: string | null
          address: string | null
          phone: string | null
          business_registration_number: string | null
          platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
          platform_store_id: string
          platform_url: string | null
          crawling_enabled: boolean
          crawling_interval_minutes: number
          last_crawled_at: string | null
          next_crawl_at: string | null
          auto_reply_enabled: boolean
          reply_style: 'friendly' | 'formal' | 'casual'
          custom_instructions: string | null
          positive_reply_template: string | null
          negative_reply_template: string | null
          neutral_reply_template: string | null
          negative_review_delay_hours: number
          auto_approve_positive: boolean
          require_approval_negative: boolean
          branding_keywords: Json | null
          seo_keywords: Json | null
          naver_id: string | null
          naver_password_encrypted: string | null
          naver_session_active: boolean
          naver_last_login: string | null
          naver_device_registered: boolean
          naver_login_attempts: number
          naver_profile_path: string | null
          is_active: boolean
          is_verified: boolean
          verification_date: string | null
          platform_metadata: Json | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          store_name: string
          business_type?: string | null
          address?: string | null
          phone?: string | null
          business_registration_number?: string | null
          platform: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
          platform_store_id: string
          platform_url?: string | null
          crawling_enabled?: boolean
          crawling_interval_minutes?: number
          last_crawled_at?: string | null
          next_crawl_at?: string | null
          auto_reply_enabled?: boolean
          reply_style?: 'friendly' | 'formal' | 'casual'
          custom_instructions?: string | null
          positive_reply_template?: string | null
          negative_reply_template?: string | null
          neutral_reply_template?: string | null
          negative_review_delay_hours?: number
          auto_approve_positive?: boolean
          require_approval_negative?: boolean
          branding_keywords?: Json | null
          seo_keywords?: Json | null
          naver_id?: string | null
          naver_password_encrypted?: string | null
          naver_session_active?: boolean
          naver_last_login?: string | null
          naver_device_registered?: boolean
          naver_login_attempts?: number
          naver_profile_path?: string | null
          is_active?: boolean
          is_verified?: boolean
          verification_date?: string | null
          platform_metadata?: Json | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          store_name?: string
          business_type?: string | null
          address?: string | null
          phone?: string | null
          business_registration_number?: string | null
          platform?: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
          platform_store_id?: string
          platform_url?: string | null
          crawling_enabled?: boolean
          crawling_interval_minutes?: number
          last_crawled_at?: string | null
          next_crawl_at?: string | null
          auto_reply_enabled?: boolean
          reply_style?: 'friendly' | 'formal' | 'casual'
          custom_instructions?: string | null
          positive_reply_template?: string | null
          negative_reply_template?: string | null
          neutral_reply_template?: string | null
          negative_review_delay_hours?: number
          auto_approve_positive?: boolean
          require_approval_negative?: boolean
          branding_keywords?: Json | null
          seo_keywords?: Json | null
          naver_id?: string | null
          naver_password_encrypted?: string | null
          naver_session_active?: boolean
          naver_last_login?: string | null
          naver_device_registered?: boolean
          naver_login_attempts?: number
          naver_profile_path?: string | null
          is_active?: boolean
          is_verified?: boolean
          verification_date?: string | null
          platform_metadata?: Json | null
          created_at?: string
          updated_at?: string
        }
      }
      reviews_naver: {
        Row: {
          id: string
          platform_store_id: string
          naver_review_id: string
          naver_review_url: string | null
          reviewer_name: string | null
          reviewer_id: string | null
          reviewer_level: string | null
          rating: number | null
          review_text: string | null
          review_date: string | null
          sentiment: 'positive' | 'negative' | 'neutral' | null
          sentiment_score: number | null
          extracted_keywords: Json | null
          reply_text: string | null
          reply_status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'failed' | null
          ai_generated_reply: string | null
          ai_model_used: string | null
          ai_generation_time_ms: number | null
          ai_confidence_score: number | null
          requires_approval: boolean
          approved_by: string | null
          approved_at: string | null
          approval_notes: string | null
          reply_sent_at: string | null
          reply_failed_at: string | null
          failure_reason: string | null
          retry_count: number
          has_photos: boolean
          photo_count: number
          is_visited_review: boolean
          naver_metadata: Json | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          platform_store_id: string
          naver_review_id: string
          naver_review_url?: string | null
          reviewer_name?: string | null
          reviewer_id?: string | null
          reviewer_level?: string | null
          rating?: number | null
          review_text?: string | null
          review_date?: string | null
          sentiment?: 'positive' | 'negative' | 'neutral' | null
          sentiment_score?: number | null
          extracted_keywords?: Json | null
          reply_text?: string | null
          reply_status?: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'failed'
          ai_generated_reply?: string | null
          ai_model_used?: string | null
          ai_generation_time_ms?: number | null
          ai_confidence_score?: number | null
          requires_approval?: boolean
          approved_by?: string | null
          approved_at?: string | null
          approval_notes?: string | null
          reply_sent_at?: string | null
          reply_failed_at?: string | null
          failure_reason?: string | null
          retry_count?: number
          has_photos?: boolean
          photo_count?: number
          crawled_at?: string
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          platform_store_id?: string
          naver_review_id?: string
          naver_review_url?: string | null
          reviewer_name?: string | null
          reviewer_id?: string | null
          reviewer_level?: string | null
          rating?: number | null
          review_text?: string | null
          review_date?: string | null
          sentiment?: 'positive' | 'negative' | 'neutral' | null
          sentiment_score?: number | null
          extracted_keywords?: Json | null
          reply_text?: string | null
          reply_status?: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'failed'
          ai_generated_reply?: string | null
          ai_model_used?: string | null
          ai_generation_time_ms?: number | null
          ai_confidence_score?: number | null
          requires_approval?: boolean
          approved_by?: string | null
          approved_at?: string | null
          approval_notes?: string | null
          reply_sent_at?: string | null
          reply_failed_at?: string | null
          failure_reason?: string | null
          retry_count?: number
          has_photos?: boolean
          photo_count?: number
          crawled_at?: string
          created_at?: string
          updated_at?: string
        }
      }
      analytics: {
        Row: {
          id: string
          platform_store_id: string
          date: string
          period_type: 'daily' | 'weekly' | 'monthly'
          total_reviews: number
          new_reviews: number
          average_rating: number | null
          rating_distribution: Json | null
          positive_reviews: number
          negative_reviews: number
          neutral_reviews: number
          sentiment_trend: number | null
          total_replies: number
          ai_generated_replies: number
          manual_replies: number
          average_reply_time_hours: number | null
          reply_rate: number | null
          top_positive_keywords: Json | null
          top_negative_keywords: Json | null
          trending_keywords: Json | null
          seo_keyword_coverage: number | null
          created_at: string
        }
        Insert: {
          id?: string
          platform_store_id: string
          date: string
          period_type?: 'daily' | 'weekly' | 'monthly'
          total_reviews?: number
          new_reviews?: number
          average_rating?: number | null
          rating_distribution?: Json | null
          positive_reviews?: number
          negative_reviews?: number
          neutral_reviews?: number
          sentiment_trend?: number | null
          total_replies?: number
          ai_generated_replies?: number
          manual_replies?: number
          average_reply_time_hours?: number | null
          reply_rate?: number | null
          top_positive_keywords?: Json | null
          top_negative_keywords?: Json | null
          trending_keywords?: Json | null
          seo_keyword_coverage?: number | null
          created_at?: string
        }
        Update: {
          id?: string
          platform_store_id?: string
          date?: string
          period_type?: 'daily' | 'weekly' | 'monthly'
          total_reviews?: number
          new_reviews?: number
          average_rating?: number | null
          rating_distribution?: Json | null
          positive_reviews?: number
          negative_reviews?: number
          neutral_reviews?: number
          sentiment_trend?: number | null
          total_replies?: number
          ai_generated_replies?: number
          manual_replies?: number
          average_reply_time_hours?: number | null
          reply_rate?: number | null
          top_positive_keywords?: Json | null
          top_negative_keywords?: Json | null
          trending_keywords?: Json | null
          seo_keyword_coverage?: number | null
          created_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      subscription_plan: 'free' | 'basic' | 'premium' | 'enterprise'
      platform_type: 'naver' | 'baemin' | 'yogiyo' | 'coupangeats'
      reply_style: 'friendly' | 'formal' | 'casual'
      review_sentiment: 'positive' | 'negative' | 'neutral'
      reply_status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'failed'
      period_type: 'daily' | 'weekly' | 'monthly'
    }
  }
}