import Graph, { UndirectedGraph } from 'graphology'
import { useCallback, useEffect, useRef } from 'react'
import * as Constants from '@/lib/constants'
import { useGraphStore, RawGraph } from '@/stores/graph'
import seedrandom from 'seedrandom'

const TYPE_SYNONYMS: Record<string, string> = {
  'unknown': 'unknown',
  '미지': 'unknown',
  'other': 'unknown',

  'category': 'category',
  '류별': 'category',
  'type': 'category',
  '분류': 'category',

  'organization': 'organization',
  '조직': 'organization',
  'org': 'organization',
  'company': 'organization',
  '회사': 'organization',
  '기관': 'organization',

  'event': 'event',
  '사건': 'event',
  'activity': 'event',
  '활동': 'event',

  'person': 'person',
  '인물': 'person',
  'people': 'person',
  'human': 'person',
  '인': 'person',

  'animal': 'animal',
  '동물': 'animal',
  'creature': 'animal',
  '생물': 'animal',

  'geo': 'geo',
  '지리': 'geo',
  'geography': 'geo',
  '지역': 'geo',

  'location': 'location',
  '지점': 'location',
  'place': 'location',
  'address': 'location',
  '위치': 'location',
  '주소': 'location',

  'technology': 'technology',
  '기술': 'technology',
  'tech': 'technology',
  '과학기술': 'technology',

  'equipment': 'equipment',
  '설비': 'equipment',
  'device': 'equipment',
  '장비': 'equipment',

  'weapon': 'weapon',
  '무기': 'weapon',
  'arms': 'weapon',
  '군화': 'weapon',

  'object': 'object',
  '물품': 'object',
  'stuff': 'object',
  '물체': 'object',

  'group': 'group',
  '군조': 'group',
  'community': 'group',
  '사회': 'group'
};

// 节点类型到颜色的映射
const NODE_TYPE_COLORS: Record<string, string> = {
  'unknown': '#f4d371', // Yellow
  'category': '#e3493b', // GoogleRed
  'organization': '#0f705d', // Green
  'event': '#00bfa0', // Turquoise
  'person': '#4169E1', // RoyalBlue
  'animal': '#84a3e1', // SkyBlue
  'geo': '#ff99cc', // Pale Pink
  'location': '#cf6d17', // Carrot
  'technology': '#b300b3', // Purple
  'equipment': '#2F4F4F', // DarkSlateGray
  'weapon': '#4421af', // DeepPurple
  'object': '#00cc00', // Green
  'group': '#0f558a', // NavyBlue
};

// Extended colors pool - Used for unknown node types
const EXTENDED_COLORS = [
  '#5a2c6d', // DeepViolet
  '#0000ff', // Blue
  '#cd071e', // ChinaRed
  '#00CED1', // DarkTurquoise
  '#9b3a31', // DarkBrown
  '#b2e061', // YellowGreen
  '#bd7ebe', // LightViolet
  '#6ef7b3', // LightGreen
  '#003366', // DarkBlue
  '#DEB887', // BurlyWood
];

