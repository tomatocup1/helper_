"use client"

import { useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { ko } from 'date-fns/locale'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatisticsData {
  id: string
  date: string
  place_inflow: number
  place_inflow_change: number | null
  reservation_order: number
  reservation_order_change: number | null
  smart_call: number
  smart_call_change: number | null
  review_registration: number
  review_registration_change: number | null
  inflow_channels: Array<{ rank: number; channel_name: string; count: number }>
  inflow_keywords: Array<{ rank: number; keyword: string; count: number }>
}

interface StatisticsChartProps {
  data: StatisticsData[]
  title: string
  description?: string
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7300']

export function StatisticsTrendChart({ data, title, description }: StatisticsChartProps) {
  const chartData = useMemo(() => {
    return data
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .map(item => ({
        date: format(parseISO(item.date), 'MM/dd', { locale: ko }),
        fullDate: format(parseISO(item.date), 'yyyy년 MM월 dd일', { locale: ko }),
        placeInflow: item.place_inflow,
        reservationOrder: item.reservation_order,
        smartCall: item.smart_call,
        reviewRegistration: item.review_registration
      }))
  }, [data])

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip 
                labelFormatter={(value, payload) => {
                  const item = payload?.[0]?.payload
                  return item?.fullDate || value
                }}
                formatter={(value, name) => {
                  const nameMap: Record<string, string> = {
                    placeInflow: '플레이스 유입',
                    reservationOrder: '예약·주문',
                    smartCall: '스마트콜',
                    reviewRegistration: '리뷰 등록'
                  }
                  return [value, nameMap[name] || name]
                }}
              />
              <Line 
                type="monotone" 
                dataKey="placeInflow" 
                stroke="#8884d8" 
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line 
                type="monotone" 
                dataKey="reservationOrder" 
                stroke="#82ca9d" 
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line 
                type="monotone" 
                dataKey="smartCall" 
                stroke="#ffc658" 
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line 
                type="monotone" 
                dataKey="reviewRegistration" 
                stroke="#ff7300" 
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}


export function StatisticsSummaryCards({ data }: { data: StatisticsData[] }) {
  const latestData = data?.[0]
  const previousData = data?.[1]

  if (!latestData) return null

  const metrics = [
    {
      title: '플레이스 유입',
      value: latestData.place_inflow,
      change: latestData.place_inflow_change,
      previousValue: previousData?.place_inflow,
      icon: '👁️'
    },
    {
      title: '예약·주문 신청',
      value: latestData.reservation_order,
      change: latestData.reservation_order_change,
      previousValue: previousData?.reservation_order,
      icon: '🛒'
    },
    {
      title: '스마트콜 통화',
      value: latestData.smart_call,
      change: latestData.smart_call_change,
      previousValue: previousData?.smart_call,
      icon: '📞'
    },
    {
      title: '리뷰 등록',
      value: latestData.review_registration,
      change: latestData.review_registration_change,
      previousValue: previousData?.review_registration,
      icon: '💬'
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric) => (
        <Card key={metric.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
            <span className="text-2xl">{metric.icon}</span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metric.value.toLocaleString()}</div>
            <div className="flex items-center mt-1">
              {metric.change !== null && (
                <>
                  {metric.change > 0 ? (
                    <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                  ) : metric.change < 0 ? (
                    <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
                  ) : (
                    <Minus className="w-4 h-4 text-gray-400 mr-1" />
                  )}
                  <span
                    className={`text-xs font-medium ${
                      metric.change > 0
                        ? 'text-green-600'
                        : metric.change < 0
                        ? 'text-red-600'
                        : 'text-gray-600'
                    }`}
                  >
                    {metric.change > 0 ? '+' : ''}{metric.change}%
                  </span>
                </>
              )}
              {metric.previousValue !== undefined && (
                <span className="text-xs text-muted-foreground ml-2">
                  전일: {metric.previousValue}
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// 유입 채널 분포 차트
export function InflowChannelChart({ data }: { data: StatisticsData[] }) {
  const channelData = useMemo(() => {
    if (!data || data.length === 0) return []

    // 최신 데이터의 유입 채널 정보 사용
    const latestData = data[0]
    if (!latestData.inflow_channels || latestData.inflow_channels.length === 0) {
      return []
    }

    // JSONB 데이터를 차트 데이터로 변환하고 퍼센트 계산
    const channels = latestData.inflow_channels
    const totalValue = channels.reduce((sum: number, channel: any) => sum + (channel.visits || channel.count || 0), 0)
    
    return channels.map((channel: any, index: number) => {
      const value = channel.visits || channel.count || 0
      const percentage = totalValue > 0 ? ((value / totalValue) * 100) : 0
      
      return {
        name: channel.channel_name || channel.name || `채널 ${index + 1}`,
        value: value,
        percentage: Math.round(percentage * 10) / 10 // 소수점 1자리
      }
    }).sort((a, b) => b.value - a.value) // 값 기준 내림차순 정렬
  }, [data])

  const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316']

  return (
    <Card>
      <CardHeader>
        <CardTitle>유입 채널 분포</CardTitle>
        <CardDescription>
          채널별 방문자 유입 현황
        </CardDescription>
      </CardHeader>
      <CardContent>
        {channelData.length > 0 ? (
          <div className="space-y-6">
            {/* 파이 차트 */}
            <div className="flex justify-center">
              <div className="h-72 w-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={channelData}
                      cx="50%"
                      cy="50%"
                      outerRadius={120}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {channelData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value: any, name: any, props: any) => [
                        `${value}회 (${props.payload.percentage}%)`, 
                        props.payload.name
                      ]} 
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            {/* 범례 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {channelData.map((item, index) => (
                <div key={item.name} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-4 h-4 rounded-full flex-shrink-0"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-sm truncate">{item.name}</div>
                      <div className="text-xs text-muted-foreground">{item.percentage}%</div>
                    </div>
                  </div>
                  <Badge variant="secondary" className="font-medium ml-2">
                    {item.value}회
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-muted-foreground">
            <div className="text-center">
              <p>유입 채널 데이터가 없습니다</p>
              <p className="text-sm mt-1">통계 수집 후 확인 가능합니다</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// 인기 검색 키워드 차트
export function InflowKeywordChart({ data }: { data: StatisticsData[] }) {
  const keywordData = useMemo(() => {
    if (!data || data.length === 0) return []

    // 최신 데이터의 검색 키워드 정보 사용
    const latestData = data[0]
    if (!latestData.inflow_keywords || latestData.inflow_keywords.length === 0) {
      return []
    }

    // JSONB 데이터를 차트 데이터로 변환하고 퍼센트 계산 (상위 8개만)
    const keywords = latestData.inflow_keywords.slice(0, 8)
    const totalCount = keywords.reduce((sum: number, keyword: any) => sum + (keyword.visits || keyword.count || keyword.searches || 0), 0)
    
    return keywords.map((keyword: any, index: number) => {
      const count = keyword.visits || keyword.count || keyword.searches || 0
      const percentage = totalCount > 0 ? ((count / totalCount) * 100) : 0
      
      return {
        keyword: keyword.keyword || keyword.term || `키워드 ${index + 1}`,
        count: count,
        percentage: Math.round(percentage * 10) / 10, // 소수점 1자리
        rank: index + 1
      }
    }).sort((a, b) => b.count - a.count) // 검색 수 기준 내림차순 정렬
  }, [data])

  const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1']

  return (
    <Card>
      <CardHeader>
        <CardTitle>인기 검색 키워드</CardTitle>
        <CardDescription>
          상위 검색 키워드별 유입 현황
        </CardDescription>
      </CardHeader>
      <CardContent>
        {keywordData.length > 0 ? (
          <div className="space-y-6">
            {/* 파이 차트 */}
            <div className="flex justify-center">
              <div className="h-72 w-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={keywordData}
                      cx="50%"
                      cy="50%"
                      outerRadius={120}
                      fill="#8884d8"
                      dataKey="count"
                    >
                      {keywordData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value: any, name: any, props: any) => [
                        `${value}회 (${props.payload.percentage}%)`, 
                        props.payload.keyword
                      ]} 
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            {/* 범례 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {keywordData.map((item, index) => (
                <div key={item.keyword} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-4 h-4 rounded-full flex-shrink-0"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-sm truncate">{item.keyword}</div>
                      <div className="text-xs text-muted-foreground">{item.percentage}%</div>
                    </div>
                  </div>
                  <Badge variant="secondary" className="font-medium ml-2">
                    {item.count}회
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-muted-foreground">
            <div className="text-center">
              <p>검색 키워드 데이터가 없습니다</p>
              <p className="text-sm mt-1">통계 수집 후 확인 가능합니다</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}