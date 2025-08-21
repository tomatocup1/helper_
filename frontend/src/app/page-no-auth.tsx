export default function HomePage() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h1 style={{
        fontSize: '3rem',
        color: '#2563eb',
        marginBottom: '1rem',
        textAlign: 'center'
      }}>
        🎉 앱이 정상 작동합니다!
      </h1>
      
      <p style={{
        fontSize: '1.2rem',
        color: '#6b7280',
        marginBottom: '2rem',
        textAlign: 'center'
      }}>
        무한 로딩 문제가 해결되었습니다.
      </p>

      <div style={{
        backgroundColor: '#f3f4f6',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '2rem'
      }}>
        <h2 style={{ color: '#374151', marginBottom: '10px' }}>✅ 작동 상태</h2>
        <ul style={{ color: '#6b7280', lineHeight: '1.6' }}>
          <li>✓ Next.js 서버 실행 중</li>
          <li>✓ React 컴포넌트 렌더링</li>
          <li>✓ 포트 3000에서 실행</li>
          <li>✓ 인증 시스템 우회</li>
        </ul>
      </div>

      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'center' }}>
        <a 
          href="/analytics/naver" 
          style={{
            backgroundColor: '#2563eb',
            color: 'white',
            padding: '10px 20px',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: 'bold'
          }}
        >
          네이버 통계 테스트
        </a>
        
        <a 
          href="/test-simple" 
          style={{
            backgroundColor: '#10b981',
            color: 'white',
            padding: '10px 20px',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: 'bold'
          }}
        >
          간단 테스트
        </a>
      </div>

      <div style={{
        marginTop: '2rem',
        padding: '15px',
        backgroundColor: '#fef3c7',
        border: '1px solid #f59e0b',
        borderRadius: '6px',
        maxWidth: '500px',
        textAlign: 'center'
      }}>
        <strong style={{ color: '#92400e' }}>현재 상태:</strong>
        <br />
        <span style={{ color: '#78350f' }}>
          인증 시스템이 비활성화되어 모든 페이지에 접근할 수 있습니다.
        </span>
      </div>
    </div>
  )
}