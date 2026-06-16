---
title: 오래된 grep 결과는 어디로 갔는가 — Micro Compaction이 모르게 하는 3가지
date: '2026-04-25'
tags:
  - AI
  - Claude Code
series: AI
emoji: "\U0001F52C"
---

Claude Code로 작업하다 보면 가끔 이런 메시지를 보게 됩니다.

> [Old tool result content cleared]

분명히 방금 전에 grep으로 찾은 결과인데, Claude가 갑자기 그 결과를 모른다고 합니다. 이건 Claude가 멍청해진 게 아닙니다. **Micro Compaction**이 조용히 일을 한 겁니다.


## Micro Compaction이란?


[지난 글](https://dhbang.co.kr/posts/study/harness-engineering-auto-compaction/)에서 다룬 Auto Compaction은 컨텍스트가 167K 토큰(전체의 83.5%)에 도달하면 전체 대화 내용을 AI가 요약해서 새로 시작하는 방식이었습니다.


Micro Compaction은 그것과 달리 **AI를 전혀 호출하지 않습니다.** 오래된 특정 도구 결과만 정확히 골라내어 삭제하는 가벼운 정리 작업입니다.

> "The cheapest token is the one you never send."

책에서 강조하는 이 원칙이 Micro Compaction의 핵심입니다. 한 시간 전에 실행한 grep 결과는 지금 대화와 관련이 없을 가능성이 높습니다. 이걸 계속 컨텍스트에 끌고 다니는 건 낭비입니다.


## 세 가지 메커니즘


Claude Code는 Micro Compaction을 세 가지 방식으로 구현하고 있습니다.


### 1. 시간 기반 (Time-Based)


**조건**: 마지막 응답으로부터 **60분** 이상 경과


점심을 먹고 와서 작업을 이어받거나, 오랜 회의 후 돌아왔을 때 작동합니다. 60분이라는 기준은 우연이 아닙니다. Anthropic 서버가 프롬프트 캐시를 유지하는 TTL이 1시간입니다. 캐시가 만료되는 시점이라면 오래된 도구 결과를 삭제해도 추가적인 손해가 없습니다.

- 오래된 도구 결과를 `[Old tool result content cleared]` 플레이스홀더로 교체
- 가장 최근 5개 결과는 보존

### 2. 캐시 기반 (Cached / cache_edits)


**조건**: 활성 세션에서 삭제 가능한 도구 결과가 임계값 초과


이 방식이 가장 정교합니다. 단순 삭제가 아닌 **cache_edits**라는 서버 측 지시를 활용해 캐시 prefix를 그대로 유지하면서 내용만 제거합니다.


캐시가 살아있는 상태에서 내용만 교체하기 때문에, 캐시 비용을 낭비하지 않으면서 오래된 내용을 정리할 수 있습니다. 비용과 효율을 동시에 챙기는 방식입니다.


**중요한 제약**: 이 메커니즘은 **메인 스레드에서만 실행됩니다.** 서브 에이전트가 등록한 도구 ID를 메인 스레드가 삭제하려 하면 존재하지 않는 ID를 참조하는 잘못된 cache_edits 지시가 만들어집니다. 그래서 서브 에이전트 컨텍스트에서는 이 메커니즘이 작동하지 않습니다.


### 3. API 선언형 (API Context Management)


**조건**: API 레벨에서 input_tokens가 임계값 초과


서버 측에서 자동으로 실행되는 선언형 방식입니다. 이 방식은 일반 세션뿐 아니라 thinking 모델에도 적용됩니다. 도구 결과 삭제 외에 thinking 블록 관리도 함께 처리합니다.


## 어떤 도구 결과가 지워지나?


```javascript
삭제 대상 (시간/캐시 기반):
FileRead, Shell, Grep, Glob, WebSearch, WebFetch, FileEdit, FileWrite

삭제 대상 (API 선언형):
Shell, Glob, Grep, FileRead, WebFetch, WebSearch

API 선언형에서 제외:
FileEdit, FileWrite, NotebookEdit
```


편집 결과는 API 선언형에서 삭제되지 않습니다. "어떤 파일을 어떻게 수정했는가"는 작업 맥락의 핵심이기 때문입니다.


## [CLAUDE.md](http://claude.md/)는 지워지지 않는다


가장 중요한 사실입니다. [CLAUDE.md](http://claude.md/)를 통해 주입된 내용은 **시스템 프롬프트**로 들어갑니다. Micro Compaction은 도구 결과만 대상으로 하기 때문에 시스템 프롬프트는 어떤 메커니즘에서도 건드리지 않습니다.


이 때문에 [지난 글](https://dhbang.co.kr/posts/study/harness-engineering-auto-compaction/)에서 추가한 `## Compact Instructions` 전략이 유효합니다. [CLAUDE.md](http://claude.md/)에 적어둔 거부 규칙과 핵심 맥락은 60분이 지나도 사라지지 않습니다.


## 세 메커니즘의 우선순위


세 메커니즘이 동시에 동작하지는 않습니다.

- 시간 기반과 캐시 기반은 **상호 배타적**: 시간 기반은 캐시가 만료된 경우에만 작동 ("캐시 편집은 따뜻한 캐시를 전제")
- API 선언형은 독립적으로 서버 측에서 처리

결과적으로 이런 계층이 만들어집니다.


```javascript
캐시 따뜻함  → 캐시 기반 micro-compaction (cache_edits)
캐시 만료 (60분+) → 시간 기반 micro-compaction
API 임계 도달  → API 선언형
```


## 실제 개발에서 의미하는 것


**"[Old tool result content cleared]가 보였다면"**


이건 Claude가 실패한 게 아닙니다. 이 경우 "아까 검색한 결과 다시 알려줘"라고 요청하는 것보다 검색을 다시 실행하는 게 훨씬 낫습니다.


**"오케스트레이터가 같은 파일을 반복 읽는다면"**


긴 세션에서 오케스트레이터가 한 시간 전에 읽었던 파일을 다시 읽는 건 비효율처럼 보이지만, 실제로는 이전 결과가 삭제되어 재조회가 필요한 정상 동작일 수 있습니다.


**"서브 에이전트는 항상 새 컨텍스트"**


캐시 기반 micro-compaction이 메인 스레드에서만 실행된다는 사실은 서브 에이전트 구조를 설명합니다. 각 서브 에이전트는 독립된 컨텍스트를 가지며, 에이전트 간 도구 결과 공유는 오케스트레이터가 명시적으로 전달해야 합니다.


## 직접 겪은 사례


switch-job-quest 프로젝트는 오케스트레이터가 be-feature-builder → fe-feature-builder → qa-reviewer 순서로 서브 에이전트를 호출합니다. 서브 에이전트 하나가 끝나고 다음 에이전트를 호출하기까지 시간이 걸리다 보면, 앞서 be-feature-builder가 실행한 Grep 결과가 `[Old tool result content cleared]`로 바뀌어 있는 경우가 있었습니다.


fe-feature-builder 입장에서는 BE API 스펙을 알 수 없으니 "API 엔드포인트가 어떻게 되나요?"를 오케스트레이터에게 다시 묻거나, 추측으로 진행하려 했습니다.


해결은 간단했습니다. 오케스트레이터 프롬프트에 도구 결과를 그대로 넘기는 대신, 핵심 스펙을 텍스트로 요약해서 명시적으로 포함시켰습니다. 도구 결과는 삭제되지만 메시지 본문은 남기 때문입니다.


```javascript
BE API: POST /api/quests/{id}/evaluate, body: { answer: string }
```


서브 에이전트 간 정보 전달은 "결과를 넘긴다"가 아니라 **"요약을 넘긴다"** 가 맞습니다.


## 정리


| 메커니즘    | 트리거           | 캐시 영향        | 적용 범위 |
| ------- | ------------- | ------------ | ----- |
| 시간 기반   | 60분 경과        | 캐시 prefix 깨짐 | 메인+서브 |
| 캐시 기반   | 임계 초과 (활성 세션) | 캐시 유지        | 메인 전용 |
| API 선언형 | token 임계 도달   | 서버 처리        | 모든 세션 |


Claude Code는 눈에 띄지 않는 방식으로 비용을 최적화하고 있습니다. 도구 결과가 사라지는 것이 불안하게 느껴질 수 있지만, [CLAUDE.md](http://claude.md/)의 지시는 살아있고 작업 맥락은 보존됩니다. 한 시간 전의 grep 결과를 버리는 건 현명한 선택입니다.


---


_Reference: Harness Engineering: From Claude Code Internals to AI Coding Best Practices, Path C: Performance Optimization (Ch.11)_