// 향상된 엔티티 분류 함수
const classifyEntity = (entityName: string): string => {
  const name = entityName.toLowerCase()
  
  // 인물 (파란색) - RoyalBlue
  if (name.includes('씨') || name.includes('님') || name.includes('사람') || 
      name.includes('고객') || name.includes('환자') || name.includes('의사') || 
      name.includes('변호사') || name.includes('회장') || name.includes('대표') ||
      name.includes('직원') || name.includes('관리자') || name.match(/[가-힣]+님$/)) {
    return 'person'
  }
  
  // 조직/기관 (녹색) - Green
  if (name.includes('회사') || name.includes('보험') || name.includes('은행') || 
      name.includes('병원') || name.includes('법원') || name.includes('정부') || 
      name.includes('부서') || name.includes('팀') || name.includes('그룹') ||
      name.includes('생명') || name.includes('기관') || name.includes('센터') ||
      name.includes('abl') || name.match(/.*보험.*회사/)) {
    return 'organization'
  }
  
  // 장소/위치 (주황색) - Carrot
  if (name.includes('시') || name.includes('구') || name.includes('동') || 
      name.includes('로') || name.includes('길') || name.includes('지역') ||
      name.includes('위치') || name.includes('주소') || name.includes('장소')) {
    return 'location'
  }
  
  // 의료/질병 (분홍색) - Pale Pink
  if (name.includes('암') || name.includes('병') || name.includes('치료') || 
      name.includes('진단') || name.includes('수술') || name.includes('약') || 
      name.includes('증상') || name.includes('질환') || name.includes('의료') ||
      name.includes('건강') || name.includes('질병') || name.includes('갑상선') ||
      name.includes('심장') || name.includes('수질성') || name.includes('재활')) {
    return 'geo'  // WebUI에서는 의료를 geo 카테고리로 분류
  }
  
  // 금융/보험 (보라색) - Purple  
  if (name.includes('보험금') || name.includes('금') || name.includes('원') || 
      name.includes('율') || name.includes('이자') || name.includes('대출') || 
      name.includes('투자') || name.includes('수익') || name.includes('료') ||
      name.includes('비용') || name.includes('가격') || name.includes('연금') ||
      name.includes('적립') || name.includes('배당') || name.includes('수익률')) {
    return 'technology'  // WebUI에서는 금융을 technology로 분류
  }
  
  // 법률/계약 (네이비블루) - NavyBlue
  if (name.includes('법') || name.includes('계약') || name.includes('약관') || 
      name.includes('소송') || name.includes('판결') || name.includes('권리') || 
      name.includes('의무') || name.includes('조항') || name.includes('규정') ||
      name.includes('청약') || name.includes('해지') || name.includes('철회')) {
    return 'group'
  }
  
  // 제품/서비스 (초록색) - Green
  if (name.includes('서비스') || name.includes('상품') || name.includes('제품') || 
      name.includes('특약') || name.includes('보장') || name.includes('혜택') ||
      name.includes('프로그램') || name.includes('상담') || name.includes('지원')) {
    return 'object'
  }
  
  // 기술/시스템 (다크슬레이트그레이) - DarkSlateGray
  if (name.includes('코드') || name.includes('qr') || name.includes('앱') || 
      name.includes('ai') || name.includes('디지털') || name.includes('온라인') ||
      name.includes('시스템') || name.includes('view') || name.includes('프로그램')) {
    return 'equipment'
  }
  
  // 이벤트/활동 (터키색) - Turquoise
  if (name.includes('이벤트') || name.includes('활동') || name.includes('행사') || 
      name.includes('프로세스') || name.includes('절차') || name.includes('과정') ||
      name.includes('납입') || name.includes('지급') || name.includes('면제')) {
    return 'event'
  }
  
  // 카테고리/분류 (구글레드) - GoogleRed
  if (name.includes('분류표') || name.includes('표') || name.includes('목록') ||
      name.includes('형') || name.includes('종류') || name.includes('유형') ||
      name.match(/.*형$/) || name.match(/.*표$/)) {
    return 'category'
  }
  
  return 'unknown'  // 기본값 (노란색)
}

// Select color based on node type
const getNodeColorByType = (nodeType: string | undefined): string => {
  const defaultColor = '#f4d371';  // 노란색 (unknown)
  const normalizedType = nodeType ? nodeType.toLowerCase() : 'unknown';
  
  // 직접 색상 매핑
  const color = NODE_TYPE_COLORS[normalizedType] || defaultColor;
  
  return color;
};

export type NodeType = {
  x: number
  y: number
  label: string
  size: number
  color: string
  highlighted?: boolean
}

export type EdgeType = {
  label: string
  originalWeight?: number
  size?: number
  color?: string
  hidden?: boolean
}

// datasets.json에서만 데이터셋 목록 로드 (fallback 없음)
const getAvailableDatasets = async (): Promise<string[]> => {
  try {
    console.log('🔍 Loading datasets from datasets.json...')
    
    // 생성된 datasets.json 파일에서만 목록 로드
    const datasetsResponse = await fetch('./datasets.json')
    if (!datasetsResponse.ok) {
      throw new Error('datasets.json not found')
    }
    
    const datasetsInfo = await datasetsResponse.json()
    const datasets = datasetsInfo.datasets || []
    
    console.log(`✅ Found ${datasets.length} datasets:`, datasets)
    return datasets
  } catch (error) {
    console.error('❌ Error loading datasets.json:', error)
    // 최소한의 기본값만 반환
    return []
  }
}

