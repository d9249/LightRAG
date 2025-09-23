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

// Select color based on node type
const getNodeColorByType = (nodeType: string | undefined): string => {
  const defaultColor = '#5D6D7E';
  const normalizedType = nodeType ? nodeType.toLowerCase() : 'unknown';
  const typeColorMap = useGraphStore.getState().typeColorMap;

  // Return previous color if already mapped
  if (typeColorMap.has(normalizedType)) {
    return typeColorMap.get(normalizedType) || defaultColor;
  }

  const standardType = TYPE_SYNONYMS[normalizedType];
  if (standardType) {
    const color = NODE_TYPE_COLORS[standardType];
    // Update color mapping
    const newMap = new Map(typeColorMap);
    newMap.set(normalizedType, color);
    useGraphStore.setState({ typeColorMap: newMap });
    return color;
  }

  // For unknown nodeTypes, use extended colors
  const usedExtendedColors = new Set(
    Array.from(typeColorMap.entries())
      .filter(([, color]) => !Object.values(NODE_TYPE_COLORS).includes(color))
      .map(([, color]) => color)
  );

  // Find and use the first unused extended color
  const unusedColor = EXTENDED_COLORS.find(color => !usedExtendedColors.has(color));
  const newColor = unusedColor || defaultColor;

  // Update color mapping
  const newMap = new Map(typeColorMap);
  newMap.set(normalizedType, newColor);
  useGraphStore.setState({ typeColorMap: newMap });

  return newColor;
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

// 사용 가능한 데이터셋 목록을 가져오는 함수
const getAvailableDatasets = async (): Promise<string[]> => {
  try {
    const datasets: string[] = []
    
    // 기본 데이터셋 체크
    try {
      const defaultResponse = await fetch('./data/kv_store_full_entities.json')
      if (defaultResponse.ok) {
        datasets.push('Default')
      }
    } catch (error) {
      console.log('Default dataset not available')
    }
    
    // 알려진 데이터셋들을 체크하고 더 많은 데이터셋을 자동으로 감지
    const possibleDatasets = [
      'ABL', 'BBL', 'CCL', 'DDL', 'EEL', // 기존 + 추가 가능한 데이터셋들
      'dataset1', 'dataset2', 'dataset3', // 일반적인 이름들
      'test', 'demo', 'sample', 'example' // 테스트용 데이터셋들
    ]
    
    // 병렬로 모든 데이터셋 체크
    const checkPromises = possibleDatasets.map(async (dataset) => {
      try {
        const testResponse = await fetch(`./data/${dataset}/kv_store_full_entities.json`)
        if (testResponse.ok) {
          return dataset
        }
      } catch (error) {
        // 무시 - 데이터셋이 존재하지 않음
      }
      return null
    })
    
    const results = await Promise.all(checkPromises)
    const foundDatasets = results.filter((dataset): dataset is string => dataset !== null)
    
    // 중복 제거하고 정렬
    const allDatasets = [...new Set([...datasets, ...foundDatasets])]
    
    console.log('Found datasets:', allDatasets)
    return allDatasets
  } catch (error) {
    console.error('Error getting available datasets:', error)
    return []
  }
}

// 간단한 로컬 데이터 로드 함수 (데이터셋 지정 가능)
const loadLocalGraphData = async (dataset?: string) => {
  try {
    // 데이터셋에 따른 경로 설정
    const basePath = dataset && dataset !== 'Default' ? `./data/${dataset}` : './data'
    
    // 로컬 파일 로드
    const entitiesResponse = await fetch(`${basePath}/kv_store_full_entities.json`)
    const relationsResponse = await fetch(`${basePath}/kv_store_full_relations.json`)
    
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
    
    // 노드 생성
    const nodes: any[] = Array.from(allEntities).map(entity => ({
      id: entity,
      labels: [entity],
      properties: {
        entity_id: entity,
        entity_type: 'unknown',
        description: '',
        source_id: '',
        file_path: '',
        created_at: 0
      }
    }))
    
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

        rawData.nodes.forEach(node => {
          node.size = Math.round(Constants.minNodeSize + scale * Math.pow((node.degree - minDegree) / range, 0.5))
          node.color = getNodeColorByType(node.properties?.entity_type)
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
