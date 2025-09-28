# 웹 UI 사용 빠른 시작

<cite>
**이 문서에서 참조한 파일**  
- [lightrag_server.py](file://lightrag/api/lightrag_server.py)
- [UploadDocumentsDialog.tsx](file://lightrag_webui/src/components/documents/UploadDocumentsDialog.tsx)
- [RetrievalTesting.tsx](file://lightrag_webui/src/features/RetrievalTesting.tsx)
- [GraphViewer.tsx](file://lightrag_webui/src/features/GraphViewer.tsx)
- [LanguageToggle.tsx](file://lightrag_webui/src/components/LanguageToggle.tsx)
- [ThemeToggle.tsx](file://lightrag_webui/src/components/ThemeToggle.tsx)
- [package.json](file://lightrag_webui/package.json)
</cite>

## 목차
1. [기본 명령어](#기본-명령어)  
2. [문서 업로드](#문서-업로드)  
3. [검색 테스트](#검색-테스트)  
4. [지식 그래프 시각화](#지식-그래프-시각화)  
5. [부가 기능](#부가-기능)  
6. [의존성 문제 해결](#의존성-문제-해결)

## 기본 명령어

LightRAG WebUI를 사용하기 위해 `lightrag_webui` 디렉터리에서 Bun을 사용한 기본 명령어를 실행해야 합니다. Bun은 빠른 JavaScript/TypeScript 런타임 및 패키지 관리자로, 개발 환경 설정에 적합합니다.

### 의존성 설치
```bash
bun install
```
또는, `bun.lockb` 파일의 상태를 고정하여 정확히 동일한 버전의 패키지를 설치하려면 다음 명령어를 사용합니다:
```bash
bun install --frozen-lockfile
```
`--frozen-lockfile` 옵션은 lock 파일에 기록된 버전 외의 업데이트를 허용하지 않으며, 팀 개발 시 의존성 버전의 일관성을 보장합니다.

### 개발 서버 실행
```bash
bun run dev
```
이 명령어는 개발 서버를 시작하고, 기본적으로 `http://localhost:5173`에서 WebUI를 제공합니다.

### 빌드
```bash
bun run build
```
이 명령어는 프로덕션용 정적 자산을 `dist` 디렉터리에 번들링합니다.

**중요 전제 조건**: WebUI를 사용하려면 백엔드 API 서버인 `lightrag_server.py`가 실행 중이어야 합니다. 다음 명령어로 서버를 시작하세요:
```bash
python lightrag/api/lightrag_server.py
```

**Section sources**
- [package.json](file://lightrag_webui/package.json#L5-L14)
- [lightrag_server.py](file://lightrag/api/lightrag_server.py#L1-L889)

## 문서 업로드

문서 업로드 기능은 사용자가 다양한 형식의 문서를 시스템에 추가할 수 있도록 해줍니다. 이 기능은 `UploadDocumentsDialog.tsx` 컴포넌트에서 구현되어 있으며, 다음과 같은 특징을 가집니다.

1. **업로드 트리거**: "Upload Documents" 버튼을 클릭하면 대화상자가 열립니다.
2. **파일 드롭존**: 사용자는 파일을 끌어다 놓거나, 클릭하여 파일 선택 창을 열 수 있습니다.
3. **지원 형식 및 제한**: 최대 200MB 크기의 파일을 업로드할 수 있으며, 지원 형식은 시스템 설정에 따라 다릅니다.
4. **업로드 프로세스**: 
   - 파일은 이름 순서로 정렬되어 순차적으로 업로드됩니다.
   - 각 파일의 업로드 진행률이 실시간으로 표시됩니다.
   - 중복된 파일 이름이 감지되면 경고 메시지가 표시됩니다.
   - 업로드가 성공하면 문서 목록이 자동으로 새로 고침됩니다.
5. **오류 처리**: 지원하지 않는 파일 형식이나 네트워크 오류 시, 구체적인 오류 메시지가 표시됩니다.

업로드된 문서는 LightRAG 시스템에서 자동으로 처리되어 지식 그래프와 벡터 저장소에 저장됩니다.

**Section sources**
- [UploadDocumentsDialog.tsx](file://lightrag_webui/src/components/documents/UploadDocumentsDialog.tsx#L1-L221)

## 검색 테스트

검색 테스트 기능은 사용자가 자연어 쿼리를 입력하여 RAG 시스템의 검색 및 생성 성능을 평가할 수 있도록 합니다. 이 기능은 `RetrievalTesting.tsx` 컴포넌트에서 구현되어 있으며, 다음과 같은 절차로 사용합니다.

1. **쿼리 입력**: 하단의 입력란에 질문을 입력합니다.
2. **쿼리 모드 지정**: 입력란에 `/모드명` 접두사를 붙여 검색 모드를 지정할 수 있습니다 (예: `/local 질문 내용`). 지원되는 모드는 `naive`, `local`, `global`, `hybrid`, `mix`, `bypass`입니다.
3. **전송**: "Send" 버튼을 클릭하거나 Enter 키를 눌러 쿼리를 전송합니다.
4. **응답 수신**: 
   - 시스템은 지식 그래프와 벡터 저장소에서 관련 정보를 검색합니다.
   - LLM이 검색된 정보를 바탕으로 응답을 생성합니다.
   - 스트리밍 모드가 활성화된 경우, 응답이 생성되는 즉시 실시간으로 표시됩니다.
5. **대화 기록**: 모든 질문과 응답은 대화 기록에 저장되며, 이후 쿼리에 컨텍스트로 활용됩니다.
6. **기록 삭제**: "Clear" 버튼을 클릭하면 대화 기록을 초기화할 수 있습니다.

이 기능을 통해 사용자는 시스템의 정확성, 관련성, 응답 속도를 직접 테스트할 수 있습니다.

**Section sources**
- [RetrievalTesting.tsx](file://lightrag_webui/src/features/RetrievalTesting.tsx#L1-L395)

## 지식 그래프 시각화

지식 그래프 시각화 기능은 추출된 엔티티와 관계를 시각적으로 탐색할 수 있도록 합니다. 이 기능은 `GraphViewer.tsx` 컴포넌트에서 구현되어 있으며, 다음과 같은 기능을 제공합니다.

1. **그래프 렌더링**: Sigma.js 라이브러리를 사용하여 노드(엔티티)와 엣지(관계)를 시각화합니다.
2. **노드 검색**: 상단의 검색 창을 통해 특정 엔티티를 찾을 수 있습니다.
3. **노드 선택 및 포커스**: 
   - 노드를 클릭하면 속성 패널에 해당 엔티티의 속성이 표시됩니다.
   - 선택된 노드는 자동으로 화면 중앙에 배치됩니다.
4. **레이아웃 제어**: 다양한 레이아웃 알고리즘(예: 원형, 힘 기반)을 선택하여 그래프의 구조를 변경할 수 있습니다.
5. **확대/축소 및 이동**: 마우스 휠로 확대/축소하고, 드래그로 그래프를 이동할 수 있습니다.
6. **전체 화면**: 전체 화면 모드로 전환하여 더 넓은 범위의 그래프를 탐색할 수 있습니다.
7. **범례 표시**: 노드와 엣지의 색상 및 모양이 의미하는 바를 설명하는 범례를 표시할 수 있습니다.
8. **속성 패널**: 선택된 노드의 모든 속성을 확인하고 편집할 수 있습니다.

이 시각화 도구는 지식 그래프의 구조와 품질을 분석하는 데 매우 유용합니다.

**Section sources**
- [GraphViewer.tsx](file://lightrag_webui/src/features/GraphViewer.tsx#L1-L239)

## 부가 기능

WebUI는 사용자 경험을 향상시키기 위한 다양한 부가 기능을 제공합니다.

### 언어 전환
`LanguageToggle.tsx` 컴포넌트는 UI의 표시 언어를 전환합니다. 현재는 영어(en)와 중국어(zh)를 지원하며, 버튼 클릭으로 즉시 전환됩니다. 예를 들어, 현재 언어가 중국어일 경우 "EN" 버튼을 클릭하면 영어로 전환됩니다.

### 테마 전환
`ThemeToggle.tsx` 컴포넌트는 어두운 모드와 밝은 모드 사이의 테마를 전환합니다. 다크 테마에서는 달 아이콘, 라이트 테마에서는 해 아이콘을 표시하며, 사용자의 선호에 따라 시각적 피로를 줄일 수 있습니다.

이러한 기능들은 사용자가 자신의 환경에 맞게 UI를 맞춤설정할 수 있도록 도와줍니다.

**Section sources**
- [LanguageToggle.tsx](file://lightrag_webui/src/components/LanguageToggle.tsx#L1-L50)
- [ThemeToggle.tsx](file://lightrag_webui/src/components/ThemeToggle.tsx#L1-L42)

## 의존성 문제 해결

Bun을 사용한 개발 환경 설정 시 흔히 발생하는 의존성 문제를 해결하는 방법은 다음과 같습니다.

1. **`bun install --frozen-lockfile` 사용**: 이 옵션은 `bun.lockb` 파일에 정확히 기록된 버전만 설치하므로, lock 파일이 변경되지 않도록 보장합니다. 협업 환경에서 모든 개발자가 동일한 의존성 버전을 사용해야 할 때 유용합니다.
2. **캐시 정리**: Bun의 글로벌 캐시가 손상된 경우, `bun pm cache clean` 명령어로 캐시를 정리할 수 있습니다.
3. **lock 파일 재생성**: `bun install` 명령어는 `bun.lockb` 파일이 없거나 손상된 경우 자동으로 재생성합니다. 의도적으로 재생성하려면 기존 파일을 삭제한 후 다시 설치합니다.
4. **모듈 충돌 해결**: `bun pm check` 명령어를 사용하여 의존성 트리의 일관성을 검사하고, 충돌을 해결할 수 있습니다.
5. **Node.js 호환성**: Bun은 대부분의 Node.js 패키지를 지원하지만, 일부 네이티브 모듈과 호환되지 않을 수 있습니다. 이 경우 `bun install --prefer-offline` 옵션을 시도하거나, `bun create` 명령어로 Bun 전용 프로젝트를 초기화하는 것이 좋습니다.

이러한 방법들을 통해 안정적인 개발 환경을 유지할 수 있습니다.

**Section sources**
- [package.json](file://lightrag_webui/package.json#L1-L101)
- [lightrag_server.py](file://lightrag/api/lightrag_server.py#L1-L889)