// 선택된 데이터셋 로드 함수
const loadLocalGraphData = async (selectedDataset: string = 'ABL') => {
  try {
    console.log(`🔄 Loading dataset: ${selectedDataset}`)
    
    // 선택된 데이터셋 경로
    const entitiesResponse = await fetch(`./data/${selectedDataset}/kv_store_full_entities.json`)
    const relationsResponse = await fetch(`./data/${selectedDataset}/kv_store_full_relations.json`)
    
    console.log('📡 Fetch responses:', {
      dataset: selectedDataset,
      entities: entitiesResponse.status,
      relations: relationsResponse.status
    })
    
    if (!entitiesResponse.ok || !relationsResponse.ok) {
      throw new Error(`Failed to load dataset: ${selectedDataset}`)
    }
    
    const entitiesData = await entitiesResponse.json()
    const relationsData = await relationsResponse.json()
    
    // 엔티티 수집
    const allEntities = new Set<string>()
    for (const [, docData] of Object.entries(entitiesData)) {
      if (typeof docData === 'object' && docData && 'entity_names' in docData) {
        const entityNames = (docData as any).entity_names
        if (Array.isArray(entityNames)) {
          entityNames.forEach((name: string) => {
            if (name && typeof name === 'string') {
              allEntities.add(name)
            }
          })
        }
      }
    }
    
    // 관계 수집
    const allRelations: [string, string][] = []
    for (const [, docData] of Object.entries(relationsData)) {
      if (typeof docData === 'object' && docData && 'relation_pairs' in docData) {
        const pairs = (docData as any).relation_pairs
        if (Array.isArray(pairs)) {
          for (const pair of pairs) {
            if (Array.isArray(pair) && pair.length === 2) {
              const [source, target] = pair
              if (typeof source === 'string' && typeof target === 'string' && 
                  allEntities.has(source) && allEntities.has(target)) {
                allRelations.push([source, target])
              }
            }
          }
        }
      }
    }
    
    // 노드 생성 (카테고리별 분류 적용)
    const nodes: any[] = Array.from(allEntities).map(entity => {
      const category = classifyEntity(entity)  // 엔티티를 카테고리로 분류
      return {
        id: entity,
        labels: [entity],
        properties: {
          entity_id: entity,
          entity_type: category,  // 분류된 카테고리 적용
          description: `Category: ${category}`,
          source_id: '',
          file_path: '',
          created_at: 0
        }
      }
    })
    
    // 엣지 생성
    const edges: any[] = []
    const edgeMap = new Map<string, number>()
    
    allRelations.forEach(([source, target]) => {
      const key = `${source}→${target}` // 특수 문자로 구분
      edgeMap.set(key, (edgeMap.get(key) || 0) + 1)
    })
    
    let edgeId = 0
    edgeMap.forEach((weight, key) => {
      const [source, target] = key.split('→')
      if (allEntities.has(source) && allEntities.has(target)) {
        edges.push({
          id: `edge-${edgeId++}`,
          source: source,
          target: target,
          type: 'RELATES_TO',
          properties: { weight: weight, keywords: '', description: '' }
        })
      }
    })
    
    return { nodes, edges, is_truncated: false }
  } catch (error) {
    console.error('Error loading data:', error)
    return { nodes: [], edges: [], is_truncated: false }
  }
}

