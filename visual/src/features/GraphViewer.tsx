import { useEffect, useState, useRef } from 'react'
import { SigmaContainer, useRegisterEvents, useSigma } from '@react-sigma/core'
import { Settings as SigmaSettings } from 'sigma/settings'
import { EdgeArrowProgram, NodePointProgram, NodeCircleProgram } from 'sigma/rendering'
import { NodeBorderProgram } from '@sigma/node-border'
import { EdgeCurvedArrowProgram, createEdgeCurveProgram } from '@sigma/edge-curve'

import GraphControl from '@/components/graph/GraphControl'
import DatasetSelector from '@/components/DatasetSelector'

import { useGraphStore } from '@/stores/graph'
import useLightragGraph from '@/hooks/useLightragGraph'

import '@react-sigma/core/lib/style.css'

// Sigma settings (WebUI와 정확히 동일)
const defaultSigmaSettings: Partial<SigmaSettings> = {
  allowInvalidContainer: true,
  defaultNodeType: 'default',  // WebUI와 동일
  defaultEdgeType: 'curvedNoArrow',
  renderEdgeLabels: false,
  edgeProgramClasses: {
    arrow: EdgeArrowProgram,
    curvedArrow: EdgeCurvedArrowProgram,
    curvedNoArrow: createEdgeCurveProgram()
  },
  nodeProgramClasses: {
    default: NodeBorderProgram,  // WebUI와 동일: default가 NodeBorderProgram
    circel: NodeCircleProgram,
    point: NodePointProgram
  },
  labelGridCellSize: 60,
  labelRenderedSizeThreshold: 12,
  enableEdgeEvents: true,
  labelColor: {
    color: '#000',  // WebUI와 동일: 검은색 라벨
    attribute: 'labelColor'
  },
  edgeLabelColor: {
    color: '#000',  // WebUI와 동일: 검은색 엣지 라벨
    attribute: 'labelColor'
  },
  edgeLabelSize: 8,
  labelSize: 12
}

const GraphEvents = () => {
  const registerEvents = useRegisterEvents()
  const sigma = useSigma()
  const [draggedNode, setDraggedNode] = useState<string | null>(null)

  useEffect(() => {
    // Register the events
    registerEvents({
      downNode: (e) => {
        setDraggedNode(e.node)
        sigma.getGraph().setNodeAttribute(e.node, 'highlighted', true)
      },
      // On mouse move, if the drag mode is enabled, we change the position of the draggedNode
      mousemovebody: (e) => {
        if (!draggedNode) return
        // Get new position of node
        const pos = sigma.viewportToGraph(e)
        sigma.getGraph().setNodeAttribute(draggedNode, 'x', pos.x)
        sigma.getGraph().setNodeAttribute(draggedNode, 'y', pos.y)

        // Prevent sigma to move camera:
        e.preventSigmaDefault()
        e.original.preventDefault()
        e.original.stopPropagation()
      },
      // On mouse up, we reset the autoscale and the dragging mode
      mouseup: () => {
        if (draggedNode) {
          setDraggedNode(null)
          sigma.getGraph().removeNodeAttribute(draggedNode, 'highlighted')
        }
      },
      // Disable the autoscale at the first down interaction
      mousedown: (e) => {
        // Only set custom BBox if it's a drag operation (mouse button is pressed)
        const mouseEvent = e.original as MouseEvent;
        if (mouseEvent.buttons !== 0 && !sigma.getCustomBBox()) {
          sigma.setCustomBBox(sigma.getBBox())
        }
      }
    })
  }, [registerEvents, sigma, draggedNode])

  return null
}

