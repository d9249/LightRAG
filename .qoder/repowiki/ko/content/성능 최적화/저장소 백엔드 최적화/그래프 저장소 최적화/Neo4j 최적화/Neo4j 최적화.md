# Neo4j 최적화

<cite>
**참조된 문서**
- [values.yaml](file://k8s-deploy/databases/neo4j/values.yaml)
- [neo4j_impl.py](file://lightrag/kg/neo4j_impl.py)
</cite>

## 목차
1. [소개](#소개)
2. [Kubernetes 배포 설정 최적화](#kubernetes-배포-설정-최적화)
3. [초기화 시 연결 풀 및 트랜잭션 설정](#초기화-시-연결-풀-및-트랜잭션-설정)
4. [인덱스 생성 전략](#인덱스-생성-전략)
5. [Cypher 쿼리 프로파일링 및 관계 탐색 최적화](#cypher-쿼리-프로파일링-및-관계-탐색-최적화)
6. [대규모 그래프 데이터 처리를 위한 캐시 및 메모리 구성](#대규모-그래프-데이터-처리를-위한-캐시-및-메모리-구성)
7. [결론](#결론)

## 소개
이 문서는 Neo4j 기반 그래프 저장소의 성능 최적화 전략을 설명합니다. Kubernetes 환경에서의 리소스 할당 조정, Neo4j 초기화 시 연결 풀 및 트랜잭션 설정, 인덱스 전략, 쿼리 최적화 패턴, 그리고 대규모 데이터 처리를 위한 메모리 구성에 대해 다룹니다. 본 문서는 `k8s-deploy/databases/neo4j/values.yaml` 파일과 `lightrag/kg/neo4j_impl.py` 구현을 기반으로 합니다.

## Kubernetes 배포 설정 최적화

Neo4j의 성능은 Kubernetes 환경에서의 리소스 할당에 크게 영향을 받습니다. `k8s-deploy/databases/neo4j/values.yaml` 파일을 통해 CPU, 메모리, 스토리지 볼륨 크기 및 복제본 수를 조정할 수 있습니다.

### CPU 및 메모리 설정
CPU 코어 수와 메모리 양은 Neo4j의 처리 능력과 캐시 성능을 직접적으로 결정합니다. 현재 설정은 2코어 CPU와 4GiB 메모리를 할당하고 있습니다.

```yaml
# CPU
cpu: 2

# Memory(Gi)
memory: 4
```

**최적화 가이드:**
- **저사양 워크로드:** 2코어, 2GiB 이상 (현재 설정보다 메모리 증가 권장)
- **중간 사양 워크로드:** 4-8코어, 8-16GiB
- **고사양 워크로드:** 16코어 이상, 32GiB 이상
- **메모리 증가 시 고려사항:** Neo4j는 메모리를 페이지 캐시와 JVM 힙에 할당합니다. 충분한 OS 페이지 캐시는 디스크 I/O를 줄이는 데 중요합니다.

### 스토리지 및 복제본 설정
스토리지 볼륨 크기는 저장할 데이터의 양에 따라 결정되어야 하며, 복제본 수는 가용성과 성능에 영향을 미칩니다.

```yaml
# Storage(Gi)
storage: 20

# Replicas
replicas: 1
```

**최적화 가이드:**
- **스토리지:** 초기 설정 20GiB이며, 최대 10,000GiB까지 확장 가능합니다. 예상 데이터 크기의 1.5배 이상을 할당하는 것이 좋습니다.
- **복제본:** 현재 단일 인스턴스(`replicas: 1`)로 설정되어 있습니다. 높은 가용성을 위해 `mode: replicaset`으로 변경하고 `replicas: 3` 이상으로 설정해야 합니다. 단일 인스턴스는 장애 시 데이터 접근이 불가능해질 수 있습니다.

**Section sources**
- [values.yaml](file://k8s-deploy/databases/neo4j/values.yaml#L1-L47)

## 초기화 시 연결 풀 및 트랜잭션 설정

`lightrag/kg/neo4j_impl.py` 파일은 Neo4j 드라이버 초기화 시 다양한 연결 및 트랜잭션 관련 설정을 환경 변수 또는 구성 파일을 통해 적용합니다. 이러한 설정은 동시성과 오류 복구 능력에 핵심적인 역할을 합니다.

### 주요 설정 파라미터
다음은 초기화 시 구성되는 주요 성능 관련 파라미터입니다.

| 설정 파라미터 | 환경 변수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| **최대 연결 풀 크기** | `NEO4J_MAX_CONNECTION_POOL_SIZE` | 100 | 드라이버가 유지할 수 있는 최대 연결 수. 동시 요청이 많을 경우 증가 필요 |
| **연결 타임아웃** | `NEO4J_CONNECTION_TIMEOUT` | 30.0초 | 새 연결을 설정하기 위해 기다리는 최대 시간 |
| **연결 획득 타임아웃** | `NEO4J_CONNECTION_ACQUISITION_TIMEOUT` | 30.0초 | 풀에서 사용 가능한 연결을 가져오기 위해 기다리는 시간 |
| **최대 트랜잭션 재시도 시간** | `NEO4J_MAX_TRANSACTION_RETRY_TIME` | 30.0초 | 트랜잭션 충돌 시 재시도를 시도하는 총 시간 |
| **최대 연결 수명** | `NEO4J_MAX_CONNECTION_LIFETIME` | 300.0초 | 연결이 폐기되기 전까지의 최대 수명 |
| **라이브니스 체크 타임아웃** | `NEO4J_LIVENESS_CHECK_TIMEOUT` | 30.0초 | 연결이 여전히 활성 상태인지 확인하는 데 사용되는 시간 |

### 설정 적용 코드
이러한 설정은 `Neo4JStorage` 클래스의 `initialize` 메서드에서 `AsyncGraphDatabase.driver` 생성자에 전달됩니다.

```python
self._driver: AsyncDriver = AsyncGraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD),
    max_connection_pool_size=MAX_CONNECTION_POOL_SIZE,
    connection_timeout=CONNECTION_TIMEOUT,
    connection_acquisition_timeout=CONNECTION_ACQUISITION_TIMEOUT,
    max_transaction_retry_time=MAX_TRANSACTION_RETRY_TIME,
    max_connection_lifetime=MAX_CONNECTION_LIFETIME,
    liveness_check_timeout=LIVENESS_CHECK_TIMEOUT,
    keep_alive=KEEP_ALIVE,
)
```

**최적화 가이드:**
- **고부하 환경:** `MAX_CONNECTION_POOL_SIZE`를 200-500으로 증가시켜 동시 연결을 처리할 수 있도록 합니다.
- **불안정한 네트워크:** `CONNECTION_TIMEOUT`과 `CONNECTION_ACQUISITION_TIMEOUT`을 60초 이상으로 늘려 일시적인 네트워크 지연에 대응합니다.
- **충돌이 많은 트랜잭션:** `MAX_TRANSACTION_RETRY_TIME`을 60초 이상으로 설정하여 재시도 기회를 늘립니다.

**Section sources**
- [neo4j_impl.py](file://lightrag/kg/neo4j_impl.py#L80-L140)

## 인덱스 생성 전략

효율적인 쿼리 성능을 위해서는 적절한 인덱스 생성이 필수적입니다. 이 시스템은 초기화 과정에서 자동으로 인덱스를 생성합니다.

### 자동 인덱스 생성
`Neo4JStorage.initialize()` 메서드는 데이터베이스 연결 후 워크스페이스 레이블에 대한 `entity_id` 필드에 인덱스를 생성합니다.

```python
# 워크스페이스 레이블에 entity_id 필드에 대한 인덱스 생성
result = await session.run(
    f"CREATE INDEX FOR (n:`{workspace_label}`) ON (n.entity_id)"
)
```

또한, `db.indexes()` 쿼리가 지원되지 않는 Neo4j 버전을 위한 대체 구문도 제공합니다.

```python
# 호환성을 위한 대체 구문
result = await session.run(
    f"CREATE INDEX IF NOT EXISTS FOR (n:`{workspace_label}`) ON (n.entity_id)"
)
```

### 인덱스 생성 전략
- **대상 필드:** `entity_id`는 노드를 고유하게 식별하는 주요 키이므로, 이 필드에 인덱스를 생성하는 것은 매우 중요합니다.
- **조건부 생성:** `CREATE INDEX IF NOT EXISTS`를 사용하여 중복 생성을 방지합니다.
- **레이블 기반:** 각 워크스페이스는 고유한 레이블을 가지므로, 인덱스는 해당 레이블 내에서만 적용됩니다.

**최적화 가이드:**
- **추가 인덱스 고려:** 자주 쿼리되는 다른 속성(예: `name`, `type`)에도 인덱스를 생성할 수 있습니다.
- **복합 인덱스:** 여러 필드를 조합하여 쿼리하는 경우, 복합 인덱스를 생성하는 것이 유리할 수 있습니다.
- **프로파일링 기반:** 실제 쿼리 패턴을 분석하여 가장 효과적인 인덱스를 결정해야 합니다.

**Section sources**
- [neo4j_impl.py](file://lightrag/kg/neo4j_impl.py#L208-L232)

## Cypher 쿼리 프로파일링 및 관계 탐색 최적화

효율적인 그래프 탐색을 위해서는 최적화된 Cypher 쿼리 패턴이 필요합니다. 이 시스템은 다양한 쿼리 패턴을 사용하여 노드와 관계를 검색합니다.

### 쿼리 프로파일링 및 최적화 패턴
- **노드 존재 확인:** `has_node` 메서드는 `MATCH` 절과 `RETURN count(n) > 0`을 사용하여 불필요한 데이터 로딩 없이 존재 여부만 확인합니다. 이는 불린 결과를 반환하므로 매우 효율적입니다.
- **관계 탐색 최적화:** `get_nodes_edges_batch` 메서드는 `UNWIND`를 사용하여 여러 노드에 대한 관계를 한 번의 쿼리로 검색합니다. 이는 개별 쿼리 실행보다 훨씬 효율적입니다.
- **노드 및 관계 일괄 가져오기:** `get_nodes_batch` 및 `get_edges_batch` 메서드는 `UNWIND`를 활용하여 대량의 데이터를 효율적으로 가져옵니다.

### 서브그래프 탐색 전략
`get_subgraph` 메서드는 그래프를 탐색하는 데 중요한 역할을 합니다. 이 메서드는 다음과 같은 전략을 사용합니다.
1.  **노드 수 사전 확인:** `max_nodes` 제한을 초과하는 경우, `is_truncated` 플래그를 설정하여 그래프가 잘렸음을 알립니다.
2.  **중요 노드 우선 탐색:** `ORDER BY degree DESC`를 사용하여 연결이 많은(중요한) 노드를 우선적으로 가져옵니다. 이는 시각화 시 핵심 정보를 보존하는 데 도움이 됩니다.
3.  **범위 제한:** `max_depth` 매개변수를 통해 탐색 깊이를 제한하여 무한 탐색을 방지합니다.

**최적화 가이드:**
- **`EXPLAIN` 및 `PROFILE`:** 복잡한 쿼리는 반드시 `EXPLAIN` 또는 `PROFILE` 명령어로 실행 계획을 분석해야 합니다. 이를 통해 인덱스 사용 여부, 노드 스캔 방식 등을 확인할 수 있습니다.
- **`OPTIONAL MATCH`의 신중한 사용:** `OPTIONAL MATCH`는 왼쪽 외부 조인을 수행하므로, 조건이 맞지 않는 경우에도 왼쪽 노드를 반환합니다. 의도치 않은 결과를 초래할 수 있으므로 주의가 필요합니다.
- **`WITH` 절 활용:** 중간 결과를 집계하거나 필터링한 후 다음 단계로 전달할 때 `WITH` 절을 사용하면 쿼리의 가독성과 성능을 모두 향상시킬 수 있습니다.

**Section sources**
- [neo4j_impl.py](file://lightrag/kg/neo4j_impl.py#L208-L232)

## 대규모 그래프 데이터 처리를 위한 캐시 및 메모리 구성

대규모 그래프 데이터를 처리하기 위해서는 효과적인 캐시 전략과 메모리 구성이 필수적입니다. 이 시스템은 Neo4j의 내부 메커니즘과 애플리케이션 레벨의 전략을 결합하여 성능을 극대화합니다.

### 캐시 설정
Neo4j는 자체적으로 강력한 캐시 계층 구조를 가지고 있습니다.
- **페이지 캐시:** 디스크에서 읽은 그래프 데이터를 캐시합니다. 이는 OS 페이지 캐시와 밀접하게 연관되어 있으며, `k8s-deploy/databases/neo4j/values.yaml`에서 할당된 전체 메모리의 상당 부분이 이 캐시에 사용되어야 합니다.
- **JVM 힙:** 트랜잭션 상태, 쿼리 실행 계획, 일부 캐시된 데이터를 저장합니다. 힙 크기는 너무 작으면 GC 압박을, 너무 크면 GC 시간이 길어지는 문제가 있습니다.

### 메모리 구성 최적화 가이드
1.  **리소스 할당:** `values.yaml`에서 `memory` 값을 충분히 크게 설정합니다. 예를 들어, 32GiB 이상의 메모리를 할당하면 페이지 캐시가 전체 그래프 데이터의 상당 부분을 담을 수 있습니다.
2.  **Neo4j 내부 설정:** 이 프로젝트의 설정 파일에는 명시되어 있지 않지만, Neo4j 서버의 `neo4j.conf` 파일에서 `dbms.memory.pagecache.size`와 `dbms.memory.heap.initial_size`/`dbms.memory.heap.max_size`를 직접 조정할 수 있습니다. 일반적으로 페이지 캐시에 전체 메모리의 50-75%를, 나머지를 JVM 힙에 할당하는 것이 일반적인 가이드라인입니다.
3.  **애플리케이션 레벨 캐시:** `Neo4JStorage` 클래스는 `get_node`, `get_nodes_batch` 등의 메서드를 통해 자주 접근하는 데이터를 캐시할 수 있는 구조를 제공합니다. 추가적인 외부 캐시(예: Redis)를 도입하여 애플리케이션 레벨에서 자주 사용되는 결과를 캐시하는 것도 효과적인 전략입니다.

**Section sources**
- [values.yaml](file://k8s-deploy/databases/neo4j/values.yaml#L1-L47)
- [neo4j_impl.py](file://lightrag/kg/neo4j_impl.py#L80-L140)

## 결론
Neo4j의 성능 최적화는 여러 계층에서 접근해야 합니다. 본 문서에서는 Kubernetes 환경에서의 리소스 할당(`values.yaml`), 애플리케이션 레벨의 연결 풀 및 트랜잭션 설정(`neo4j_impl.py`), 인덱스 전략, 쿼리 최적화 패턴, 그리고 메모리 구성에 대한 포괄적인 가이드를 제공했습니다. 핵심은 워크로드의 특성에 맞게 이러한 설정을 조정하고, `EXPLAIN`/`PROFILE`을 통해 쿼리 성능을 지속적으로 모니터링하는 것입니다. 특히, 충분한 메모리 할당과 `entity_id` 필드에 대한 인덱스 생성은 대부분의 사용 사례에서 기본적인 성능 향상을 보장합니다.