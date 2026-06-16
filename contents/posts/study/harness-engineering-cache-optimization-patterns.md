---
title: '날짜 하나가 11,000 토큰을 날린다 — Claude Code의 Cache 최적화 7가지 전술'
date: '2026-05-09'
tags:
  - AI
  - Claude Code
series: AI
emoji: ⚡
---

_이 글은_ [_Harness Engineering: From Claude Code Internals to AI Coding Best Practices_](https://github.com/nyang-police/harness-engineering-ko)_를 참고하여 작성되었습니다. 시리즈 주제: 경로 C — 성능 최적화 (LLM 애플리케이션 비용 및 지연 시간)_


---


이전 글(Chapter 14)에서 cache break 탐지 시스템을 다뤘습니다. BigQuery에 쌓인 `tengu_prompt_cache_break` 데이터는 반복적인 원인 패턴을 드러냈습니다. 다음 질문은 자연스러웠습니다: 발생한 break를 감지하는 것도 좋지만, 애초에 깨지지 않게 할 수는 없을까?


Claude Code는 이 질문에 7개의 최적화 패턴으로 답합니다.


---


## 탐지 데이터가 먼저다


7가지 패턴은 모두 Chapter 14의 탐지 시스템이 수집한 데이터에서 나왔습니다. BigQuery를 통해 break 원인의 패턴이 드러나면, 엔지니어링 팀이 맞춤형 최적화를 설계했습니다. 관측가능성이 최적화보다 먼저입니다.


| # | 패턴                    | 원인              | 전략                           | 영향                      |
| - | --------------------- | --------------- | ---------------------------- | ----------------------- |
| 1 | Date Memoization      | 자정 날짜 변경        | `memoize(getLocalISODate)`   | System prompt           |
| 2 | Monthly Granularity   | 매일 날짜 변경        | "Month YYYY" 형식              | Tool prompt             |
| 3 | Agent 목록 → Attachment | 동적 Agent 목록     | tool description → message 끝 | cache_creation 10.2% 제거 |
| 4 | Skill List Budget     | Skill 수 증가      | Context window 1% 제한         | Tool schema             |
| 5 | $TMPDIR Placeholder   | 사용자 UID 포함 경로   | 환경변수 대체                      | Global cache            |
| 6 | 조건부 문단 생략             | Feature flag 변경 | Prefix 단조 안정성                | System prompt           |
| 7 | Tool Schema Cache     | GrowthBook 재평가  | Session 수준 Map               | 모든 tool schema          |


---


## 패턴 1: Date Memoization


자정마다 system prompt의 날짜가 바뀝니다. 날짜 하나 때문에 11,000개 token의 prefix cache가 무효화됩니다.


```typescript
export const getSessionStartDate = memoize(getLocalISODate)
```


Session 시작 시 날짜를 한 번 캡처하고, 이후에는 같은 값을 재사용합니다. 자정이 지나도 session이 살아있는 동안은 날짜가 바뀌지 않습니다.


자정 이후 세션에서 오래된 날짜를 보게 되는 trade-off가 있습니다. `getDateChangeAttachments`가 message 끝에 새 날짜를 추가하는 방식으로 정확성을 보완합니다. Prefix를 안정적으로 유지하면서, 날짜 정확성은 message 레이어에서 처리합니다.


---


## 패턴 2: Monthly Granularity


Tool prompt에서도 날짜를 사용할 때가 있습니다. 전체 날짜를 쓰면 매일 cache가 무효화됩니다.


```typescript
export function getLocalMonthYear(): string {
  return date.toLocaleString('en-US', { month: 'long', year: 'numeric' })
}
// "April 2026" → 한 달에 한 번만 변경
```


**API 요청의 앞쪽에 있을수록 변경 빈도가 낮아야 합니다.** Tool prompt가 system prompt보다 뒤에 위치하더라도, 불필요하게 자주 바뀌면 그 뒤의 cache에 영향을 줍니다. 정밀도를 낮춰 빈도를 줄이는 방식입니다.


---


## 패턴 3: Agent 목록을 Attachment로 이동


`AgentTool`의 tool description에 동적 agent 목록이 들어있었습니다. Agent가 추가되거나 제거될 때마다 tool schema가 바뀌고 cache가 깨졌습니다. BigQuery 분석 결과 이것이 `cache_creation` token의 **10.2%를 낭비**하고 있었습니다.


수정 방향은 위치 변경입니다.


```javascript
Before: tool description → "현재 agent: [A, B, C, ...]"  (prefix 앞쪽)
After:  user message의 agent_listing_delta attachment      (prefix 끝쪽)
```


Attachment는 message 끝에 추가되므로 그 앞의 prefix cache에 영향을 주지 않습니다. 내용이 바뀌어도 앞쪽 cache는 유지됩니다.


---


## 패턴 4: Skill List Budget


Skill 생태계가 성장하면서 skill 목록이 길어졌습니다. 새로운 skill이 추가될 때마다 목록이 변경되고 cache가 깨집니다.


```typescript
export const SKILL_BUDGET_CONTEXT_PERCENT = 0.01
export const MAX_LISTING_DESC_CHARS = 250
```


전체 context window의 1%로 skill 목록을 제한합니다. Budget이 가득 차면, 새로운 skill이 추가되어도 trimming된 결과가 같을 수 있습니다. 목록 변경이 cache break으로 이어지는 연결고리를 끊습니다.


---


## 패턴 5: $TMPDIR Placeholder


BashTool prompt에는 임시 디렉토리 경로가 포함됩니다. 이 경로가 사용자별로 다르다는 점이 문제입니다.


```javascript
사용자 A: /private/tmp/claude-1001/...
사용자 B: /private/tmp/claude-1042/...
```


사용자마다 바이트가 다르면 global cache hit이 불가능합니다.


```typescript
const normalizeAllowOnly = (paths: string[]): string[] =>
  paths.map(p => (p === claudeTempDir ? '$TMPDIR' : p))
```


절대 경로를 `$TMPDIR` placeholder로 대체하면 모든 사용자의 prompt가 동일해집니다. Global cache 공유가 가능해집니다.


---


## 패턴 6: 조건부 문단 생략


Feature flag가 켜지고 꺼질 때마다 system prompt의 문단이 나타났다 사라집니다. 문단 하나의 등장/소멸이 그 뒤 전체 prefix를 무효화합니다.


**"말했다가 제거하는 것보다 아예 말하지 않는 것이 낫다."**

- 조건부 문단을 정적 텍스트로 대체하거나 항상 포함/제외 결정
- 불가피하다면 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 이후에 배치
- Message attachment 메커니즘 활용

목표는 **단조적 안정성(monotonic stability)**입니다. Prefix의 system prompt 블록이 session 전체에 걸쳐 변하지 않아야 합니다.


---


## 패턴 7: Tool Schema Cache


Tool schema 직렬화 과정에서 GrowthBook flag를 매 요청마다 재평가합니다. Flag 값이 바뀌면 schema가 바뀌고 cache break이 발생합니다.


```typescript
const TOOL_SCHEMA_CACHE = new Map<string, CachedSchema>()

export function getToolSchemaCache(): Map<string, CachedSchema> {
  return TOOL_SCHEMA_CACHE
}
```


Module 수준 Map에 첫 렌더링 결과를 저장합니다. 이후 요청에서는 Map을 재사용합니다.


Cache key 설계가 핵심입니다. 이름이 같아도 schema가 다를 수 있기 때문입니다.


```typescript
const cacheKey =
  'inputJSONSchema' in tool && tool.inputJSONSchema
    ? `${tool.name}:${jsonStringify(tool.inputJSONSchema)}`
    : tool.name
```


StructuredOutput처럼 이름은 동일하지만 schema가 다른 케이스를 처리합니다. 이 설계로 5.4% → 51% 오류율 문제를 해결했습니다.


생명주기: 첫 `toolToAPISchema()` 호출 시 생성 → 이후 재사용 → session 종료 시 `clearToolSchemaCache()`로 초기화.


---


## 최적화 의사결정 흐름


7가지 패턴을 하나의 결정 흐름으로 정리하면 이렇습니다.


```javascript
동적 콘텐츠 발견
  ↓
반드시 prefix에 있어야 하는가?
  No  → Message 끝에 이동 (패턴 3)
  Yes ↓
사용자별 차이를 제거할 수 있는가?
  Yes → Placeholder/정규화 (패턴 5)
  No  ↓
변경 빈도를 줄일 수 있는가?
  Yes → Memoization / 정밀도 감소 / Session cache (패턴 1, 2, 7)
  No  ↓
변경 규모를 제한할 수 있는가?
  Yes → Budget 제어 / 조건부 생략 (패턴 4, 6)
  No  → Dynamic region으로 표시 (scope: null)
```


---


## 직접 겪은 사례


### 사례 1: [CONTEXT.md](http://context.md/) 헤더의 날짜 — Pattern 2 적용


오케스트레이터는 매 작업 시작 시 `.claude/CONTEXT.md`의 "현재 상태" 섹션을 갱신합니다. 파일을 열어보니 헤더에 날짜가 박혀 있었습니다.


```markdown
## 현재 상태 (2026-05-12)
```


0단계 지침이 "현재 상태 표를 갱신한다"였고, 날짜가 바뀐 날 새 작업을 시작하면 헤더도 함께 변경됐습니다. 날짜가 바뀌면 파일 전체가 diff로 잡히고, 이후 내용까지 "변경된 파일"로 인식됩니다.


Pattern 2의 원칙은 "정밀도를 낮춰 변경 빈도를 줄인다"입니다. 날짜를 헤더에서 아예 제거했습니다.


```markdown
## 현재 상태
```


날짜 정보는 "최근 완료" 표의 각 PR 행에만 유지합니다. 헤더는 이제 세션이 바뀌어도 변하지 않습니다. `orchestrator.md` 0단계 지침에도 "헤더에 날짜를 포함하지 않는다. 날짜는 최근 완료 행에만 기록한다"는 제약을 명시했습니다.


`CONTEXT.md`는 system prompt 캐시 대상이 아니라 session마다 `cat`으로 읽히는 파일입니다. 직접적인 cache hit 수치 변화보다는, 오케스트레이터가 불필요하게 파일을 수정하는 행동을 없애는 것이 목적입니다. "앞쪽에 있을수록 변경 빈도가 낮아야 한다"는 원칙은 캐시 레이어를 막론하고 동일하게 적용됩니다.


---


### 사례 2: [CONTEXT.md](http://context.md/) 커밋 누락 — Pattern 6의 단조 안정성


Pattern 6의 핵심은 **단조 안정성(monotonic stability)**입니다. "말했다가 제거하는 것보다 아예 말하지 않는 것이 낫다." Prefix가 session 전체에 걸쳐 변하지 않아야 한다는 원칙입니다.


이 원칙을 코드 레이어가 아닌 메타데이터 레이어에서 위반하고 있었습니다. 오케스트레이터는 PR 생성 후 `CONTEXT.md`를 수정했지만, 커밋 없이 세션을 종료했습니다.


```javascript
PR 생성 → CONTEXT.md 수정(브랜치·PR 번호 기록) → 세션 종료
         ↓
다음 세션에서 CONTEXT.md가 이전 상태로 복원됨
```


"현재 상태가 기록됐다"는 사실 자체가 불안정했습니다. Pattern 6이 feature flag 문단을 attachment로 옮겨 "등장/소멸"을 막는 것처럼, 9단계 프로세스에 커밋·push를 필수 절차로 추가했습니다.


```bash
git add .claude/CONTEXT.md
git commit -m "chore: CONTEXT.md 갱신 — PR #<번호>"
git push
```


코드 레이어의 cache prefix를 안정적으로 유지하는 것과, 세션 메타데이터를 안정적으로 유지하는 것은 레이어만 다를 뿐 같은 원칙입니다. 쓴 내용이 사라지지 않는 것이 단조 안정성의 전제입니다.


---


## 정리


| 패턴                    | 문제                        | 핵심 접근                 |
| --------------------- | ------------------------- | --------------------- |
| Date Memoization      | 자정 prefix 무효화             | Session 시작 시 날짜 고정    |
| Monthly Granularity   | 매일 cache 만료               | 월 단위 변경으로 빈도 감소       |
| Agent 목록 → Attachment | cache_creation 10.2% 낭비   | 동적 목록을 message 끝으로 이동 |
| Skill List Budget     | 목록 성장으로 잦은 변경             | Context window 1% 상한  |
| $TMPDIR Placeholder   | 사용자별 경로 차이                | 환경변수로 통일              |
| 조건부 문단 생략             | Feature flag → prefix 불안정 | 단조 안정성 확보             |
| Tool Schema Cache     | GrowthBook 재평가 비용         | Module 수준 Map 캐시      |


7가지 패턴의 공통 방향은 하나입니다. **동적 콘텐츠를 prefix 앞쪽에서 끝쪽으로, 불가능하면 변경 빈도를 줄이는 방향으로.** Cache 최적화는 특정 모듈의 문제가 아니라, 요청을 구성하는 모든 지점에 스며드는 설계 원칙입니다.


---


_참고: Harness Engineering: From Claude Code Internals to AI Coding Best Practices, Chapter 15 — Cache 최적화 패턴_

