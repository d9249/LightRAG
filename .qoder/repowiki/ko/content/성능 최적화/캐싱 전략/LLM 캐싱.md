
# LLM 캐싱

<cite>
**이 문서에서 참조된 파일**
- [lightrag.py](file://lightrag/lightrag.py)
- [utils.py](file://lightrag/utils.py)
- [operate.py](file://lightrag/operate.py)
</cite>

## 목차
1. [소개](#소개)
2. [LLM 응답 캐싱 메커니즘](#llm-응답-캐싱-메커니즘)
3. [캐시 키 생성 로직](#캐시-키-생성-로직)
4. [SHA256 기반 해시 알고리즘의 영향](#sha256-기반-해시-알고리즘의-영향)
5. [엔티티 추출에서의 캐시 활용](#엔티티-추출에서의-캐시-활용)
6. [성능 향상 및 fallback 동작](#성능-향상-및-fallback-동작)
7. [결론](#결론)

## 소개
LightRAG는 반복적인 LLM 호출을 방지하고 성능을 향상시키기 위해 정교한 캐싱 메커니즘을 구현하고 있습니다. 이 문서는 `lightrag.py`의 `enable_llm_cache` 설정이 LLM 호출에 미치는 영향, `utils.py`의 `handle_cache` 및 `generate_cache_key` 함수가 캐시 키를 생성하는 방식, `compute_args_hash` 함수의 해시 알고리즘이 캐시 적중률에 미치는 영향, 그리고 `operate.py`의 `extract_entities` 함수가 캐시를 통해 반복적인 엔티티 추출을 방지하는 흐름을 심층적으로 분석합니다.

## LLM 응답 캐싱 메커니즘

LightRAG의 LLM 응답 캐싱 메커니즘은 `lightrag.py` 파일에서 정의된 `enable_llm_cache` 및 `enable_llm_cache_for_entity_extract` 설정에 의해 제어됩니다. 이 설정들은 LLM 호출 시 응답 재사용 여부를 결정합니다.

`enable_llm_cache` 설정은 일반적인 LLM 쿼리에 대한 캐싱을 활성화하거나 비활성화합니다. 이 설정이 `True`로 설정되면, LLM 응답은 캐시에 저장되어 이후 동일한 쿼리에 대해 빠르게 재사용될 수 있습니다. 반면, `enable_llm_cache_for_entity_extract` 설정은 엔티티 추출 단계에 대한 캐싱을 제어합니다. 이 설정이 `True`로 설정되면, 엔티티 추출 과정에서 생성된 LLM 응답도 캐시에 저장되어 반복적인 추출을 방지할 수 있습니다.

LLM 응답 캐싱은 `use_llm_func_with_cache` 함수를 통해 구현됩니다. 이 함수는 캐시를 확인하고, 캐시 적중(cache hit)이 발생하면 저장된 응답을 반환하며, 캐시 미스(cache miss)가 발생하면 새로운 LLM 호출을 수행하고 그 결과를 캐시에 저장합니다.

**Section sources**
- [lightrag.py](file://lightrag/lightrag.py#L207-L210)
- [utils.py](file://lightrag/utils.py#L1398-L1467)

## 캐시 키 생성 로직

LightRAG는 캐시 키를 생성하기 위해 `utils.py` 파일의 `generate_cache_key` 함수를 사용합니다. 이 함수는 캐시 키를 `{mode}:{cache_type}:{hash}` 형식으로 생성하여 충돌을 방지합니다.

`generate_cache_key` 함수는 세 가지 매개변수를 입력으로 받습니다: `mode`, `cache_type`, `hash_value`. `mode`는 캐시 모드를 나타내며, 예를 들어 'default', 'local', 'global' 등이 될 수 있습니다. `cache_type`은 캐시 유형을 나타내며, 예를 들어 'extract', 'query', 'keywords' 등이 될 수 있습니다. `hash_value`는 `compute_args_hash` 함수를 통해 생성된 해시 값입니다.

이 함수는 세 가지 매개변수를 결합하여 캐시 키를 생성합니다. 이 형식은 캐시 키의 고유성을 보장하고, 다양한 모드와 유형에 대한 캐시 항목을 명확하게 구분할 수 있도록 합니다.

**Section sources**
- [utils.py](file://lightrag/utils.py#L270-L309)

## SHA256 기반 해시 알고리즘의 영향

`compute_args_hash` 함수는 SHA256 기반 해시 알고리즘을 사용하여 입력 인수의 해시 값을 계산합니다. 이 함수는 모든 인수를 문자열로 변환하고 결합한 후, UTF-8로 인코딩하여 해시 값을 생성합니다.

이 해시 알고리즘은 캐시 적중률에 중요한 영향을 미칩니다. 해시 값은 입력 인수의 고유한 표현을 제공하므로, 동일한 인수를 가진 LLM 호출은 항상 동일한 해시 값을 생성합니다. 이는 캐시 적중률을 높이고, 반복적인 LLM 호출을 방지하는 데 기여합니다.

또한, 이 함수는 유니코드 인코딩 오류를 처리하기 위해 'replace' 오류 처리를 사용합니다. 이는 잘못된 문자를 유니코드 대체 문자(U+FFFD)로 대체하여 안전하게 인코딩할 수 있도록 합니다.

**Section sources**
- [utils.py](file://lightrag/utils.py#L270-L309)

## 엔티티 추출에서의 캐시 활용

`operate.py`의 `extract_entities` 함수는 캐시를 통해 반복적인 엔티티 추출을 방지하는 흐름을 구현합니다. 이 함수는 `use_llm_func_with_cache` 함수를 사용하여 LLM 호출을 수행하고, 그 결과를 캐시에 저장합니다.

`extract_entities` 함수는 먼저 `use_llm_func_with_cache` 함수를 호출하여 초기 추출을 수행합니다. 이 함수는 캐시를 확인하고