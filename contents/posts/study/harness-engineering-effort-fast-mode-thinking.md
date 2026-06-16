---
title: /effort max는 다음 세션에 사라진다 — Claude Code의 Effort·Fast Mode·Thinking 해부
date: '2026-05-15'
tags:
  - AI
  - Claude Code
series: AI
emoji: "\U0001F3AF"
---

_이 글은_ [_Harness Engineering: From Claude Code Internals to AI Coding Best Practices_](https://github.com/nyang-police/harness-engineering-ko)_를 참고하여 작성되었습니다. 시리즈 주제: 경로 C — 성능 최적화 (LLM 애플리케이션 비용 및 지연 시간)_


---


Claude Code의 추론 깊이는 단순하지 않습니다. `/effort max`를 설정했는데 다음 세션에는 사라져 있습니다. `ultrathink`를 입력했는데 UI에 무지개가 뜹니다. Fast Mode가 갑자기 cooldown에 들어갔다가 저절로 복구됩니다. 이것들은 버그가 아닙니다. 세 가지 독립적인 메커니즘 — **Effort**, **Fast Mode**, **Thinking** — 이 협력하는 방식입니다.


이 글에서는 세 가지 메커니즘을 각각 해부하고, 런타임에서 어떻게 협력해 각 API 호출의 추론 동작을 결정하는지 분석합니다.


---


## Effort: 추론 노력 수준


Effort는 모델이 응답을 생성하기 전에 얼마나 많은 "사고 시간"을 투자하는지를 제어하는 Claude API의 네이티브 파라미터입니다. 네 가지 수준이 있습니다.


| 수준       | 설명                        | 제한          |
| -------- | ------------------------- | ----------- |
| `low`    | 빠르고 직접적인 구현, 최소한의 오버헤드    | -           |
| `medium` | 균형 잡힌 접근, 표준 구현 및 테스트     | -           |
| `high`   | 광범위한 테스트와 문서화를 포함한 포괄적 구현 | -           |
| `max`    | 가장 깊은 추론 능력               | Opus 4.6 전용 |


`max`는 `modelSupportsMaxEffort()`에 하드코딩되어 있습니다 — `opus-4-6` 및 내부 모델만 지원됩니다. 다른 모델이 `max`를 사용하려 하면 `high`로 조용히 다운그레이드됩니다.


### 우선순위 Chain


Effort의 실제 값은 3단계 우선순위 chain으로 결정됩니다.


```typescript
// utils/effort.ts
export function resolveAppliedEffort(
  model: string,
  appStateEffortValue: EffortValue | undefined,
): EffortValue | undefined {
  const envOverride = getEffortEnvOverride()
  if (envOverride === null) {
    return undefined  // 'unset'/'auto': effort 파라미터 자체를 전송하지 않음
  }
  const resolved =
    envOverride ?? appStateEffortValue ?? getDefaultEffortForModel(model)
  if (resolved === 'max' && !modelSupportsMaxEffort(model)) {
    return 'high'
  }
  return resolved
}
```


높은 우선순위에서 낮은 순서로:

1. **환경변수** `CLAUDE_CODE_EFFORT_LEVEL` — 가장 강한 오버라이드. `unset` 또는 `auto`로 설정하면 API 기본값을 사용합니다
2. **AppState** — `/effort` 명령 또는 UI 토글로 설정한 값
3. **모델별 기본값** — `getDefaultEffortForModel()`이 결정

### 기본값이 `high`가 아닌 이유


직관적으로 Opus 4.6의 기본 Effort는 `high`일 것 같습니다. 실제로는 `medium`입니다.


```typescript
// utils/effort.ts
if (model.toLowerCase().includes('opus-4-6')) {
  if (isProSubscriber()) {
    return 'medium'
  }
  // Max/Team 구독자도 동일
}
```


A/B 테스트를 통해 결정된 사항입니다(GrowthBook `tengu_grey_step2`로 제어). 소스 코드 주석에는 명시적 경고가 있습니다.

> IMPORTANT: Do not change the default effort level without notifying the model launch DRI and research. Default effort is a sensitive setting that can greatly affect model quality.

대부분의 프로그래밍 인터랙션은 가장 깊은 추론이 필요하지 않습니다. 기본값을 `medium`으로 낮추면 throughput이 크게 향상되고 latency가 줄어듭니다. Ultrathink 메커니즘은 여기서 필요할 때만 `high`로 올라가는 경로를 제공합니다.


### `/effort max`는 왜 다음 세션에 사라지는가


`toPersistableEffort()` 함수가 답을 줍니다 — 외부 사용자에게 `max`는 저장되지 않습니다. 숫자형 effort(내부 전용)도 저장되지 않습니다. 오직 현재 세션에서만 유효합니다.


의도적인 설계입니다. `max`를 설정한 채 잊어버리면 장기적으로 과도한 리소스를 소비하게 됩니다. 각 세션은 모델 기본값으로 깨끗하게 시작합니다.


---


## Fast Mode: Opus 4.6 가속


Fast Mode(내부 코드명 "Penguin Mode")는 Sonnet 계열 모델이 특정 요청을 Opus 4.6으로 라우팅하는 모드입니다. 사용자의 기본 모델이 Opus가 아닐 때, 더 높은 품질이 필요한 요청을 가속기로 처리합니다.


### Cooldown 상태 머신


Fast Mode의 런타임 상태는 세 가지입니다.


```typescript
// utils/fastMode.ts
export type FastModeRuntimeState =
  | { status: 'active' }
  | { status: 'cooldown'; resetAt: number; reason: CooldownReason }
  // + 조직 수준 비활성화 (permanent)
```


Cooldown은 두 가지 이유로 트리거됩니다.

- `rate_limit` — API 429
- `overloaded` — 서비스 과부하

```typescript
// utils/fastMode.ts
export function triggerFastModeCooldown(
  resetTimestamp: number,
  reason: CooldownReason,
): void {
  runtimeState = { status: 'cooldown', resetAt: resetTimestamp, reason }
  logEvent('tengu_fast_mode_fallback_triggered', { ... })
  cooldownTriggered.emit(resetTimestamp, reason)
}
```


Cooldown 만료 감지는 **지연(lazy) 방식**입니다 — 타이머를 사용하지 않습니다. 대신 `getFastModeRuntimeState()`를 호출할 때마다 `Date.now() >= resetAt`을 확인합니다. 타이머 리소스 오버헤드와 경쟁 조건을 피하는 대신, 만료 감지가 쿼리 빈도에 의존합니다. UI 구동 시스템에서 이 비용은 사실상 제로입니다.


`getFastModeState()`는 모든 상태를 사용자에게 보이는 세 가지로 압축합니다.


```typescript
'off' | 'cooldown' | 'on'
```


`on`은 가속 아이콘, `cooldown`은 임시 성능 저하 안내, `off`는 아무것도 표시하지 않습니다.


### 가용성 확인 순서


Fast Mode가 켜지는 데는 여러 조건을 통과해야 합니다.

1. **Statsig 원격 킬 스위치** (`tengu_penguins_off`) — 최고 우선순위
2. **SDK mode** — Agent SDK에서는 명시적 opt-in 없이 기본 비활성화
3. **Non-first-party provider** — Bedrock/Vertex/Foundry 미지원
4. **조직 수준 상태** — API prefetch로 캐싱, 30초 스로틀

조직 상태 prefetch는 네트워크 실패 시 다르게 폴백합니다 — 내부 사용자는 기본 허용, 외부 사용자는 디스크에 캐시된 값을 사용합니다.


---


## Thinking: Chain-of-Thought 설정


Thinking은 모델이 추론 과정을 출력할지 여부와 방법을 제어합니다. 세 가지 모드가 있습니다.


```typescript
// utils/thinking.ts
export type ThinkingConfig =
  | { type: 'adaptive' }
  | { type: 'enabled'; budgetTokens: number }
  | { type: 'disabled' }
```


| 모드         | 동작                                | 적용 모델                |
| ---------- | --------------------------------- | -------------------- |
| `adaptive` | 모델이 사고 여부와 깊이를 스스로 결정             | Opus 4.6, Sonnet 4.6 |
| `enabled`  | 고정된 token budget chain-of-thought | 구형 Claude 4 모델       |
| `disabled` | chain-of-thought 없음               | API 검증, 저오버헤드 호출     |


### 3단계 기능 감지


세 가지 독립적인 함수가 순서대로 결정합니다.


**`modelSupportsThinking()`** — chain-of-thought 자체를 지원하는가?


```typescript
// first-party 및 Foundry: Claude 3을 제외한 모든 모델
return !canonical.includes('claude-3-')
// Bedrock/Vertex: Sonnet 4+, Opus 4+만
return canonical.includes('sonnet-4') || canonical.includes('opus-4')
```


**`modelSupportsAdaptiveThinking()`** — adaptive 모드를 지원하는가?


```typescript
// 4.6 버전만 명시적 지원
if (canonical.includes('opus-4-6') || canonical.includes('sonnet-4-6')) {
  return true
}
```


always-true 기본값에 주석이 붙어 있습니다.

> Newer models (4.6+) are all trained on adaptive thinking and MUST have it enabled for model testing. DO NOT default to false for first party, otherwise we may silently degrade model quality.

**`shouldEnableThinkingByDefault()`** — Thinking이 기본 활성화되어야 하는가?


```typescript
// 환경변수 > settings.alwaysThinkingEnabled > 기본 활성화
if (process.env.MAX_THINKING_TOKENS) {
  return parseInt(process.env.MAX_THINKING_TOKENS, 10) > 0
}
```


---


## Ultrathink: 키워드 하나로 추론을 올린다


Ultrathink는 메시지에 `ultrathink` 키워드가 있으면 Effort를 `medium`에서 `high`로 상향하는 메커니즘입니다.


### 작동 방식


감지는 단어 경계 매칭(`\b`)으로 대소문자 무관하게 동작합니다.


```typescript
export function hasUltrathinkKeyword(text: string): boolean {
  return /\bultrathink\b/i.test(text)
}
```


흥미로운 구현 세부사항이 있습니다 — 매 호출마다 새로운 regex 리터럴을 생성합니다. 공유 인스턴스를 재사용하면 `String.prototype.matchAll`이 `lastIndex` 상태를 복사해 호출 간에 누출될 수 있기 때문입니다.


감지되면 attachment 시스템을 통해 메시지를 주입합니다.


```typescript
// utils/attachments.ts
return [{ type: 'ultrathink_effort', level: 'high' }]
```


이 attachment는 system reminder 메시지로 변환됩니다.


```typescript
// utils/messages.ts
case 'ultrathink_effort': {
  return wrapMessagesInSystemReminder([
    createUserMessage({
      content: `The user has requested reasoning effort level: ${attachment.level}. Apply this to the current turn.`,
      isMeta: true,
    }),
  ])
}
```


Ultrathink는 `resolveAppliedEffort()`의 출력을 직접 수정하지 않습니다. API 파라미터를 건드리지 않고, 메시지 시스템을 통해 모델에게 "더 높은 추론 노력을 적용하라"고 알립니다. 모델이 adaptive thinking 모드에서 스스로 조정합니다.


### 레인보우 UI


Ultrathink가 인식되면 키워드가 무지개 색으로 표시됩니다.


```typescript
const RAINBOW_COLORS: Array<keyof Theme> = [
  'rainbow_red', 'rainbow_orange', 'rainbow_yellow',
  'rainbow_green', 'rainbow_blue', 'rainbow_indigo', 'rainbow_violet',
]
```


`getRainbowColor()`는 문자 인덱스에 따라 색상을 순환 할당하며, shimmer 변형으로 반짝이는 효과를 줍니다.


### Opus 4.6의 기본값 `medium`과의 시너지


설계가 맞물립니다.

1. 기본 effort는 `medium` — 대부분의 요청에 빠른 응답
2. 깊은 추론이 필요할 때 메시지에 `ultrathink`를 추가
3. attachment가 effort 상향 메시지를 주입
4. adaptive thinking 모드에서 모델이 추론 깊이를 높임

설정 메뉴를 열 필요가 없습니다. 문장에 단어 하나만 추가하면 됩니다.


---


## 세 가지 메커니즘의 협력


Effort, Fast Mode, Thinking은 API 호출 경로에서 순서대로 작동합니다.


```javascript
User Input
  │
  ├─ "ultrathink" 포함? → ultrathink_effort attachment 주입
  │
  ▼
resolveAppliedEffort()
  ├─ 환경변수 CLAUDE_CODE_EFFORT_LEVEL
  ├─ AppState.effortValue (/effort 명령)
  └─ 모델 기본값 (Opus 4.6 Pro → 'medium')
  │
  ▼
Fast Mode 확인
  ├─ 'on'  → Opus 4.6으로 라우팅
  ├─ 'cooldown' → 원래 모델 사용
  └─ 'off' → 원래 모델 사용
  │
  ▼
Thinking 설정
  ├─ adaptive 지원? → { type: 'adaptive' }
  ├─ thinking 지원? → { type: 'enabled', budget_tokens: N }
  └─ 미지원 → { type: 'disabled' }
  │
  ▼
API call: messages.create({ model, effort, thinking, ... })
```


주요 상호작용 세 가지입니다.

- **Effort + Thinking**: Effort가 `medium`이고 Thinking이 `adaptive`일 때, 모델은 추론을 적게 선택할 수 있습니다. Ultrathink가 `high`로 상향하면 adaptive thinking이 추론 깊이를 함께 높입니다
- **Fast Mode + Effort**: Fast Mode는 모델을 바꾸고(Opus 4.6으로 라우팅), Effort는 동일 모델의 추론 깊이를 바꿉니다. 두 가지는 직교(orthogonal)합니다
- **Fast Mode + Thinking**: Fast Mode가 요청을 Opus 4.6으로 라우팅하면, 해당 모델은 adaptive thinking을 지원하므로 Thinking 설정이 자동으로 업그레이드됩니다

---


## 직접 겪은 사례


### 사례: switch-job-quest — `/effort max`를 프롬프트 설계로 대체하다


멀티 에이전트 하네스를 운영하다 보면 자연스럽게 드는 생각이 있습니다. 복잡한 백엔드 구현을 담당하는 `be-feature-builder`, 코드 전체를 검토하는 `qa-reviewer` — 이 둘은 가능한 한 깊게 추론해야 합니다. 그래서 `/effort max`를 설정했는데, 다음 세션을 시작하면 다시 `medium`으로 돌아와 있었습니다.


앞서 살펴본 `toPersistableEffort()`의 동작 그대로였습니다. `max`는 저장되지 않고 세션이 끝나면 모델 기본값으로 초기화됩니다. 매 세션마다 수동으로 설정할 수도 있지만, 오케스트레이터가 `Agent()`를 호출해 sub-agent를 스폰하는 구조에서는 사람이 개입할 타이밍이 없습니다.


해결책은 sub-agent를 스폰할 때 전달하는 프롬프트 첫 줄에 `ultrathink`를 추가하는 것이었습니다. `ultrathink`는 user message에 포함되는 순간 `hasUltrathinkKeyword()`가 감지하고 `ultrathink_effort` attachment를 주입합니다. `/effort` 설정도, 세션 상태도 필요 없이, 스폰할 때마다 자동으로 `high` effort가 적용됩니다.


모든 sub-agent에 적용하지는 않았습니다. `be-feature-builder`와 `qa-reviewer`에만 추가했고, `fe-feature-builder`와 `design-reviewer`는 제외했습니다. BE 구현은 헥사고날 아키텍처의 레이어 의존성, TDD 사이클, 포트-어댑터 패턴 준수 여부를 동시에 고려해야 하고, QA 리뷰는 아키텍처 위반이나 BE↔FE 계약 불일치를 놓치면 이후 단계에서 비용이 커집니다. 반면 FE 구현과 Design 리뷰는 명확한 스펙을 받아 실행하는 구조라 `medium` effort로 충분했습니다. Opus 4.6의 기본값이 `medium`인 이유 — 대부분의 요청에는 가장 깊은 추론이 필요하지 않다 — 와 같은 판단입니다.


`/effort`의 세션 범위 한계를 프롬프트 설계로 우회한 결과, 세션마다 effort를 재설정해야 한다는 것을 의식하지 않게 됐습니다. 스폰 프롬프트 첫 줄 한 단어가, 세션 상태에 의존하지 않는 추론 깊이 제어의 전부입니다.


---


## 정리


| 메커니즘       | 제어 대상                | 핵심 설계                          |
| ---------- | -------------------- | ------------------------------ |
| Effort     | 동일 모델의 사고 깊이         | 환경변수 > AppState > 모델 기본값 chain |
| Fast Mode  | 요청 라우팅 (Opus 4.6 가속) | Cooldown 상태 머신, 지연 만료 감지       |
| Thinking   | Chain-of-thought 방식  | adaptive 우선, 3단계 기능 감지         |
| Ultrathink | Effort 일시 상향         | API 파라미터 대신 메시지 주입             |


세 가지 메커니즘의 공통 원칙은 하나입니다. **고비용 설정이 세션 간에 누출되어서는 안 된다.** `max` effort가 저장되지 않고, Fast Mode cooldown이 자동 복구되며, Ultrathink가 영구 설정이 아닌 메시지 주입으로 동작하는 것 — 모두 같은 이유에서입니다. 한 세션의 의식적인 선택이 다음 세션으로 묵묵히 이어지면, 잊혀진 리소스 낭비가 됩니다.


---


_참고: Harness Engineering: From Claude Code Internals to AI Coding Best Practices, Chapter 21 — Effort, Fast Mode, Thinking_

