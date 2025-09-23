import { useEffect } from 'react'
import GraphViewer from '@/features/GraphViewer'

// 스타일 추가
const globalStyles = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  
  * {
    box-sizing: border-box;
  }
  
  body {
    margin: 0;
    padding: 0;
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background-color: hsl(222.2, 84%, 4.9%);
    color: white;
  }
  
  #root {
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }
`

function App() {
  useEffect(() => {
    // Add global styles
    const styleSheet = document.createElement('style')
    styleSheet.textContent = globalStyles
    document.head.appendChild(styleSheet)
    
    return () => {
      document.head.removeChild(styleSheet)
    }
  }, [])

  return (
    <div style={{ height: '100vh', width: '100vw' }}>
      <GraphViewer />
    </div>
  )
}

export default App
