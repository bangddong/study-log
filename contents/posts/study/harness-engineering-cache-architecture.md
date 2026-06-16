---
title: '매 API 호출마다 30,000 토큰이 공짜다 — Claude Code의 Cache Architecture와 Latching 설계'
date: '2026-04-30'
tags:
  - AI
  - Claude Code
series: AI
emoji: "\U0001F4BE"
---

_이 글은_ [_Harness Engineering: From Claude Code Internals to AI Coding Best Practices_](https://github.com/nyang-police/harness-engineering-ko)_를 참고하여 작성되었습니다. 시리즈 주제: 경로 C — 성능 최적화 (LLM 애플리케이션 비용 및 지연 시간)_


---


Claude Code로 50턴짜리 세션을 진행한다고 가정해봅시다. 매 API 호출마다 system prompt(~11,000 토큰)와 40개 이상의 tool schema 정의(~20,000 토큰)가 전송됩니다. 이 "고정 오버헤드"만 호출당 30,000 토큰입니다. 50턴이면 **1,500,000 토큰이 반복 처리**됩니다.


Anthropic의 Prompt Caching은 정확히 이 문제를 해결합니다. API 요청의 prefix가 이전 요청과 일치하면 캐시된 KV 상태를 재사용해 **캐시된 부분의 비용을 90% 절감**할 수 있습니다. 하지만 cache hit에는 엄격한 조건이 있습니다. prefix가 **byte 단위로 정확히** 일치해야 하며, 단 한 글자라도 다르면 cache break가 발생합니다.


Claude Code는 이 제약 조건을 중심으로 정교한 cache architecture를 구축합니다. 이 글에서는 세 가지 cache scope, 두 가지 TTL tier, 그리고 cache break를 막는 latching 메커니즘을 해부합니다.


---


## Prefix Matching: 왜 한 글자도 달라지면 안 되는가


Anthropic의 prompt caching은 **prefix matching** 원리에 기반합니다. 서버는 API 요청을 직렬화된 byte stream으로 취급하여 처음부터 byte 단위로 비교합니다. 불일치가 발견되는 순간 그 지점에서 cache가 break됩니다.


```javascript
[System Prompt] → [Tool Definitions] → [Message History]
```


System prompt와 tool 정의가 앞부분에 위치하기 때문에, 이 부분에 변경이 생기면 **전체 cache가 무효화**됩니다. message history는 끝에 추가되므로, 새 메시지는 증분 부분에 대해서만 비용이 발생합니다.


caching을 활성화하려면 content block에 `cache_control` 마커를 추가합니다.


```typescript
// 기본 형태
{ type: 'ephemeral' }

// 확장 형태 (1P 전용)
{
  type: 'ephemeral',
  scope: 'global' | 'org',
  ttl: '5m' | '1h'
}
```


---


## 세 가지 Cache Scope: 공유 범위별 전략


Claude Code는 세 가지 cache scope를 사용하며, 각각 서로 다른 공유 범위에 대응합니다.


| Cache Scope | 공유 범위         | 적용 대상              | TTL      |
| ----------- | ------------- | ------------------ | -------- |
| **global**  | 조직 간, 사용자 간   | 완전히 불변적인 정적 prompt | 5분 (기본값) |
| **org**     | 동일 조직 내 사용자 간 | 조직별이지만 사용자 무관 콘텐츠  | 5분 / 1시간 |
| **null**    | cache 미적용     | 고빈도 변경 콘텐츠         | N/A      |


### Global Cache: 가장 공격적인 최적화


Global caching은 모든 Claude Code 사용자 간에 KV cache를 공유합니다. User A가 system prompt 정적 부분을 캐시하면, User B의 다음 요청이 해당 cache를 바로 hit할 수 있습니다.


적격 기준은 매우 엄격합니다. 콘텐츠는 **완전히 불변**이어야 합니다. Claude Code는 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 마커로 system prompt를 정적/동적 부분으로 분리합니다.


```typescript
// 경계 이전 → cacheScope: 'global'
// 경계 이후 → cacheScope: null
if (i < boundaryIndex) {
  staticBlocks.push(block)   // global 캐시 대상
} else {
  dynamicBlocks.push(block)  // 캐시 미적용
}
```


경계 이후 동적 콘텐츠는 `cacheScope: null`로 표시됩니다. org level caching도 사용하지 않습니다. 변경 빈도가 너무 높아 cache hit rate가 극히 낮을 것이고, cache breakpoint를 표시하는 것은 복잡성만 추가하기 때문입니다.


### Org Cache: Global의 합리적인 Fallback


Global caching을 사용할 수 없는 경우(global 기능 비활성화 or 조직별 정보 포함), org level로 fallback합니다.


한 가지 중요한 세부 사항이 있습니다. **billing attribution header**(`x-anthropic-billing-header`)는 `null`로 표시되어 캐시에서 제외됩니다. 이 header에는 사용자 식별 정보가 포함되어 org level에서도 공유할 수 없기 때문입니다.


### MCP Tool이 Global Cache를 무너뜨리는 이유


MCP tool을 구성하면 global caching 전략이 변경됩니다. MCP tool 정의는 외부 서버에서 제공되어 내용을 예측할 수 없기 때문에, global cache에 포함하면 hit rate가 떨어집니다. Claude Code는 `skipGlobalCacheForSystemPrompt` 플래그로 이를 감지하여 전체 콘텐츠를 org scope로 다운그레이드합니다.


잦은 global cache miss를 감수하기보다 더 안정적인 org level hit rate로 fallback하는 보수적인 선택입니다.


---


## TTL Tier: 5분 vs 1시간, 그리고 Latching


Anthropic의 prompt caching의 기본 TTL은 **5분**입니다. 활발한 코딩 세션에서는 충분하지만, 깊은 사고나 문서 검토가 필요한 시나리오에서는 부족할 수 있습니다.


Claude Code는 1시간 TTL을 지원하며, 다음 조건으로 결정됩니다.


| 조건                                                | TTL |
| ------------------------------------------------- | --- |
| 3P Bedrock + `ENABLE_PROMPT_CACHING_1H_BEDROCK=1` | 1시간 |
| Anthropic 직원 (`USER_TYPE=ant`)                    | 1시간 |
| Claude AI 구독자 + 할당량 미초과 + allowlist 통과            | 1시간 |
| 그 외                                               | 5분  |

> ⚠️ **[2026-03 기준 변경]** 위 표의 "Claude AI 구독자" 조건은 플랜별로 세분화되었습니다. **Max 구독자는 자동으로 1시간 TTL**, Pro 구독자 및 API 기본값은 5분입니다. ([출처](https://www.theregister.com/2026/04/13/claude_code_cache_confusion/))

### 왜 Latching이 필요한가


TTL 결정에서 가장 핵심적인 설계는 **latching**입니다. 다음 시나리오를 보세요.


```javascript
1. 세션 시작: 구독 할당량 이내 → 1시간 TTL 적용
2. 30번째 턴: 사용자가 할당량 초과 → isUsingOverage = true
3. TTL이 1시간 → 5분으로 변경
4. cache_control 객체의 직렬화가 변경
5. API 요청 prefix 불일치 → cache break!
```


단 한 번의 overage 상태 전환으로 ~20,000 토큰의 tool 정의 cache가 전부 무효화됩니다. latching 메커니즘은 **세션 시작 시 TTL tier를 결정하면 세션 전체에서 변경되지 않도록** 보장합니다.


```typescript
// 첫 호출 시 평가 후 STATE에 고정
let userEligible = getPromptCache1hEligible()
if (userEligible === null) {
  userEligible = isClaudeAISubscriber() && !currentLimits.isUsingOverage
  setPromptCache1hEligible(userEligible)  // 세션 내 고정
}
```


latching의 핵심 원칙: **약간 오래된 값을 사용하는 것이 세션 도중 cache key가 변경되는 것보다 낫다.**


---


## Beta Header Latching: 기능 토글이 Cache를 망치지 않도록


### 문제: 동적 Header가 Cache Key를 바꾼다


Anthropic의 API 요청에는 실험적 기능을 식별하는 "beta header" 세트가 포함됩니다. 이 header들은 서버 측 cache key의 일부입니다. header를 추가하거나 제거하면 cache key가 변경되어 cache break가 발생합니다.


Claude Code에는 세션 도중 동적으로 활성화/비활성화될 수 있는 기능들이 있습니다.

- **AFK Mode**: 자리를 비웠을 때 자동으로 작업 실행
- **Fast Mode**: 더 빠른 모델 사용
- **Cache Editing (Cached Microcompact)**: cache 내에서 증분 편집

이 기능들 중 하나가 상태를 변경할 때마다 대응하는 beta header가 추가/제거되어 ~50~70K 토큰의 cache가 무효화됩니다.


### 해결: Sticky-On Latching


```typescript
// 코드 주석 원문:
// Sticky-on latches for dynamic beta headers. Each header, once first
// sent, keeps being sent for the rest of the session so mid-session
// toggles don't change the server-side cache key and bust ~50-70K tokens.
// Latches are cleared on /clear and /compact via clearBetaHeaderLatches().
```


Claude Code의 해결책은 **sticky-on** latching입니다. 한 번이라도 beta header가 전송되면, 기능이 비활성화되더라도 세션이 끝날 때까지 계속 전송됩니다.


```typescript
// Fast Mode 예시
let fastModeHeaderLatched = getFastModeHeaderLatched() === true
if (!fastModeHeaderLatched && isFastMode) {
  fastModeHeaderLatched = true
  setFastModeHeaderLatched(true)  // 한 번 true가 되면 되돌아오지 않음
}
```


세 가지 beta header 모두 동일한 상태 전이를 따릅니다.


```javascript
Unlatched → (조건 최초 충족) → Latched → (기능 비활성화) → Latched 유지
                                    ↓
                          /clear 또는 /compact
                                    ↓
                               Unlatched (초기화)
```


| Beta Header   | 전제 조건                                  | 초기화 트리거              |
| ------------- | -------------------------------------- | -------------------- |
| AFK Mode      | agentic query + auto mode 활성           | `/clear`, `/compact` |
| Fast Mode     | fast mode 활성화 요청                       | `/clear`, `/compact` |
| Cache Editing | `CACHED_MICROCOMPACT` 활성 + main thread | `/clear`, `/compact` |


---


## Thinking Clear Latching: 1시간 후 캐시가 만료됐을 때


beta header latching 외에 특수한 latching이 하나 더 있습니다. 마지막 API 완료 이후 1시간 이상 경과했을 때 트리거되는 `thinkingClearLatched`입니다.


```typescript
if (!thinkingClearLatched && isAgenticQuery) {
  const lastCompletion = getLastApiCompletionTimestamp()
  if (lastCompletion !== null &&
      Date.now() - lastCompletion > CACHE_TTL_1HOUR_MS) {
    thinkingClearLatched = true
    setThinkingClearLatched(true)
  }
}
```


1시간 TTL을 사용하더라도 이 시점에서는 cache가 이미 만료된 상태입니다. Thinking Clear는 이 신호를 활용해 축적된 thinking 콘텐츠를 정리하여 이후 요청의 token 소비를 줄입니다.


---


## 설계 인사이트: Latching이 Cache 안정성의 핵심이다


Claude Code의 caching 코드 전반에서 동일한 패턴이 반복됩니다.

> **한 번 평가 → latch → 세션 안정성**

이 패턴은 TTL 적격성, TTL allowlist 설정, beta header 전송 상태, thinking clear 트리거 등 모든 곳에 등장합니다. 모든 latch의 목적은 하나입니다. 세션 중 상태 변경이 직렬화된 API 요청을 변경하는 것을 방지하여 cache prefix의 무결성을 보호하는 것입니다.


### Cache Scope는 비용 대 Hit Rate의 Trade-off다


세 가지 cache scope level은 명확한 trade-off를 구현합니다.

- **global**: 가장 높은 hit rate, 절대적 불변 콘텐츠만 가능
- **org**: 적당한 hit rate, 조직 수준 차이 허용
- **null**: cache marking 자체를 건너뜀, 비효과적인 캐싱 시도 방지

"가능하면 global, 아니면 org, 둘 다 안 되면 포기" — 획일적 접근보다 훨씬 세분화된 전략입니다.


---


## Claude Code 사용자를 위한 실용 가이드


**1. System prompt를 안정적으로 유지하라**


[CLAUDE.md](http://claude.md/)를 수정할 때마다 cache prefix가 무효화될 수 있습니다. 실험적 지시사항은 파일보다 세션 수준(`/memory` 또는 대화 내 지시)에 배치하는 것을 고려하세요.


**2. 모델 전환을 자주 하지 마라**


모델을 전환하면 cache prefix가 완전히 무효화됩니다. Opus와 Sonnet은 서로 다른 system prompt를 가지며, 전환 후 모든 caching이 처음부터 시작됩니다.


**3.** **`/compact`** **사용 시점을 잘 맞춰라**


수동 compaction 후 CC가 cache prefix를 재구축합니다. 많은 tool 호출(일괄 파일 수정 등)을 할 예정이라면, 먼저 compact하면 더 긴 유효 cache 기간을 확보할 수 있습니다.


**4. Cache hit 지표를 확인하라**


`--verbose` 모드에서 CC는 `cache_read_input_tokens`를 보고합니다. 이 수치가 0에 가깝고 `input_tokens`가 높다면 cache가 자주 무효화되고 있다는 신호입니다.


**5. MCP tool 연결 시 cache 저하를 감안하라**


MCP tool을 연결하면 global cache가 org level로 다운그레이드됩니다. 외부 tool 정의가 동적이어서 예측이 불가능하기 때문입니다.


---


## 직접 겪은 사례 (switch-job-quest 프로젝트)


### 사례 1: Evaluator 프롬프트 분리 — Prefix Matching 원리를 직접 구현


switch-job-quest에는 면접 답변을 평가하는 AI Evaluator가 12개 있습니다. 기존에는 system 지시사항과 user 입력을 하나의 프롬프트로 합쳐서 보냈습니다.


```kotlin
// 변경 전: system + user가 하나의 문자열로 뭉쳐짐
chatClient.prompt(systemPrompt + "\n\n" + userInput).call()
```


이 구조에서는 user 입력이 달라질 때마다 프롬프트 전체가 달라집니다. "처음부터 byte 단위로 비교"하는 prefix matching에서 cache hit가 불가능합니다.


Ch13의 구조를 그대로 적용했습니다. 각 Evaluator의 `.st` 파일을 `*-system.st`와 `*-user.st`로 분리하고, 호출 방식도 바꿨습니다.


```kotlin
// 변경 후: system(정적) + user(동적) 분리
chatClient
  .system(systemPrompt)  // 안정적 → 캐시 대상
  .user(userInput)       // 동적 → 매번 변경
  .call()
```


```kotlin
// AiClientConfig.kt — SYSTEM_ONLY cache strategy 적용
val cacheOptions = AnthropicCacheOptions.builder()
    .strategy(AnthropicCacheStrategy.SYSTEM_ONLY)
    .build()
val options = AnthropicChatOptions.builder()
    .model(Model.of(bossModel))
    .cacheOptions(cacheOptions)
    .build()
```


`SYSTEM_ONLY` strategy는 system prompt에만 `cache_control` 마커를 붙입니다. 12개 Evaluator의 system prompt는 평가 기준, 채점 루브릭 등 완전히 정적인 내용입니다. user prompt만 면접 답변에 따라 달라집니다.


결과: 동일 Evaluator를 여러 번 호출할 때 system prompt 부분은 cache hit됩니다. 대량 평가 배치에서 비용 절감 효과가 큽니다.


### 사례 2: Cache Strategy 프로퍼티 외부화 — Latching 원칙 적용


처음에는 `SYSTEM_ONLY`를 코드에 하드코딩했습니다. latching 설계의 핵심은 "실행 중 변경이 cache key를 바꾸면 안 된다"입니다. 코드에 strategy가 고정되면 런타임 중 변경은 막히지만, 환경별 제어가 불가능합니다.


```kotlin
// 변경 전: 하드코딩
.strategy(AnthropicCacheStrategy.SYSTEM_ONLY)

// 변경 후: 프로퍼티로 외부화
@Value("\${devquest.ai.boss-cache-strategy:SYSTEM_ONLY}")
bossCacheStrategy: String

.strategy(AnthropicCacheStrategy.valueOf(bossCacheStrategy))
```


```yaml
# client-ai-anthropic.yml
devquest:
  ai:
    boss-model: claude-sonnet-4-6
    boss-cache-strategy: SYSTEM_ONLY
```


Claude Code의 latching 메커니즘이 "세션 시작 시 결정을 고정"하는 것처럼, 애플리케이션 레벨에서는 "배포 단위로 strategy를 고정"합니다. 런타임 중 strategy가 바뀌면 이미 캐시된 요청과 prefix가 달라져 cache bust가 발생하기 때문입니다. 프로퍼티 외부화로 환경별 제어는 가능하되, 런타임 중 변경은 구조적으로 막혀 있습니다.


---


## 정리


| 메커니즘                      | 목적              | 핵심 설계                   |
| ------------------------- | --------------- | ----------------------- |
| Prefix Matching           | Cache hit 조건    | Byte 단위 일치 필요           |
| Global / Org / null Scope | Hit rate vs 유연성 | 콘텐츠 안정성에 따라 분리          |
| TTL Latching              | 세션 내 일관성        | 최초 평가 후 고정              |
| Beta Header Latching      | Cache key 보호    | Sticky-on, /clear로만 초기화 |
| Thinking Clear Latching   | 만료 후 최적화        | 1시간 경과 감지               |


Claude Code의 cache architecture는 단순히 "캐싱을 켠다"가 아닙니다. prefix의 안정성을 지키기 위한 다층적 방어 시스템입니다. 세션 중 어떤 상태 변경도 직렬화된 API 요청을 건드리지 못하도록 모든 가변 요소를 latching으로 고정합니다.


다음 글(Chapter 14)에서는 cache break가 실제로 발생했을 때 이를 감지하고 진단하는 2단계 detection architecture를 다룹니다.


---


_참고: Harness Engineering: From Claude Code Internals to AI Coding Best Practices, Chapter 13 — Cache Architecture와 Breakpoint 설계_

