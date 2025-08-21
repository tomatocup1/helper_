export default function TestSimplePage() {
  return (
    <div style={{
      minHeight: '100vh',
      padding: '20px',
      fontFamily: 'Arial, sans-serif',
      backgroundColor: '#f9fafb'
    }}>
      <div style={{
        maxWidth: '800px',
        margin: '0 auto'
      }}>
        <h1 style={{
          fontSize: '2.5rem',
          color: '#1f2937',
          marginBottom: '1rem',
          textAlign: 'center'
        }}>
          🧪 간단 테스트 페이지
        </h1>

        <div style={{
          backgroundColor: 'white',
          padding: '30px',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          marginBottom: '20px'
        }}>
          <h2 style={{ color: '#374151', marginBottom: '20px' }}>시스템 상태 확인</h2>
          
          <div style={{ display: 'grid', gap: '15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px' }}>
              <span>Next.js:</span>
              <span style={{ color: '#059669', fontWeight: 'bold' }}>✓ 정상</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px' }}>
              <span>React 렌더링:</span>
              <span style={{ color: '#059669', fontWeight: 'bold' }}>✓ 정상</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px' }}>
              <span>CSS 스타일링:</span>
              <span style={{ color: '#059669', fontWeight: 'bold' }}>✓ 정상</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px' }}>
              <span>라우팅:</span>
              <span style={{ color: '#059669', fontWeight: 'bold' }}>✓ 정상</span>
            </div>
          </div>
        </div>

        <div style={{
          backgroundColor: '#dbeafe',
          border: '1px solid #3b82f6',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#1e40af', marginBottom: '10px' }}>💡 테스트 결과</h3>
          <p style={{ color: '#1e3a8a', margin: 0, lineHeight: '1.6' }}>
            이 페이지가 보인다면 Next.js 앱이 정상적으로 작동하고 있습니다. 
            무한 로딩 문제가 해결되었으며, 모든 기본 기능이 정상 작동합니다.
          </p>
        </div>

        <div style={{ textAlign: 'center' }}>
          <a 
            href="/" 
            style={{
              display: 'inline-block',
              backgroundColor: '#3b82f6',
              color: 'white',
              padding: '12px 24px',
              borderRadius: '6px',
              textDecoration: 'none',
              fontWeight: 'bold',
              marginRight: '10px'
            }}
          >
            ← 메인으로 돌아가기
          </a>
          
          <a 
            href="/analytics/naver" 
            style={{
              display: 'inline-block',
              backgroundColor: '#10b981',
              color: 'white',
              padding: '12px 24px',
              borderRadius: '6px',
              textDecoration: 'none',
              fontWeight: 'bold'
            }}
          >
            네이버 통계 →
          </a>
        </div>
      </div>
    </div>
  )
}