// Create a new graph instance with the raw graph data
const createSigmaGraph = (rawGraph: RawGraph | null) => {
  // Skip graph creation if no data or empty nodes
  if (!rawGraph || !rawGraph.nodes.length) {
    console.log('No graph data available, skipping sigma graph creation');
    return null;
  }

  // Create new graph instance
  const graph = new UndirectedGraph()

  // Add nodes from raw graph data
  for (const rawNode of rawGraph?.nodes ?? []) {
    // Ensure we have fresh random positions for nodes
    seedrandom(rawNode.id + Date.now().toString(), { global: true })
    const x = Math.random()
    const y = Math.random()

    graph.addNode(rawNode.id, {
      label: rawNode.labels.join(', '),
      color: rawNode.color,
      x: x,
      y: y,
      size: rawNode.size,
      // for node-border
      borderColor: Constants.nodeBorderColor,
      borderSize: 0.2
    })
  }

  // Add edges from raw graph data (노드 존재 여부 검증)
  for (const rawEdge of rawGraph?.edges ?? []) {
    // 소스와 타겟 노드가 그래프에 존재하는지 확인
    if (!graph.hasNode(rawEdge.source)) {
      console.warn(`Source node not found: ${rawEdge.source}`)
      continue
    }
    if (!graph.hasNode(rawEdge.target)) {
      console.warn(`Target node not found: ${rawEdge.target}`)
      continue
    }

    // Get weight from edge properties or default to 1
    const weight = rawEdge.properties?.weight !== undefined ? Number(rawEdge.properties.weight) : 1

    try {
      rawEdge.dynamicId = graph.addEdge(rawEdge.source, rawEdge.target, {
        label: rawEdge.properties?.keywords || undefined,
        size: weight, // Set initial size based on weight
        originalWeight: weight, // Store original weight for recalculation
        type: 'curvedNoArrow' // Explicitly set edge type to no arrow
      })
    } catch (error) {
      console.error(`Failed to add edge ${rawEdge.source} -> ${rawEdge.target}:`, error)
    }
  }

  return graph
}

