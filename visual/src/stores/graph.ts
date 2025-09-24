import { create } from 'zustand'
import { createSelectors } from '@/lib/utils'
import { DirectedGraph } from 'graphology'
import MiniSearch from 'minisearch'

export type RawNodeType = {
  id: string
  labels: string[]
  properties: Record<string, any>
  size: number
  x: number
  y: number
  color: string
  degree: number
}

export type RawEdgeType = {
  id: string
  source: string
  target: string
  type?: string
  properties: Record<string, any>
  dynamicId: string
}

export class RawGraph {
  nodes: RawNodeType[] = []
  edges: RawEdgeType[] = []
  nodeIdMap: Record<string, number> = {}
  edgeIdMap: Record<string, number> = {}
  edgeDynamicIdMap: Record<string, number> = {}

  getNode = (nodeId: string) => {
    const nodeIndex = this.nodeIdMap[nodeId]
    if (nodeIndex !== undefined) {
      return this.nodes[nodeIndex]
    }
    return undefined
  }

  getEdge = (edgeId: string, dynamicId: boolean = true) => {
    const edgeIndex = dynamicId ? this.edgeDynamicIdMap[edgeId] : this.edgeIdMap[edgeId]
    if (edgeIndex !== undefined) {
      return this.edges[edgeIndex]
    }
    return undefined
  }

  buildDynamicMap = () => {
    this.edgeDynamicIdMap = {}
    for (let i = 0; i < this.edges.length; i++) {
      const edge = this.edges[i]
      this.edgeDynamicIdMap[edge.dynamicId] = i
    }
  }
}

interface GraphState {
  selectedNode: string | null
  focusedNode: string | null
  selectedEdge: string | null
  focusedEdge: string | null

  rawGraph: RawGraph | null
  sigmaGraph: DirectedGraph | null
  sigmaInstance: any | null
  allDatabaseLabels: string[]

  searchEngine: MiniSearch | null

  moveToSelectedNode: boolean
  isFetching: boolean
  graphIsEmpty: boolean
  lastSuccessfulQueryLabel: string

  typeColorMap: Map<string, string>

  // 데이터셋 관련 상태
  availableDatasets: string[]
  selectedDataset: string | null
  isLoadingDatasets: boolean

  // 레이아웃 모드 상태
  layoutMode: 'forceatlas2' | 'noverlap' | 'hybrid'

  setSigmaInstance: (instance: any) => void
  setSelectedNode: (nodeId: string | null, moveToSelectedNode?: boolean) => void
  setFocusedNode: (nodeId: string | null) => void
  setSelectedEdge: (edgeId: string | null) => void
  setFocusedEdge: (edgeId: string | null) => void
  clearSelection: () => void
  reset: () => void

  setMoveToSelectedNode: (moveToSelectedNode: boolean) => void
  setGraphIsEmpty: (isEmpty: boolean) => void
  setLastSuccessfulQueryLabel: (label: string) => void

  setRawGraph: (rawGraph: RawGraph | null) => void
  setSigmaGraph: (sigmaGraph: DirectedGraph | null) => void
  setAllDatabaseLabels: (labels: string[]) => void
  setIsFetching: (isFetching: boolean) => void

  setSearchEngine: (engine: MiniSearch | null) => void
  resetSearchEngine: () => void

  setTypeColorMap: (typeColorMap: Map<string, string>) => void

  // 데이터셋 관련 액션
  setAvailableDatasets: (datasets: string[]) => void
  setSelectedDataset: (dataset: string | null) => void
  setIsLoadingDatasets: (isLoading: boolean) => void

  // 레이아웃 모드 액션
  setLayoutMode: (mode: 'forceatlas2' | 'noverlap' | 'hybrid') => void
}

const useGraphStoreBase = create<GraphState>()((set, get) => ({
  selectedNode: null,
  focusedNode: null,
  selectedEdge: null,
  focusedEdge: null,

  moveToSelectedNode: false,
  isFetching: false,
  graphIsEmpty: false,
  lastSuccessfulQueryLabel: '',

  rawGraph: null,
  sigmaGraph: null,
  sigmaInstance: null,
  allDatabaseLabels: ['*'],

  typeColorMap: new Map<string, string>(),

  searchEngine: null,

  // 데이터셋 관련 초기 상태
  availableDatasets: [],
  selectedDataset: null,
  isLoadingDatasets: false,

  // 레이아웃 모드 초기 상태 (localStorage에서 읽어오기)
  layoutMode: (typeof window !== 'undefined' ? 
    (localStorage.getItem('lightrag-layout-mode') as 'forceatlas2' | 'noverlap' | 'hybrid') || 'hybrid' 
    : 'hybrid') as 'forceatlas2' | 'noverlap' | 'hybrid',

  setGraphIsEmpty: (isEmpty: boolean) => set({ graphIsEmpty: isEmpty }),
  setLastSuccessfulQueryLabel: (label: string) => set({ lastSuccessfulQueryLabel: label }),

  setIsFetching: (isFetching: boolean) => set({ isFetching }),
  setSelectedNode: (nodeId: string | null, moveToSelectedNode?: boolean) =>
    set({ selectedNode: nodeId, moveToSelectedNode }),
  setFocusedNode: (nodeId: string | null) => set({ focusedNode: nodeId }),
  setSelectedEdge: (edgeId: string | null) => set({ selectedEdge: edgeId }),
  setFocusedEdge: (edgeId: string | null) => set({ focusedEdge: edgeId }),
  clearSelection: () =>
    set({
      selectedNode: null,
      focusedNode: null,
      selectedEdge: null,
      focusedEdge: null
    }),
  reset: () => {
    set({
      selectedNode: null,
      focusedNode: null,
      selectedEdge: null,
      focusedEdge: null,
      rawGraph: null,
      sigmaGraph: null,
      searchEngine: null,
      moveToSelectedNode: false,
      graphIsEmpty: false
    });
  },

  setRawGraph: (rawGraph: RawGraph | null) =>
    set({
      rawGraph
    }),

  setSigmaGraph: (sigmaGraph: DirectedGraph | null) => {
    set({ sigmaGraph });
  },

  setAllDatabaseLabels: (labels: string[]) => set({ allDatabaseLabels: labels }),

  setMoveToSelectedNode: (moveToSelectedNode?: boolean) => set({ moveToSelectedNode }),

  setSigmaInstance: (instance: any) => set({ sigmaInstance: instance }),

  setTypeColorMap: (typeColorMap: Map<string, string>) => set({ typeColorMap }),

  setSearchEngine: (engine: MiniSearch | null) => set({ searchEngine: engine }),
  resetSearchEngine: () => set({ searchEngine: null }),

  // 데이터셋 관련 액션 구현
  setAvailableDatasets: (datasets: string[]) => set({ availableDatasets: datasets }),
  setSelectedDataset: (dataset: string | null) => set({ selectedDataset: dataset }),
  setIsLoadingDatasets: (isLoading: boolean) => set({ isLoadingDatasets: isLoading }),

  // 레이아웃 모드 액션 구현
  setLayoutMode: (mode: 'forceatlas2' | 'noverlap' | 'hybrid') => {
    // localStorage에 저장
    if (typeof window !== 'undefined') {
      localStorage.setItem('lightrag-layout-mode', mode)
    }
    set({ layoutMode: mode })
  },
}))

const useGraphStore = createSelectors(useGraphStoreBase)

export { useGraphStore }
