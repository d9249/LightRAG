
# KV 저장소

<cite>
**참조된 문서 내 파일**   
- [shared_storage.py](file://lightrag/kg/shared_storage.py)
- [json_kv_impl.py](file://lightrag/kg/json_kv_impl.py)
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py)
- [redis_impl.py](file://lightrag/kg/redis_impl.py)
- [mongo_impl.py](file://lightrag/kg/mongo_impl.py)
- [base.py](file://lightrag/base.py)
</cite>

## 목차
1. [소개](#소개)
2. [KV 저장소 아키텍처 개요](#kv-저장소-아키텍처-개요)
3. [공통 추상화 및 BaseKVStorage 인터페이스](#공통-추상화-및-basekvstorage-인터페이스)
4. [구현체 분석](#구현체-분석)
    1. [JSON 기반 저장소 (json_kv_impl.py)](#json-기반-저장소-json_kv_implpy)
    2. [PostgreSQL 저장소 (postgres_impl.py)](#postgresql-저장소-postgres_implpy)
    3. [Redis 저장소 (redis_impl.py)](#redis-저장소-redis_implpy)
    4. [MongoDB 저장소 (mongo_impl.py)](#mongodb-저장소-mongo_implpy)
5. [환경 구성 및 설정 방법](#환경-구성-및-설정-방법)
6. [데이터 일관성 및 장애 복구 전략](#데이터-일관성-및-장애-복구-전략)
7. [사용자 정의 KV 저장소 구현](#사용자-정의-kv-저장소-구현)
8. [결론](#결론)

## 소개

LightRAG는 다양한 데이터 저장소를 유연하게 지원하기 위해 키-값(Key-Value) 저장소 아키텍처를 설계하였습니다. 이 문서는 LightRAG에서 사용되는 KV 저장소의 목적과 아키텍처를 설명하며, JSON 기반, PostgreSQL, Redis, MongoDB 구현체의 특징과 사용 사례를 비교 분석합니다. 또한, 각 구현체의 초기화 로직, 설정 옵션, 데이터 직렬화 방식을 실제 코드를 기반으로 설명하고, Redis와 MongoDB의 성능 이점과 제약사항을 기술합니다. 마지막으로, `shared_storage.py`가 다양한 KV 저장소 간 공통 로직을 어떻게 추상화하고 있는지 설명하며, 사용자 정의 KV 저장소를 구현하기 위한 `BaseKVStorage` 인터페이스의 메서드 시그니처와 확장 방법을 제시합니다.

## KV 저장소 아키텍처 개요

LightRAG의 KV 저장소 아키텍처는 모듈화된 설계를 통해 다양한 백엔드 저장소를 유연하게 교체할 수 있도록 합니다. 핵심은 `BaseKVStorage`라는 추상 기본 클래스를 정의하고, 이를 상속받아 각각의 저장소 구현체(`JsonKVStorage`, `PostgreSQLDB`, `RedisKVStorage`, `MongoKVStorage`)를 개발하는 것입니다. 이 아키텍처는 다음과 같은 장점을 제공합니다:

*   **유연성**: 사용자는 애플리케이션의 요구 사항(성능, 지속성, 확장성 등)에 따라 가장 적합한 저장소를 선택할 수 있습니다.
*   **확장성**: 새로운 저장소를 추가하려면 `BaseKVStorage` 인터페이스를 구현하기만 하면 되므로, 시스템의 기존 코드를 변경하지 않고도 확장이 가능합니다.
*   **일관성**: 모든 저장소 구현체는 동일한 메서드 시그니처를 따르므로, 상위 레이어의 코드는 저장소의 종류에 관계없이 동일한 방식으로 데이터를 조작할 수 있습니다.

이러한 아키텍처는 `shared_storage.py` 파일에 정의된 공유 자원과 잠금 메커니즘을 통해 다중 프로세스 환경에서도 데이터의 일관성을 보장합니다.

**Section sources**
- [shared_storage.py](file://lightrag/kg/shared_storage.py#L0-L799)
- [base.py](file://lightrag/base.py#L303-L341)

## 공통 추상화 및 BaseKVStorage 인터페이스

`shared_storage.py`는 다양한 KV 저장소 간에 공통적으로 필요한 로직을 추상화하고, 다중 프로세스 환경에서의 데이터 일관성을 유지하기 위한 핵심 인프라를 제공합니다. 이 파일은 다음과 같은 주요 기능을 담당합니다:

1.  **공유 자원 관리**: `_shared_dicts`, `_init_flags`, `_update_flags`와 같은 전역 변수를 통해 여러 프로세스 간에 데이터를 공유하고 상태를 추적합니다.
2.  **동기화 메커니즘**: `UnifiedLock`과 `KeyedUnifiedLock` 클래스를 제공하여, 다중 프로세스 및 비동기 환경에서의 데드락을 방지하고 안전한 데이터 접근을 보장합니다. `KeyedUnifiedLock`은 특정 키에 대한 잠금을 관리하여, 전체 저장소를 잠그는 것보다 더 세밀한 제어가 가능하게 합니다.
3.  **초기화 및 상태 관리**: `get_data_init_lock()`, `get_storage_lock()` 등의 함수를 통해 저장소 초기화 및 데이터 업데이트 플래그를 관리합니다. 이는 `index_done_callback` 메서드를 통해 데이터가 디스크에 적절한 시점에 지속되도록 합니다.

이러한 공통 로직 위에 구축된 `BaseKVStorage` 인터페이스는 모든 KV 저장소 구현체가 반드시 따라야 하는 계약을 정의합니다. 이 인터페이스는 `lightrag/base.py` 파일에 정의되어 있으며, 다음과 같은 핵심 메서드를 포함합니다:

```mermaid
classDiagram
class BaseKVStorage {
<<abstract>>
+get_by_id(id : str) dict[str, Any] | None
+get_by_ids(ids : list[str]) list[dict[str, Any]]
+filter_keys(keys : set[str]) set[str]
+upsert(data : dict[str, dict[str, Any]]) None
+delete(ids : list[str]) None
}
```

**Diagram sources**
- [base.py](file://lightrag/base.py#L303-L341)

**Section sources**
- [shared_storage.py](file://lightrag/kg/shared_storage.py#L0-L799)
- [base.py](file://lightrag/base.py#L303-L341)

## 구현체 분석

### JSON 기반 저장소 (json_kv_impl.py)

`JsonKVStorage`는 파일 시스템에 JSON 파일을 사용하여 데이터를 저장하는 구현체입니다. 이는 설정이 간단하고, 외부 종속성이 없기 때문에 개발 및 테스트 환경에 적합합니다.

**초기화 로직 및 설정 옵션**:
*   초기화는 `__post_init__` 메서드에서 수행됩니다. `global_config["working_dir"]`을 기반으로 작업 디렉토리를 생성하고, `kv_store_{namespace}.json`이라는 이름의 JSON 파일 경로를 설정합니다.
*   `workspace` 매개변수를 사용하여 데이터를 논리적으로 격리할 수 있습니다. 이는 동일한 디렉토리 내에서 여러 작업 공간을 운영할 수 있게 합니다.
*   주요 설정은 `working_dir`이며, 이는 전역 설정 객체를 통해 전달됩니다.

**데이터 직렬화 방식**:
*   데이터는 메모리 내 `dict` 객체(`self._data`)로 유지됩니다.
*   `index_done_callback` 메서드가 호출될 때, 메모리의 데이터가 `lightrag.utils.write_json` 함수를 통해 JSON 파일로 직렬화되어 디스크에 저장됩니다.
*   반대로, 초기화 시에는 `load_json` 함수를 사용하여 디스크의 JSON 파일을 읽어 메모리로 로드합니다.
*   데이터는 `{"key": {"value": "data", "create_time": 123, "update_time": 456}}`와 같은 구조로 저장됩니다.

**성능 및 제약사항**:
*   **장점**: 설정이 매우 간단하고, 외부 서버가 필요 없어 개발이 용이합니다. JSON 파일은 사람이 직접 읽고 수정할 수 있어 디버깅이 쉽습니다.
*   **제약사항**: 모든 데이터가 메모리에 로드되므로, 대규모 데이터셋을 처리할 경우 메모리 사용량이 급격히 증가합니다. 또한, 파일 입출력은 디스크 I/O를 수반하므로, 고빈도의 읽기/쓰기 작업에서는 성능이 저하될 수 있습니다. 다중 프로세스 환경에서는 `shared_storage.py`의 잠금 메커니즘을 통해 보호되지만, 여전히 파일 기반의 한계로 인해 동시성 성능은 제한적입니다.

**Section sources**
- [json_kv_impl.py](file://lightrag/kg/json_kv_impl.py#L0-L284)
- [shared_storage.py](file://lightrag/kg/shared_storage.py#L0-L799)

### PostgreSQL 저장소 (postgres_impl.py)

`PostgreSQLDB`는 관계형 데이터베이스인 PostgreSQL을 백엔드로 사용하는 구현체입니다. 이는 ACID 특성을 보장하고, 복잡한 쿼리와 트랜잭션을 지원하므로, 데이터 무결성이 중요한 프로덕션 환경에 적합합니다.

**초기화 로직 및 설정 옵션**:
*   초기화는 `__init__` 메서드에서 구성 사전(`config`)을 통해 이루어집니다. 주요 설정 항목은 다음과 같습니다:
    *   `host`, `port`, `user`, `password`, `database`: 데이터베이스 연결 정보.
    *   `max_connections`: 연결 풀의 최대 크기.
    *   `ssl_mode`, `ssl_cert`, `ssl_key` 등: SSL 연결을 위한 옵션.
    *   `vector_index_type`, `hnsw_m`, `ivfflat_lists` 등: 벡터 검색을 위한 인덱스 설정.
*   `initdb` 메서드는 `asyncpg` 라이브러리를 사용하여 비동기적으로 데이터베이스 연결 풀을 생성하고, 필요한 확장(`vector`, `age`)을 설정합니다.

**데이터 직렬화 방식**:
*   데이터는 PostgreSQL의 테이블에 저장됩니다. 예를 들어, LLM 캐시는 `LIGHTRAG_LLM_CACHE` 테이블에 저장됩니다.
*   복잡한 데이터 구조는 `JSONB` 데이터 타입을 사용하여 저장됩니다. 이는 JSON 데이터를 이진 형식으로 저장하여, 저장 공간을 절약하고 쿼리 성능을 향상시킵니다.
*   `upsert` 작업은 `INSERT ... ON CONFLICT ... DO UPDATE` 문을 사용하여 수행됩니다.

**성능 및 제약사항**:
*   **장점**: 강력한 데이터 무결성과 트랜잭션 지원, 복잡한 쿼리 및 조인 가능, 높은 확장성. `JSONB`를 사용하면 반정형 데이터를 효율적으로 저장하고 쿼리할 수 있습니다.
*   **제약사항**: 관계형 데이터베이스 서버를 별도로 운영해야 하므로, 인프라 관리가 복잡해질 수 있습니다. 스키마 마이그레이션을 위한 `_migrate_*` 메서드들이 존재하지만, 스키마 변경이 필요한 경우 수동 개입이 필요할 수 있습니다. 설정이 가장 복잡한 편입니다.

**Section sources**
- [postgres_impl.py](file://lightrag/kg/postgres_impl.py#L0-L799)

### Redis 저장소 (redis_impl.py)

`RedisKVStorage`는 메모리 기반의 고성능 키-값 저장소인 Redis를 사용하는 구현체입니다. 이는 초저지연 읽기/쓰기 성능을 제공하므로, 캐싱과 같이 빈번한 데이터 접근이 필요한 시나리오에 최적화되어 있습니다.

**초기화 로직 및 설정 옵션**:
*   초기화는 `__post_init__` 메서드에서 수행됩니다. 설정은 다음과 같은 순서로 우선순위가 적용됩니다:
    1.  `REDIS_WORKSPACE` 환경 변수 (가장 높은 우선순위).
    2.  `workspace` 매개변수.
    3.  `REDIS_URI` 환경 변수 또는 `config.ini` 파일의 `redis.uri` 설정 (기본값: `redis://localhost:6379`).
*   `RedisConnectionManager` 클래스를 사용하여 공유 연결 풀을 관리합니다. 이는 연결 오버헤드를 줄이고, 리소스를 효율적으로 사용합니다.
*   `MAX_CONNECTIONS`, `SOCKET_TIMEOUT`, `RETRY_ATTEMPTS` 등의 상수를 통해 연결 풀과 재시도 정책을 구성할 수 있습니다.

**데이터 직렬화 방식**:
*   데이터는 Redis의 문자열 키-값 쌍으로 저장됩니다. 키는 `{final_namespace}:{id}` 형식을 따릅니다.
*   값은 `json.dumps`를 사용하여 JSON 문자열로 직렬화되어 저장되며, `json.loads`를 사용하여 역직렬화됩니다.
*   `upsert` 작업은 파이프라인을 사용하여 배치로 수행되어, 네트워크 왕복 횟수를 줄입니다.

**성능 및 제약사항**:
*   **장점**: 메모리 기반으로 인한 초고속 읽기/쓰기 성능, 높은 동시성 처리 능력, 연결 풀을 통한 효율적인 리소스 관리, `tenacity` 라이브러리를 활용한 자동 재시도 기능으로 네트워크 오류에 강한 내구성.
*   **제약사항**: 데이터가 메모리에 저장되므로, 데이터 크기가 메모리 용량을 초과할 수 있습니다. 전원 장애 시 데이터를 잃을 수 있으므로, 영구 저장이 필요한 경우 RDB 또는 AOF 지속성 옵션을 활성화해야 합니다. Redis 서버를 별도로 운영해야 합니다.

**Section sources**
- [redis_impl.py](file://lightrag/kg/redis_impl.py#L0-L799)
- [shared_storage.py](file://lightrag/kg/shared_storage.py#L0-L799)

### MongoDB 저장소 (mongo_impl.py)

`MongoKVStorage`는 문서 지향 데이터베이스인 MongoDB를 사용하는 구현체입니다. 이는 스키마가 유연하고, JSON과 유사한 BSON 형식으로 데이터를 저장하므로, 반정형 데이터를 다루는 데 매우 적합합니다.

**초기화 로직 및 설정 옵션**:
*   초기화는 `__post_init__` 메서드에서 수행됩니다. 설정은 다음과 같은 순서로 우선순위가 적용됩니다:
    1.  `MONGODB_WORKSPACE` 환경 변수 (가장 높은 우선순위).
    2.  `workspace` 매개변수.
    3.  `MONGO_URI` 환경 변수 또는 `config.ini` 파일의 `mongodb.uri` 설정 (기본값: `mongodb://root:root@localhost:27017/`).
*   `ClientManager` 클래스를 사용하여 공유 `AsyncMongoClient` 인스턴스를 관리합니다. 이는 클라이언트 생성 오버헤드를 줄입니다.
*   `initialize` 메서드는 `get_or_create_collection` 함수를 통해 컬렉션을 생성하고, 필요한 인덱스를 생성합니다.

**데이터 직렬화 방식**:
*   데이터는 MongoDB의 컬렉션에 BSON 문서로 저장됩니다. 각 문서는 `_id` 필드를 기본 키로 사용합니다.
*   Python의 `dict` 객체가 그대로 BSON으로 직렬화되어 저장되며, 조회 시에도 `dict` 형태로 반환됩니다. 이는 개발자에게 매우 직관적입니다.
*   `upsert` 작업은 `bulk_write`와 `UpdateOne` 연산을 사용하여 효율적으로 수행됩니다.

**성능 및 제약사항**:
*   **장점**: 유연한 스키마로 인해 데이터 구조 변경이 용이함, JSON/BSON 기반으로 직관적인 데이터 모델링, 수평 확장이 용이함, `get_or_create_collection`을 통해 컬렉션 자동 생성.
*   **제약사항**: 관계형 데이터베이스에 비해 데이터 무결성 제약이 약할 수 있음. 쿼리 성능은 인덱스 설계에 크게 의존함. MongoDB 서버를 별도로 운영해야 함.

**Section sources**
- [mongo_impl.py](file://lightrag/kg/mongo_impl.py#L0-L799)
- [shared_storage.py](file://lightrag/kg/shared_storage.py#L0-L799)

## 환경 구성 및 설정 방법

각 KV 저장소를 사용하기 위해 필요한 환경 구성과 설정 방법은 다음과 같습니다. 설정은 일반적으로 환경 변수 또는 구성 파일(`config.ini`)을 통해 이루어집니다.

**JSON 기반 저장소 설정**:
1.  `global_config`에 `working_dir`을 지정합니다.
2.  `JsonKVStorage` 인스턴스를 생성할 때, `namespace`와 `global_config`를 전달합니다.
```python
storage = JsonKVStorage(
    namespace="my_data",
    global_config={"working_dir": "/path/to/working_dir"}
)
```

**PostgreSQL 저장소 설정**:
1.  PostgreSQL 서버를 설치하고 실행합니다.
2.  데이터베이스와 사용자를 생성합니다.
3.  환경 변수를 설정하거나 `config.ini` 파일을 생성합니다.
```ini
[postgresql]
uri = postgresql://user:password@localhost:5432/mydb
database = mydb
max_connections = 50
```
4.  `PostgreSQLDB` 인스턴스를 생성하고 `initdb`를 호출합니다.
```python
config = {
    "host": "localhost",
    "port": 5432,
    "user": "user",
    "password": "password",
    "database": "mydb",
    "max_connections": 50
}
db = PostgreSQLDB(config)
await db.initdb()
```

**Redis 저장소 설정**:
1.  Redis 서버를 설치하고 실행합니다.
2.  `REDIS_URI` 환경 변수를 설정합니다.
