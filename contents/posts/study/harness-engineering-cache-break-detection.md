---
title: Cache Break는 조용히 온다 — Claude Code의 2단계 감지 시스템 해부
date: '2026-05-07'
tags:
  - AI
  - Claude Code
series: AI
emoji: "\U0001F50D"
---

_이 글은_ [_Harness Engineering: From Claude Code Internals to AI Coding Best Practices_](https://github.com/nyang-police/harness-engineering-ko)_를 참고하여 작성되었습니다. 시리즈 주제: 경로 C — 성능 최적화 (LLM 애플리케이션 비용 및 지연 시간)_


---


cache break는 조용한 문제입니다. API 응답에서 `cache_read_input_tokens`가 0으로 떨어지지만 에러 메시지도 없고, 예외도 발생하지 않습니다. 비용이 늘어나고 있다는 사실을 뒤늦게 알아차릴 뿐입니다.


이전 글(Chapter 13)에서 cache break를 방지하는 latching 메커니즘을 다뤘습니다. 그렇다면 break가 실제로 발생했을 때는 어떻게 알 수 있을까요? Claude Code는 `services/api/promptCacheBreakDetection.ts`(728줄)에서 2단계 감지 시스템을 구현합니다.


---


## 2단계 아키텍처: 왜 Pre-request와 Post-response가 분리되어야 하는가


cache break 감지는 타이밍 제약이 결정한 구조입니다. cache hit 여부는 API 응답을 받기 전까지 알 수 없습니다. 반면 상태 비교는 요청 전에만 가능합니다. 이 두 제약이 2단계를 유일한 올바른 아키텍처로 만듭니다.


**Phase 1 — Pre-request:** **`recordPromptState()`**


요청 직전, 현재 상태를 스냅샷으로 캡처하고 이전 상태와 비교합니다. 변경사항이 있으면 `PendingChanges` 객체에 기록합니다.


```typescript
const pendingChanges = compareToPreviousState(currentState, previousState)
setPreviousState(currentState)
// 변경 감지: tool 추가/제거, system prompt 변경, beta header 변경 등
```


**Phase 2 — Post-response:** **`checkResponseForCacheBreak()`**


API 응답을 받은 후, 실제 cache token 수치를 확인합니다. Phase 1의 `PendingChanges`와 결합해 break 원인을 분석합니다.


```typescript
// 이중 임계값: 상대적 5% 이상 AND 절대적 2,000 토큰 이상 동시 만족 시에만 알림
const relativeDropThreshold = 0.05
const absoluteDropThreshold = 2000
```


이중 임계값의 목적은 노이즈 제거입니다. 자연스러운 token 수치 변동을 경보로 오인하지 않으면서도, 의미 있는 cache 손실은 놓치지 않습니다.


---


## PreviousState: 서버 캐시 키에 영향을 주는 모든 것을 추적한다


break 원인을 정확히 특정하려면 서버 캐시 키에 영향을 주는 모든 값을 추적해야 합니다. PreviousState는 15개 이상의 필드를 포함합니다.


| 필드               | 설명                            |
| ---------------- | ----------------------------- |
| systemHash       | System prompt 내용의 해시          |
| toolsHash        | 전체 tool schema 세트의 해시         |
| cacheControlHash | cache_control 마커 설정 해시        |
| model            | 사용 중인 모델명                     |
| fastMode         | Fast Mode 활성 여부               |
| betas            | 전송된 beta header 목록            |
| perToolHashes    | 개별 tool별 해시 (변경된 tool 특정에 사용) |
| callCount        | 세션 내 API 호출 횟수                |


### 핵심 설계: 이중 해시 전략


system prompt 해시와 cache control 해시를 분리합니다. cache scope 변경(global→org)이나 TTL 수정은 prompt 텍스트를 건드리지 않지만 `cacheControlHash`를 변경합니다. 이 두 해시를 분리하지 않으면 "prompt 내용은 같지만 cache control 설정이 바뀌었다"는 원인을 특정할 수 없습니다.


### Latched 값 기준


PreviousState는 실시간 설정이 아닌 latched 헤더 값을 기록합니다. 실제로 API에 전송된 값이 cache key를 결정하기 때문입니다. "설정에서는 Fast Mode가 꺼져 있지만 latch 때문에 헤더에는 포함됐다"는 상황을 정확히 추적하려면 전송 실제값이 기준이어야 합니다.


---


## Break Attribution: 90%는 서버 측이다


break 감지 후 원인 분석이 시작됩니다. 시스템은 세 가지 원인을 순서대로 확인합니다.


### 1. 클라이언트 측 변경


Phase 1의 PendingChanges를 그대로 활용합니다. tool 추가/제거, system prompt 변경, beta header 변경 등 클라이언트가 직접 일으킨 변경사항 목록입니다.


흥미로운 통계: tool schema 변경의 77%는 단일 tool 업데이트입니다. 전체 tool 세트 교체가 아니라 MCP tool 하나가 재연결되거나 정의가 바뀌는 경우가 대부분입니다. `perToolHashes`가 tool 단위 추적을 지원하는 이유입니다.


### 2. TTL 만료


마지막 assistant 응답 이후 경과 시간을 계산합니다. 5분 또는 1시간 TTL window를 초과했다면 만료가 break의 원인입니다. 이 경우는 예상된 정상 상태로 분류합니다.


### 3. 서버 측 원인 (추론)


클라이언트 변경도 없고 TTL도 초과하지 않았는데 break가 발생했다면? BigQuery `tengu_prompt_cache_break` 분석 결과, **약 90%의 break가 서버 측 원인**으로 밝혀졌습니다. 라우팅 변경, 부하 상태의 캐시 제거, billing/inference 불일치 등입니다.


이 발견은 Claude Code의 최적화 전략을 바꿨습니다. "모든 cache break를 제거하겠다"는 목표에서 "클라이언트 측 10%를 통제하는 것이 현실적인 최적화"로 초점이 이동했습니다.


---


## 진단 출력: 관측가능성이 목적이다


전체 시스템은 순수 관측가능성 목적으로 동작합니다. break를 막는 것이 아니라, break가 발생했을 때 원인을 파악할 수 있게 합니다.


**Analytics 이벤트**: BigQuery에 `tengu_prompt_cache_break` 레코드를 전송합니다. 변경 플래그, token 통계, 요청 메타데이터를 포함합니다. MCP tool 이름은 프라이버시 보호를 위해 `'mcp'`로 마스킹됩니다.


**Debug Diff**: 클라이언트 변경이 감지됐을 때 unified-format diff 파일을 생성합니다. 변경 전/후 상태를 나란히 보여줘서 "무엇이 달라졌는가"를 즉시 파악할 수 있습니다.


---


## 직접 겪은 사례 (switch-job-quest 프로젝트)


### 사례 1: BE AI Evaluator — Phase 2만 선택한 이유


PR #114/#115에서 12개 AI Evaluator에 Prompt Caching을 적용했지만, 실제로 캐시가 hit되고 있는지 알 방법이 없었습니다.


2단계 시스템을 검토했을 때, Phase 1(Pre-request 상태 스냅샷)은 적용하지 않았습니다. switch-job-quest의 AI Evaluator는 단발성 호출입니다. 사용자가 이력서를 제출하면 평가 한 번, 모의 면접을 제출하면 평가 한 번. "이전 상태"라는 개념 자체가 없으므로, PreviousState 15개 필드를 추적해도 비교할 이전 값이 없습니다.


Phase 2(Post-response 캐시 토큰 확인)만 적용했습니다. Spring AI CallAdvisor 패턴으로 `CacheMetricsAdvisor`를 구현해 ChatClient 빈에 등록했습니다. 각 Evaluator를 수정하지 않고도 모든 AI 호출 응답에서 `cache_read_input_tokens` / `cache_creation_input_tokens`를 추출해 INFO 로그로 기록합니다.


이중 임계값도 단순화했습니다. 상대적 5% 감지는 이전 호출의 `cache_read` 값이 있어야 하는데, 단발성 호출에서는 그 값이 없습니다. 절대값 2,000토큰만 적용했습니다.


```javascript
cache_creation > 2,000 AND cache_read == 0 → WARN
```


Break Attribution도 생략했습니다. 90%가 서버 측 원인이고, 단발성 호출에서 클라이언트 측 원인(prompt 변경, model 변경)은 코드 배포 시점에만 발생합니다. 로그만으로 충분히 파악할 수 있습니다.


단발성 AI 호출에서는 **Phase 2 + 절대값 임계값**의 조합이 현실적인 최소 구현입니다. 관측가능성 확보라는 목적은 달성하면서, 프로젝트 구조에 맞지 않는 Phase 1은 버렸습니다.


### 사례 2: [CONTEXT.md](http://context.md/) — 클라이언트 측 10%를 다른 레이어에서


두 번째 적용은 Claude Code 세션 자체입니다.


이 글의 핵심 결론이 "통제 가능한 클라이언트 측 10%에 집중하라"였는데, Claude Code를 사용하는 입장에서도 동일한 원칙이 적용됩니다. Claude Code는 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`로 system prompt를 정적/동적 부분으로 분리합니다. 이 경계 이전까지가 캐시 대상입니다.


프로젝트에서 Claude Code가 매 세션 읽는 파일이 `.claude/CONTEXT.md`입니다. 이 파일을 보니 브랜치명, PR 번호, 날짜가 6번째 줄 등장하고 있었습니다. 매 세션마다 이 내용이 바뀌니, 그 뒤에 오는 고정 내용(비자명적 결정, 참조 문서)도 덩달아 cache break를 겪고 있었습니다.


수정은 단순했습니다. 고정 내용을 상단으로, 동적 내용을 `---` 이하 하단으로 분리했습니다. 이제 파일 상단 약 40줄은 세션이 바뀌어도 그대로이고, cache break 영향 범위가 파일 하단으로 제한됩니다.


AI Evaluator와 Claude Code 세션은 레이어가 다르지만, 같은 원칙이 적용됐습니다. **안정적인 내용이 앞에 있어야 캐시가 유지된다.**


---


## 정리


| 구성 요소                                | 역할             | 핵심 설계                   |
| ------------------------------------ | -------------- | ----------------------- |
| Phase 1 (recordPromptState)          | 상태 스냅샷 + 변경 감지 | 요청 전 PendingChanges 생성  |
| Phase 2 (checkResponseForCacheBreak) | cache 토큰 하락 확인 | 이중 임계값 (5% AND 2,000토큰) |
| PreviousState                        | 서버 캐시 키 전체 추적  | 15개 이상 필드, latched 값 기준 |
| Break Attribution                    | 원인 분류          | 클라이언트/TTL/서버 측 순서 확인    |
| BigQuery Analytics                   | 데이터 수집         | 90%가 서버 측이라는 발견의 근거     |


cache break 감지 시스템의 핵심은 한 가지입니다. 통제 가능한 것(클라이언트 측 10%)에 집중하고, 통제 불가한 것(서버 측 90%)은 측정해서 인식합니다. 최적화는 관측가능성 위에서만 의미가 있습니다.


---


_참고: Harness Engineering: From Claude Code Internals to AI Coding Best Practices, Chapter 14 — Cache Break 감지 시스템_

