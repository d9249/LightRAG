# 그래프 API

<cite>
**이 문서에서 참조한 파일**  
- [graph_routes.py](file://lightrag/api/routers/graph_routes.py) - *그래프 조회 및 수정 엔드포인트 정의*
- [base.py](file://lightrag/base.py) - *지식 그래프 핵심 메서드 구현*
- [types.py](file://lightrag/types.py) - *노드 및 엣지 모델 정의*
- [useLightragGraph.tsx](file://lightrag_webui/src/hooks/useLightragGraph.tsx) - *프론트엔드 그래프 상태 관리 및 시각화 로직*
- [lightrag.ts](file://lightrag_webui/src/api/lightrag.ts) - *API 클라이언트 함수 정의*
</cite>

## 업데이트 요약
**변경 사항**   
- 기존 문서에 비해 `graph_routes.py`의 실제 코드 분석을 기반으로 정확한 엔드포인트 설명 추가
- `/graphs`, `/graph/label/popular`, `/graph/label/search` 등 새로운 엔드포인트 포함
- 요청 파라미터와 응답 구조를 코드 기반으로 정밀하게 재정의
- 프론트엔드 통합 섹션을 `useLightragGraph.tsx` 분석을 통해 상세히 보완
- 오류 처리 및 빈 결과에 대한 명확한 가이드 제공

## 목차
1. [소개](#소개)
2. [엔드포인트 개요](#엔드포인트-개요)
3. [요청 및 응답 구조](#요청-및-응답-구조)
4. [프론트엔드 통합](#프론트엔드-통합)
5. [오류 처리 및 빈 결과](#오류-처리-및-빈-결과)

## 소개
`graph_routes.py`는 LightRAG 시스템의 지식 그래프 조회 및 시각화 기능을 위한 핵심 API 엔드포인트를 정의합니다. 이 문서는 지식 그래프의 구조를 탐색하고, 특정 노드와 관계를 검색하며, 시각화에 적합한 데이터를 추출하는 방법을 설명합니다. 이러한 기능은 `lightrag_webui`와 같은 프론트엔드 애플리케이션에서 지식 그래프를 효과적으로 탐색하고 분석할 수 있도록 지원합니다.

## 엔드포인트 개요
`graph_routes.py`는 다음과 같은 주요 엔드포인트를 제공합니다:

- **`/graphs`**: 지정된 레이블을 포함하는 연결된 하위 그래프를 조회합니다. 이 엔드포인트는 지식 그래프의 구조를 탐색하는 데 사용됩니다.
- **`/graph/label/list`**: 지식 그래프 내의 모든 레이블 목록을 반환합니다. 이를 통해 사용자는 그래프 내에서 검색할 수 있는 엔터티 유형을 파악할 수 있습니다.
- **`/graph/label/popular`**: 노드 차수(degree) 기준으로 가장 연결이 많은 인기 있는 레이블 목록을 반환합니다. 기본값은 300개이며 최대 1000개까지 요청 가능합니다.
- **`/graph/label/search`**: 퍼지 매칭(fuzzy matching)을 사용하여 레이블을 검색합니다. 기본값은 50개이며 최대 100개까지 결과를 반환합니다.
- **`/graph/entity/exists`**: 지정된 이름의 엔터티가 그래프 내에 존재하는지 확인합니다. 이는 엔터티의 존재 여부를 빠르게 검증하는 데 유용합니다.
- **`/graph/entity/edit`**: 엔터티의 속성을 업데이트하거나 이름을 변경합니다. 이 기능을 통해 그래프의 내용을 동적으로 수정할 수 있습니다.
- **`/graph/relation/edit`**: 두 엔터티 간의 관계의 속성을 업데이트합니다. 관계의 설명이나 키워드를 변경할 수 있습니다.

**Section sources**
- [graph_routes.py](file://lightrag/api/routers/graph_routes.py#L1-L228) - *모든 그래프 관련 라우트 정의*

## 요청 및 응답 구조
### 요청 파라미터
- **`label`**: 조회할 시작 노드의 레이블입니다. `*`로 설정하면 모든 노드를 대상으로 조회합니다.
- **`max_depth`**: 조회할 하위 그래프의 최대 깊이를 지정합니다. 기본값은 3이며, 1 이상의 값을 지정해야 합니다.
- **`max_nodes`**: 반환할 최대 노드 수를 지정합니다. 기본값은 1000이며, 1 이상의 값을 지정해야 합니다. 이 값에 도달하면 그래프가 잘릴 수 있습니다.
- **`limit`**: `/graph/label/popular` 및 `/graph/label/search` 엔드포인트에서 반환할 항목 수를 제한합니다.
- **`q`**: `/graph/label/search` 엔드포인트에서 사용되는 검색 쿼리 문자열입니다.

### 응답 구조
응답은 `KnowledgeGraph` 객체로, 다음과 같은 구조를 가집니다:

```json
{
  "nodes": [
    {
      "id": "노드의 고유 식별자",
      "labels": ["노드의 레이블 목록"],
      "properties": {
        "entity_name": "엔터티 이름",
        "entity_type": "엔터티 유형",
        "description": "엔터티 설명",
        "source_id": "소스 ID",
        "created_at": "생성 시간"
      }
    }
  ],
  "edges": [
    {
      "id": "관계의 고유 식별자",
      "source": "출발 노드 ID",
      "target": "도착 노드 ID",
      "properties": {
        "description": "관계 설명",
        "keywords": "키워드",
        "weight": "관계 가중치",
        "source_id": "소스 ID",
        "created_at": "생성 시간"
      }
    }
  ],
  "is_truncated": "그래프가 max_nodes로 인해 잘렸는지 여부"
}
```

- **노드**: `id`, `labels`, `properties` 필드를 포함합니다. `properties`에는 엔터티의 이름, 유형, 설명 등 다양한 속성이 포함됩니다.
- **관계**: `id`, `source`, `target`, `properties` 필드를 포함합니다. `properties`에는 관계의 설명, 키워드, 가중치 등이 포함됩니다.
- **`is_truncated` 플래그**: `max_nodes` 제한으로 인해 그래프가 잘렸는지 여부를 나타냅니다. 이 정보는 프론트엔드에서 사용자에게 경고를 표시하는 데 활용됩니다.

**Section sources**
- [base.py](file://lightrag/base.py#L652-L666) - *get_knowledge_graph 메서드 정의*
- [types.py](file://lightrag/types.py#L11-L28) - *KnowledgeGraphNode, KnowledgeGraphEdge, KnowledgeGraph 모델 정의*

## 프론트엔드 통합
`lightrag_webui`는 `cytoscape.js`와 유사한 라이브러리를 사용하여 지식 그래프를 시각화합니다. `queryGraphs` 함수는 `/graphs` 엔드포인트를 호출하여 그래프 데이터를 가져옵니다. 가져온 데이터는 노드와 관계의 위치, 크기, 색상을 계산하여 시각적으로 표현됩니다.

- **노드 색상**: 노드의 `entity_type`에 따라 색상이 결정됩니다. 예를 들어, `person`은 파란색, `organization`은 녹색으로 표시됩니다.
- **노드 크기**: 노드의 차수(degree)에 따라 크기가 조정됩니다. 차수가 높을수록 노드가 더 큽니다.
- **관계 크기**: 관계의 `weight` 속성에 따라 두께가 조정됩니다. 가중치가 높을수록 선이 더 두꺼워집니다.

이러한 시각화는 사용자가 그래프의 구조와 중심 노드를 직관적으로 이해할 수 있도록 돕습니다.

**Section sources**
- [useLightragGraph.tsx](file://lightrag_webui/src/hooks/useLightragGraph.tsx#L0-L1168) - *그래프 상태 관리 및 시각화 로직*
- [lightrag.ts](file://lightrag_webui/src/api/lightrag.ts#L307-L314) - *queryGraphs API 클라이언트 함수 정의*

## 오류 처리 및 빈 결과
- **HTTP 500 오류**: 서버 내부 오류가 발생한 경우 반환됩니다. 예를 들어, 데이터베이스 연결 실패 또는 내부 예외가 발생하면 이 오류가 반환됩니다.
- **HTTP 400 오류**: 클라이언트 요청이 잘못된 경우 반환됩니다. 예를 들어, 유효하지 않은 파라미터가 전달되면 이 오류가 반환됩니다.
- **빈 결과**: 그래프가 비어 있거나 조회 조건에 맞는 노드가 없는 경우, 빈 `nodes` 및 `edges` 배열과 함께 HTTP 200 응답이 반환됩니다. 이는 오류가 아닌 정상적인 상태를 나타냅니다. 프론트엔드는 `is_truncated` 플래그와 함께 이 정보를 사용하여 사용자에게 적절한 메시지를 표시할 수 있습니다.

**Section sources**
- [graph_routes.py](file://lightrag/api/routers/graph_routes.py#L70-L228) - *오류 처리 로직 포함*
- [useLightragGraph.tsx](file://lightrag_webui/src/hooks/useLightragGraph.tsx#L0-L1168) - *빈 결과 처리 및 UI 반영 로직*