import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { SigmaContainer, useRegisterEvents, useSigma } from '@react-sigma/core'
import { Settings as SigmaSettings } from 'sigma/settings'
import { EdgeArrowProgram, NodePointProgram, NodeCircleProgram } from 'sigma/rendering'
import { NodeBorderProgram } from '@sigma/node-border'
import { EdgeCurvedArrowProgram, createEdgeCurveProgram } from '@sigma/edge-curve'

import GraphControl from '@/components/graph/GraphControl'

import { useGraphStore } from '@/stores/graph'

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

  const selectedNode = useGraphStore.use.selectedNode()
  const focusedNode = useGraphStore.use.focusedNode()
  const moveToSelectedNode = useGraphStore.use.moveToSelectedNode()
  const isFetching = useGraphStore.use.isFetching()

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

  const autoFocusedNode = useMemo(() => focusedNode ?? selectedNode, [focusedNode, selectedNode])

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

        {/* Basic controls */}
        <div style={{
          position: 'absolute',
          top: '8px',
          left: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          background: 'rgba(9, 9, 11, 0.6)',
          backdropFilter: 'blur(16px)',
          border: '2px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '12px',
          padding: '8px',
          zIndex: 1000
        }}>
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
              padding: '8px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            📐 Fit View
          </button>
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
          <div>Style: WebUI Exact React</div>
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
