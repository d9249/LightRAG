import { useRegisterEvents, useSetSettings, useSigma } from '@react-sigma/core'
import { AbstractGraph } from 'graphology-types'
import { useLayoutForceAtlas2 } from '@react-sigma/layout-forceatlas2'
import { useEffect } from 'react'

import { EdgeType, NodeType } from '@/hooks/useLightragGraph'
import * as Constants from '@/lib/constants'

import { useGraphStore } from '@/stores/graph'

const isButtonPressed = (ev: MouseEvent | TouchEvent) => {
  if (ev.type.startsWith('mouse')) {
    if ((ev as MouseEvent).buttons !== 0) {
      return true
    }
  }
  return false
}

const GraphControl = ({ disableHoverEffect }: { disableHoverEffect?: boolean }) => {
  const sigma = useSigma<NodeType, EdgeType>()
  const registerEvents = useRegisterEvents<NodeType, EdgeType>()
  const setSettings = useSetSettings<NodeType, EdgeType>()

  const maxIterations = 100 // Default iterations
  const { assign: assignLayout } = useLayoutForceAtlas2({
    iterations: maxIterations
  })

  const selectedNode = useGraphStore.use.selectedNode()
  const focusedNode = useGraphStore.use.focusedNode()
  const selectedEdge = useGraphStore.use.selectedEdge()
  const focusedEdge = useGraphStore.use.focusedEdge()
  const sigmaGraph = useGraphStore.use.sigmaGraph()

  /**
   * When component mount or maxIterations changes
   * => ensure graph reference and apply layout
   */
  useEffect(() => {
    if (sigmaGraph && sigma) {
      // Ensure sigma binding to sigmaGraph
      try {
        if (typeof sigma.setGraph === 'function') {
          sigma.setGraph(sigmaGraph as unknown as AbstractGraph<NodeType, EdgeType>);
          console.log('Binding graph to sigma instance');
        } else {
          (sigma as any).graph = sigmaGraph;
          console.warn('Sigma missing setGraph function, set graph property directly');
        }
      } catch (error) {
        console.error('Error setting graph on sigma instance:', error);
      }

      assignLayout();
      console.log('Initial layout applied to graph');
    }
  }, [sigma, sigmaGraph, assignLayout, maxIterations])

  /**
   * Ensure the sigma instance is set in the store
   */
  useEffect(() => {
    if (sigma) {
      const currentInstance = useGraphStore.getState().sigmaInstance;
      if (!currentInstance) {
        console.log('Setting sigma instance from GraphControl');
        useGraphStore.getState().setSigmaInstance(sigma);
      }
    }
  }, [sigma]);

  /**
   * When component mount => register events
   */
  useEffect(() => {
    const { setFocusedNode, setSelectedNode, setFocusedEdge, setSelectedEdge, clearSelection } =
      useGraphStore.getState()

    // Define event types
    type NodeEvent = { node: string; event: { original: MouseEvent | TouchEvent } }
    type EdgeEvent = { edge: string; event: { original: MouseEvent | TouchEvent } }

    // Register all events
    const events: Record<string, any> = {
      enterNode: (event: NodeEvent) => {
        if (!isButtonPressed(event.event.original)) {
          const graph = sigma.getGraph()
          if (graph.hasNode(event.node)) {
            setFocusedNode(event.node)
          }
        }
      },
      leaveNode: (event: NodeEvent) => {
        if (!isButtonPressed(event.event.original)) {
          setFocusedNode(null)
        }
      },
      clickNode: (event: NodeEvent) => {
        const graph = sigma.getGraph()
        if (graph.hasNode(event.node)) {
          setSelectedNode(event.node)
          setSelectedEdge(null)
        }
      },
      clickStage: () => clearSelection(),
      clickEdge: (event: EdgeEvent) => {
        setSelectedEdge(event.edge)
        setSelectedNode(null)
      },
      enterEdge: (event: EdgeEvent) => {
        if (!isButtonPressed(event.event.original)) {
          setFocusedEdge(event.edge)
        }
      },
      leaveEdge: (event: EdgeEvent) => {
        if (!isButtonPressed(event.event.original)) {
          setFocusedEdge(null)
        }
      }
    }

    // Register the events
    registerEvents(events)
  }, [registerEvents])

  /**
   * Setting the sigma reducers for visual effects
   */
  useEffect(() => {
    const labelColor = Constants.labelColorDarkTheme
    const edgeColor = Constants.edgeColorDarkTheme

    // Update all dynamic settings
    setSettings({
      renderEdgeLabels: false,
      renderLabels: true,

      // Node reducer for node appearance
      nodeReducer: (node, data) => {
        const graph = sigma.getGraph()
        const newData: NodeType & {
          labelColor?: string
          borderColor?: string
        } = { ...data, highlighted: data.highlighted || false, labelColor }

        if (!disableHoverEffect) {
          newData.highlighted = false
          const _focusedNode = focusedNode || selectedNode
          const _focusedEdge = focusedEdge || selectedEdge

          if (_focusedNode && graph.hasNode(_focusedNode)) {
            try {
              if (node === _focusedNode || graph.neighbors(_focusedNode).includes(node)) {
                newData.highlighted = true
                if (node === selectedNode) {
                  newData.borderColor = Constants.nodeBorderColorSelected
                }
              }
            } catch (error) {
              console.error('Error in nodeReducer:', error);
            }
          } else if (_focusedEdge && graph.hasEdge(_focusedEdge)) {
            if (graph.extremities(_focusedEdge).includes(node)) {
              newData.highlighted = true
              newData.size = 3
            }
          } else {
            return newData
          }

          if (newData.highlighted) {
            newData.labelColor = Constants.LabelColorHighlightedDarkTheme
          } else {
            newData.color = Constants.nodeColorDisabled
          }
        }
        return newData
      },

      // Edge reducer for edge appearance
      edgeReducer: (edge, data) => {
        const graph = sigma.getGraph()
        const newData = { ...data, hidden: false, labelColor, color: edgeColor }

        if (!disableHoverEffect) {
          const _focusedNode = focusedNode || selectedNode

          if (_focusedNode && graph.hasNode(_focusedNode)) {
            try {
              if (graph.extremities(edge).includes(_focusedNode)) {
                newData.color = Constants.edgeColorHighlighted
              }
            } catch (error) {
              console.error('Error in edgeReducer:', error);
            }
          } else {
            const _selectedEdge = selectedEdge && graph.hasEdge(selectedEdge) ? selectedEdge : null;
            const _focusedEdge = focusedEdge && graph.hasEdge(focusedEdge) ? focusedEdge : null;

            if (_selectedEdge || _focusedEdge) {
              if (edge === _selectedEdge) {
                newData.color = Constants.edgeColorSelected
              } else if (edge === _focusedEdge) {
                newData.color = Constants.edgeColorHighlighted
              }
            }
          }
        }
        return newData
      }
    })
  }, [
    selectedNode,
    focusedNode,
    selectedEdge,
    focusedEdge,
    setSettings,
    sigma,
    disableHoverEffect
  ])

  return null
}

export default GraphControl