const useLightragGraph = () => {
  const rawGraph = useGraphStore.use.rawGraph()
  const sigmaGraph = useGraphStore.use.sigmaGraph()
  const isFetching = useGraphStore.use.isFetching()
  const selectedDataset = useGraphStore.use.selectedDataset()
  const availableDatasets = useGraphStore.use.availableDatasets()
  const isLoadingDatasets = useGraphStore.use.isLoadingDatasets()

  // Use ref to track if data has been loaded
  const dataLoadedRef = useRef(false)
  const lastLoadedDatasetRef = useRef<string | null>(null)

  const getNode = useCallback(
    (nodeId: string) => {
      return rawGraph?.getNode(nodeId) || null
    },
    [rawGraph]
  )

  const getEdge = useCallback(
    (edgeId: string, dynamicId: boolean = true) => {
      return rawGraph?.getEdge(edgeId, dynamicId) || null
    },
    [rawGraph]
  )

  // 데이터셋 목록 로드
  useEffect(() => {
    if (availableDatasets.length === 0 && !isLoadingDatasets) {
      const state = useGraphStore.getState()
      state.setIsLoadingDatasets(true)
      
      getAvailableDatasets().then((datasets) => {
        state.setAvailableDatasets(datasets)
        state.setIsLoadingDatasets(false)
        
        // 첫 번째 데이터셋을 기본으로 선택 (사용자가 선택하지 않은 경우)
        if (datasets.length > 0 && !selectedDataset) {
          state.setSelectedDataset(datasets[0])
        }
      }).catch((error) => {
        console.error('Error loading datasets:', error)
        state.setIsLoadingDatasets(false)
      })
    }
  }, [availableDatasets.length, isLoadingDatasets, selectedDataset])

  // Graph data loading logic - 선택된 데이터셋이 변경되거나 처음 로드할 때
  useEffect(() => {
    if (!isFetching && selectedDataset && 
        (lastLoadedDatasetRef.current !== selectedDataset || !dataLoadedRef.current)) {
      const state = useGraphStore.getState()
      state.setIsFetching(true)

      console.log(`Loading graph data for dataset: ${selectedDataset}`)

      loadLocalGraphData(selectedDataset).then((rawData) => {
        if (!rawData || !rawData.nodes || !rawData.nodes.length) {
          state.setIsFetching(false)
          state.setGraphIsEmpty(true)
          return
        }

        // 간단한 데이터 처리
        const nodeIdMap: Record<string, number> = {}
        const edgeIdMap: Record<string, number> = {}

        // 노드 기본 설정
        for (let i = 0; i < rawData.nodes.length; i++) {
          const node = rawData.nodes[i]
          nodeIdMap[node.id] = i
          node.x = Math.random()
          node.y = Math.random()
          node.degree = 0
          node.size = 10
        }

        // 연결도 계산
        for (let i = 0; i < rawData.edges.length; i++) {
          const edge = rawData.edges[i]
          edgeIdMap[edge.id] = i
          const source = nodeIdMap[edge.source]
          const target = nodeIdMap[edge.target]
          if (source !== undefined && target !== undefined) {
            rawData.nodes[source].degree += 1
            rawData.nodes[target].degree += 1
          }
        }

        // 노드 크기 설정
        let minDegree = Math.min(...rawData.nodes.map(n => n.degree))
        let maxDegree = Math.max(...rawData.nodes.map(n => n.degree))
        const range = maxDegree - minDegree || 1
        const scale = Constants.maxNodeSize - Constants.minNodeSize

        // 노드 크기 및 색상 설정 (카테고리별 분류 적용)
        const categoryStats = new Map<string, number>()
        
        rawData.nodes.forEach(node => {
          // 크기 설정
          node.size = Math.round(Constants.minNodeSize + scale * Math.pow((node.degree - minDegree) / range, 0.5))
          
          // 엔티티 재분류 (더 정확한 분류를 위해)
          const actualCategory = classifyEntity(node.id)
          node.properties.entity_type = actualCategory
          
          // 색상 적용
          node.color = getNodeColorByType(actualCategory)
          
          // 통계 수집
          categoryStats.set(actualCategory, (categoryStats.get(actualCategory) || 0) + 1)
        })
        
        // 카테고리별 통계 출력
        console.log('🎨 카테고리별 노드 분포:')
        Array.from(categoryStats.entries())
          .sort((a, b) => b[1] - a[1])
          .forEach(([category, count]) => {
            const color = NODE_TYPE_COLORS[category] || '#f4d371'
            const percentage = ((count / rawData.nodes.length) * 100).toFixed(1)
            console.log(`   ${category}: ${count}개 (${percentage}%) - ${color}`)
          })

        // RawGraph 생성
        const rawGraph = new RawGraph()
        rawGraph.nodes = rawData.nodes
        rawGraph.edges = rawData.edges
        rawGraph.nodeIdMap = nodeIdMap
        rawGraph.edgeIdMap = edgeIdMap

        // SigmaGraph 생성
        const newSigmaGraph = createSigmaGraph(rawGraph)
        if (newSigmaGraph) {
          rawGraph.buildDynamicMap()
        }

        // Store 업데이트
        state.setSigmaGraph(newSigmaGraph)
        state.setRawGraph(rawGraph)
        state.setGraphIsEmpty(false)
        state.setIsFetching(false)

        console.log(`Graph loaded for ${selectedDataset}:`, { nodes: rawData.nodes.length, edges: rawData.edges.length })
        dataLoadedRef.current = true
        lastLoadedDatasetRef.current = selectedDataset
      }).catch((error) => {
        console.error('Error loading graph data:', error)
        state.setIsFetching(false)
        state.setGraphIsEmpty(true)
      })
    }
  }, [isFetching, selectedDataset])

  const lightragGraph = useCallback(() => {
    // If we already have a graph instance, return it
    if (sigmaGraph) {
      return sigmaGraph as Graph<NodeType, EdgeType>
    }

    // If no graph exists yet, create a new one and store it
    console.log('Creating new Sigma graph instance')
    const graph = new UndirectedGraph()
    useGraphStore.getState().setSigmaGraph(graph)
    return graph as Graph<NodeType, EdgeType>
  }, [sigmaGraph])

  // 데이터셋 선택 함수
  const selectDataset = useCallback((dataset: string) => {
    const state = useGraphStore.getState()
    state.setSelectedDataset(dataset)
    // 그래프 상태 초기화
    state.setRawGraph(null)
    state.setSigmaGraph(null)
    dataLoadedRef.current = false
  }, [])

  return { 
    lightragGraph, 
    getNode, 
    getEdge, 
    availableDatasets, 
    selectedDataset, 
    isLoadingDatasets, 
    selectDataset,
    getAvailableDatasets
  }
}

export default useLightragGraph
