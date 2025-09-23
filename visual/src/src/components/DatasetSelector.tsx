import { useState } from 'react'

interface DatasetSelectorProps {
  availableDatasets: string[]
  selectedDataset: string | null
  isLoadingDatasets: boolean
  onSelectDataset: (dataset: string) => void
}

const DatasetSelector = ({ 
  availableDatasets, 
  selectedDataset, 
  isLoadingDatasets, 
  onSelectDataset 
}: DatasetSelectorProps) => {
  const [isOpen, setIsOpen] = useState(false)

  if (isLoadingDatasets) {
    return (
      <div style={{
        position: 'absolute',
        top: '8px',
        right: '8px',
        background: 'rgba(9, 9, 11, 0.6)',
        backdropFilter: 'blur(16px)',
        border: '2px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '12px',
        padding: '12px',
        color: 'white',
        fontSize: '14px',
        zIndex: 1000
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            height: '16px',
            width: '16px',
            borderRadius: '50%',
            border: '2px solid #B2EBF2',
            borderTopColor: 'transparent',
            animation: 'spin 1s linear infinite'
          }}></div>
          데이터셋 로딩 중...
        </div>
      </div>
    )
  }

  if (availableDatasets.length === 0) {
    return (
      <div style={{
        position: 'absolute',
        top: '8px',
        right: '8px',
        background: 'rgba(9, 9, 11, 0.6)',
        backdropFilter: 'blur(16px)',
        border: '2px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '12px',
        padding: '12px',
        color: '#ff6b6b',
        fontSize: '14px',
        zIndex: 1000
      }}>
        사용 가능한 데이터셋이 없습니다
      </div>
    )
  }

  return (
    <div style={{
      position: 'absolute',
      top: '8px',
      right: '8px',
      zIndex: 1000
    }}>
      <div style={{
        background: 'rgba(9, 9, 11, 0.6)',
        backdropFilter: 'blur(16px)',
        border: '2px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '12px',
        overflow: 'hidden'
      }}>
        {/* 헤더 */}
        <div style={{
          padding: '12px',
          borderBottom: isOpen ? '1px solid rgba(255, 255, 255, 0.1)' : 'none',
          color: 'white',
          fontSize: '14px',
          fontWeight: 600
        }}>
          📊 데이터셋 선택
        </div>

        {/* 현재 선택된 데이터셋 */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{
            width: '100%',
            padding: '12px',
            background: 'transparent',
            border: 'none',
            color: 'white',
            fontSize: '14px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            borderBottom: isOpen ? '1px solid rgba(255, 255, 255, 0.1)' : 'none'
          }}
        >
          <span>{selectedDataset || '데이터셋을 선택하세요'}</span>
          <span style={{ 
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease'
          }}>
            ▼
          </span>
        </button>

        {/* 드롭다운 메뉴 */}
        {isOpen && (
          <div style={{
            maxHeight: '200px',
            overflowY: 'auto'
          }}>
            {availableDatasets.map((dataset) => (
              <button
                key={dataset}
                onClick={() => {
                  onSelectDataset(dataset)
                  setIsOpen(false)
                }}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: selectedDataset === dataset 
                    ? 'rgba(59, 130, 246, 0.3)' 
                    : 'transparent',
                  border: 'none',
                  color: 'white',
                  fontSize: '14px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  if (selectedDataset !== dataset) {
                    e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (selectedDataset !== dataset) {
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {selectedDataset === dataset && (
                    <span style={{ color: '#10b981' }}>✓</span>
                  )}
                  <span>{dataset}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default DatasetSelector