const GraphViewer = () => {
  const [sigmaSettings, setSigmaSettings] = useState(defaultSigmaSettings)
  const sigmaRef = useRef<any>(null)

  const isFetching = useGraphStore.use.isFetching()
  const layoutMode = useGraphStore.use.layoutMode()
  const setLayoutMode = useGraphStore.use.setLayoutMode()

  // 데이터셋 관련 상태와 함수들
  const { 
    availableDatasets, 
    selectedDataset, 
    isLoadingDatasets, 
    selectDataset 
  } = useLightragGraph()

  // 레이아웃 변경 함수
  const handleLayoutModeChange = (mode: 'forceatlas2' | 'noverlap' | 'hybrid') => {
    console.log(`Changing layout mode to: ${mode}`)
    setLayoutMode(mode)
    // 새로고침 대신 상태 변경만 - useEffect에서 실시간으로 레이아웃 적용됨
  }

  // Initialize sigma settings once on component mount
  useEffect(() => {
    setSigmaSettings(defaultSigmaSettings)
    console.log('Initialized sigma settings')
  }, [])

  // Clean up sigma instance when component unmounts
  useEffect(() => {
    return () => {
      const sigma = useGraphStore.getState().sigmaInstance;
      if (sigma) {
        try {
          sigma.kill();
          useGraphStore.getState().setSigmaInstance(null);
          console.log('Cleared sigma instance on GraphViewer unmount');
        } catch (error) {
          console.error('Error cleaning up sigma instance:', error);
        }
      }
    };
  }, []);


  // Always render SigmaContainer but control its visibility with CSS
  return (
    <div style={{ position: 'relative', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: 'hsl(222.2, 84%, 4.9%)' }}>
      <SigmaContainer
        settings={sigmaSettings}
        style={{ height: '100%', width: '100%', backgroundColor: 'hsl(222.2, 84%, 4.9%)' }}
        ref={sigmaRef}
      >
        <GraphControl />
        <GraphEvents />

        {/* 데이터셋 선택기 */}
        <DatasetSelector
          availableDatasets={availableDatasets}
          selectedDataset={selectedDataset}
          isLoadingDatasets={isLoadingDatasets}
          onSelectDataset={selectDataset}
        />

        {/* Enhanced controls */}
        <div style={{
          position: 'absolute',
          top: '8px',
          left: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          background: 'rgba(9, 9, 11, 0.6)',
          backdropFilter: 'blur(16px)',
          border: '2px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '12px',
          padding: '12px',
          zIndex: 1000,
          minWidth: '200px'
        }}>
          {/* 레이아웃 모드 선택 */}
          <div>
            <h4 style={{ 
              margin: '0 0 8px 0', 
              fontSize: '12px', 
              fontWeight: 600, 
              color: 'white',
              textAlign: 'center'
            }}>
              🎨 Layout Mode
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: 'white',
                fontSize: '11px',
                cursor: 'pointer'
              }}>
                <input
                  type="radio"
                  name="layout"
                  checked={layoutMode === 'forceatlas2'}
                  onChange={() => handleLayoutModeChange('forceatlas2')}
                  style={{ accentColor: '#B2EBF2' }}
                />
                🌟 Force Atlas 2 Only
              </label>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: 'white',
                fontSize: '11px',
                cursor: 'pointer'
              }}>
                <input
                  type="radio"
                  name="layout"
                  checked={layoutMode === 'noverlap'}
                  onChange={() => handleLayoutModeChange('noverlap')}
                  style={{ accentColor: '#B2EBF2' }}
                />
                🔧 Anti-Overlap Only
              </label>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: '#B2EBF2',
                fontSize: '11px',
                cursor: 'pointer',
                fontWeight: layoutMode === 'hybrid' ? 600 : 400
              }}>
                <input
                  type="radio"
                  name="layout"
                  checked={layoutMode === 'hybrid'}
                  onChange={() => handleLayoutModeChange('hybrid')}
                  style={{ accentColor: '#B2EBF2' }}
                />
                ⚡ Hybrid (Recommended)
              </label>
            </div>
          </div>

          {/* 구분선 */}
          <div style={{
            height: '1px',
            background: 'rgba(255, 255, 255, 0.1)',
            margin: '4px 0'
          }}></div>

          {/* 기본 컨트롤 버튼들 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <button
              onClick={() => {
                const sigma = useGraphStore.getState().sigmaInstance
                if (sigma) {
                  sigma.getCamera().animate({ x: 0, y: 0, ratio: 1 }, { duration: 1000 })
                }
              }}
              style={{
                background: 'transparent',
                color: 'white',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                padding: '6px 10px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              📐 Fit View
            </button>
            
            <button
              onClick={() => {
                const sigma = useGraphStore.getState().sigmaInstance
                if (sigma && sigma.getGraph) {
                  const graph = sigma.getGraph()
                  if (graph && graph.order > 0) {
                    // 현재 레이아웃 모드 강제 재적용
                    const currentMode = useGraphStore.getState().layoutMode
                    console.log(`Re-applying ${currentMode} layout`)
                    
                    // 강제로 레이아웃을 다시 트리거하기 위해 잠시 다른 모드로 변경 후 원래대로
                    const tempMode = currentMode === 'hybrid' ? 'forceatlas2' : 'hybrid'
                    setLayoutMode(tempMode)
                    setTimeout(() => {
                      setLayoutMode(currentMode)
                    }, 100)
                  }
                }
              }}
              style={{
                background: 'transparent',
                color: '#B2EBF2',
                border: '1px solid rgba(178, 235, 242, 0.3)',
                padding: '6px 10px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
              title="현재 선택된 레이아웃 모드를 다시 적용합니다"
            >
              🔄 Apply Layout
            </button>
            
            <button
              onClick={() => {
                const sigma = useGraphStore.getState().sigmaInstance
                if (sigma) {
                  const graph = sigma.getGraph()
                  graph.forEachNode((node: string) => {
                    graph.setNodeAttribute(node, 'x', Math.random() * 2 - 1)
                    graph.setNodeAttribute(node, 'y', Math.random() * 2 - 1)
                  })
                  sigma.refresh()
                  // 새로고침 대신 현재 레이아웃 다시 적용
                  setTimeout(() => {
                    const currentMode = useGraphStore.getState().layoutMode
                    const tempMode = currentMode === 'hybrid' ? 'forceatlas2' : 'hybrid'
                    setLayoutMode(tempMode)
                    setTimeout(() => setLayoutMode(currentMode), 100)
                  }, 100)
                }
              }}
              style={{
                background: 'transparent',
                color: '#F57F17',
                border: '1px solid rgba(245, 127, 23, 0.3)',
                padding: '6px 10px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
              title="노드를 랜덤하게 재배치하고 새로운 레이아웃을 적용합니다"
            >
              🎲 Reshuffle
            </button>
          </div>
        </div>

        {/* Stats panel */}
        <div style={{
          position: 'absolute',
          bottom: '8px',
          left: '8px',
          background: 'rgba(9, 9, 11, 0.6)',
          backdropFilter: 'blur(16px)',
          border: '2px solid rgba(255, 255, 255, 0.1)',
          color: 'white',
          padding: '12px',
          borderRadius: '12px',
          fontSize: '12px',
          zIndex: 1000
        }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600 }}>
            Graph Statistics
          </h3>
          <div>Nodes: {useGraphStore.getState().rawGraph?.nodes.length || 0}</div>
          <div>Edges: {useGraphStore.getState().rawGraph?.edges.length || 0}</div>
          <div>Layout: {
            layoutMode === 'forceatlas2' ? 'Force Atlas 2' :
            layoutMode === 'noverlap' ? 'Anti-Overlap' :
            'Hybrid (FA2 + Noverlap)'
          }</div>
          <div style={{ fontSize: '10px', color: '#B2EBF2', marginTop: '4px' }}>
            {layoutMode === 'forceatlas2' && 'Basic force-directed layout'}
            {layoutMode === 'noverlap' && 'Overlap prevention active'}
            {layoutMode === 'hybrid' && 'Best of both algorithms'}
          </div>
        </div>

        {/* Category Legend panel */}
        <div style={{
          position: 'absolute',
          bottom: '8px',
          right: '8px',
          background: 'rgba(9, 9, 11, 0.6)',
          backdropFilter: 'blur(16px)',
          border: '2px solid rgba(255, 255, 255, 0.1)',
          color: 'white',
          padding: '12px',
          borderRadius: '12px',
          fontSize: '11px',
          maxWidth: '200px',
          zIndex: 1000
        }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 600 }}>
            🏷️ Categories
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#4169E1', borderRadius: '50%' }}></div>
              <span>👤 Person</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#0f705d', borderRadius: '50%' }}></div>
              <span>🏢 Organization</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#cf6d17', borderRadius: '50%' }}></div>
              <span>📍 Location</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#ff99cc', borderRadius: '50%' }}></div>
              <span>⚕️ Medical</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#b300b3', borderRadius: '50%' }}></div>
              <span>💰 Financial</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#0f558a', borderRadius: '50%' }}></div>
              <span>⚖️ Legal</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#00cc00', borderRadius: '50%' }}></div>
              <span>📦 Service</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#00bfa0', borderRadius: '50%' }}></div>
              <span>🎯 Event</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#e3493b', borderRadius: '50%' }}></div>
              <span>📊 Category</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#f4d371', borderRadius: '50%' }}></div>
              <span>❓ Unknown</span>
            </div>
          </div>
        </div>
      </SigmaContainer>

      {/* Loading overlay */}
      {isFetching && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(9, 9, 11, 0.8)',
          zIndex: 10
        }}>
          <div style={{ textAlign: 'center', color: 'white' }}>
            <div style={{
              marginBottom: '8px',
              height: '32px',
              width: '32px',
              borderRadius: '50%',
              border: '4px solid #B2EBF2',
              borderTopColor: 'transparent',
              animation: 'spin 1s linear infinite',
              margin: '0 auto'
            }}></div>
            <p>Loading Graph Data...</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default GraphViewer
