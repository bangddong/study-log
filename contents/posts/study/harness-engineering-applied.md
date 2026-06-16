---
title: '7편에서 배운 것들, 코드에 어떻게 적용했나'
date: '2026-05-19'
tags:
  - AI
  - Claude Code
series: AI
emoji: "\U0001F5C2️"
---

_이 글은_ [_Harness Engineering: From Claude Code Internals to AI Coding Best Practices_](https://github.com/nyang-police/harness-engineering-ko)_를 참고하여 작성된 AI 시리즈의 최종편입니다._


---


이 시리즈는 Claude Code가 이상하다는 느낌에서 시작됐습니다.


세션 초반에 합의한 내용이 사라졌고, grep으로 찾은 결과가 갑자기 지워졌으며, 설정해둔 값이 다음 날 초기화되어 있었습니다. 처음엔 Claude 탓을 했는데, 원서를 읽고 글을 쓰다 보니 전부 제가 잘못 쓰고 있었던 겁니다.


7편에 걸쳐 배운 내용과 switch-job-quest 프로젝트에 어떻게 적용했는지 정리합니다.


---


## 거부한 이유가 사라진다 — Auto Compaction 편


switch-job-quest 프로젝트에서 오케스트레이터가 be-feature-builder, fe-feature-builder, qa-reviewer를 순차 호출하다 보면 컨텍스트가 생각보다 빨리 찹니다. 문제는 서브 에이전트 여러 개를 돌리고 나면 세션 초반에 합의한 내용이 사라진다는 점이었습니다.


실제로 "Kotlin data class 대신 interface로 추상화하지 않기로 했다"고 정했는데, 서브 에이전트 3개가 완료된 후 오케스트레이터가 다시 interface 추상화를 제안하는 상황이 있었습니다. Auto Compaction이 컨텍스트를 167K 기준으로 요약할 때, "무엇을 했는가"는 살아남지만 **"무엇을 하지 않기로 했는가"는 가장 먼저 사라지기** 때문입니다.


이후 `CLAUDE.md`에 `## Compact Instructions` 섹션을 추가했는데, 이 섹션은 auto-compaction 시 자동으로 새 컨텍스트에 주입됩니다.


```javascript
## Compact Instructions
- 현재 브랜치명과 열린 PR 번호 반드시 보존
- 이 세션에서 시도했다 거부한 접근법과 그 이유
- 서브 에이전트 간 합의된 API 인터페이스 스펙
- 발생한 에러와 수정 방법
```


그리고 서브 에이전트 3개 이상 완료 후에는 다음 에이전트를 호출하기 전에 수동 compact를 먼저 실행합니다. 자동 압축을 기다리지 않고 타이밍을 직접 제어하면 압축 직후 파일 재주입 타이밍도 예측할 수 있어서 오케스트레이터 흐름이 훨씬 안정됩니다.


```javascript
/compact 서브 에이전트 완료 결과 중심으로 압축. 거부된 접근법과 API 스펙 보존.
```


---


## 에이전트 간 도구 결과가 지워진다 — Micro Compaction 편


be-feature-builder가 작업을 마치고 API 스펙을 tool result로 돌려줬을 때, 오케스트레이터가 이걸 그대로 fe-feature-builder에게 넘겼습니다. 그런데 fe-feature-builder 입장에서는 API 스펙이 없었고, "API 엔드포인트가 어떻게 되나요?"를 다시 묻거나 추측으로 진행하려 했습니다.


원인은 Micro Compaction이었습니다. 60분 이상 지난 도구 결과, 캐시가 만료된 이전 검색 결과는 조용히 삭제되는데, 도구 결과는 삭제되지만 메시지 본문은 남습니다.


해결은 단순했습니다. 오케스트레이터 프롬프트에서 도구 결과를 그대로 넘기는 대신, 핵심 스펙을 텍스트로 요약해서 명시적으로 포함시키도록 바꿨습니다.


```javascript
BE API: POST /api/quests/{id}/evaluate, body: { answer: string }
```


에이전트 간 핵심 정보 전달은 도구 결과가 아니라 텍스트여야 합니다.


---


## grep이 context를 잡아먹는다 — Token Budget 편


성장 기록 화면 가독성 개선 작업에서 fe-feature-builder가 `**/*.tsx` Glob으로 97개 파일 목록을 뽑은 뒤 관련 컴포넌트 전체를 Read했습니다. 8개 파일을 두 라운드에 나눠 읽었는데, tool result 누적만 약 12K 토큰이었고 이전 대화 맥락이 쌓여 있으면 context 압박이 시작됩니다.


개별 결과가 50K를 넘으면 디스크로 저장되고, 합산이 200K를 넘으면 큰 것부터 선택적으로 저장되기 때문에, 어느 쪽이든 context가 예상보다 빨리 찹니다.


에이전트 파일에 규칙을 명시했습니다. "어떻게 쓰라"가 아니라 "이 형태로 써라" 수준으로 구체화해야 compaction 이후에도 지켜지기 때문에, 명령어를 코드로 직접 박아뒀습니다.


```javascript
Glob 후 관련 파일만 선택적 Read, 병렬 Read 4개 이하

# 빌드 결과는 마지막 20줄만
./gradlew :core:core-api:test 2>&1 | tail -20
```


Spring Boot 배너와 전체 테스트 로그를 그대로 받으면 2~3K 토큰이 날아가는데, 판단에 필요한 건 마지막 20줄뿐이었습니다.


`quest_history` 테이블의 `ai_evaluation_json` 컬럼도 문제였습니다. JSON은 같은 크기라도 일반 텍스트보다 토큰을 2배 쓰는데, QA 리뷰어가 DB 스키마 전체를 Read하면 context 압박이 빠르게 옵니다. qa-reviewer 에이전트 파일에 탐색 범위를 명시하고, 오케스트레이터가 변경 파일 목록을 명시적으로 전달하는 구조로 고정했습니다.


---


## 캐시가 hit되는지 몰랐다 — Cache Architecture + Cache Break Detection 편


switch-job-quest에는 면접 답변을 평가하는 AI Evaluator가 12개 있는데, 기존에는 system 지시사항과 user 입력을 하나의 프롬프트로 합쳐서 보내고 있었습니다.


```kotlin
// 변경 전
chatClient.prompt(systemPrompt + "\n\n" + userInput).call()
```


Prompt caching은 byte 단위 prefix matching이라, user 입력이 달라질 때마다 전체가 달라지는 구조에서는 cache hit이 불가능합니다. system(정적)과 user(동적)를 분리하고, `SYSTEM_ONLY` 캐시 전략을 적용했습니다.


```kotlin
// 변경 후
chatClient
    .system(systemPrompt)  // 평가 기준, 채점 루브릭 — 불변
    .user(userInput)       // 면접 답변 — 매번 변경
    .call()
```


cache strategy는 코드에 하드코딩하지 않고 프로퍼티로 외부화했는데, 런타임 중 strategy가 바뀌면 이미 캐시된 요청과 prefix가 달라져 cache bust가 발생하기 때문입니다. Latching의 "세션 시작 시 결정을 고정"과 같은 원칙을, 애플리케이션에서는 "배포 단위로 고정"하는 방식으로 적용한 셈입니다.


```yaml
devquest:
  ai:
    boss-cache-strategy: SYSTEM_ONLY
```


캐시를 적용했는데 실제로 hit되고 있는지는 알 방법이 없었습니다. `cache_read_input_tokens`가 0이어도 에러가 없고, 비용이 늘고 있다는 사실을 뒤늦게 알아차릴 뿐이기 때문입니다. Spring AI `CallAdvisor` 패턴으로 `CacheMetricsAdvisor`를 구현해 ChatClient 빈에 등록했고, 각 Evaluator를 수정하지 않고도 모든 AI 호출 응답에서 cache 지표를 추출합니다.


Evaluator가 단발성 호출이라 "이전 상태"와 비교하는 Phase 1은 적용하지 않았고, 응답 후 토큰 수치를 확인하는 Phase 2만 적용했습니다.


```javascript
cache_creation_input_tokens > 2,000 AND cache_read_input_tokens == 0 → WARN 로그
```


Cache break의 90%가 서버 측 원인이라는 분석 결과도 방향을 바꾸는 데 도움이 됐습니다. "모든 break를 없애겠다"는 목표 대신, **통제 가능한 클라이언트 10%에 집중**하는 방향으로 바꿨습니다.


---


## [CONTEXT.md](http://context.md/)가 매일 캐시를 깨뜨렸다 — Cache Optimization 편


`CONTEXT.md` 파일을 열어보니 헤더에 날짜가 박혀 있었습니다.


```markdown
## 현재 상태 (2026-05-12)
```


오케스트레이터가 매 작업 시작 시 이 파일을 갱신하는데, 날짜가 바뀐 날 새 작업을 시작하면 헤더도 함께 변경됩니다. 날짜가 바뀌면 파일 전체가 diff로 잡히고, 이후 내용까지 "변경된 파일"로 인식되어 캐시 효과를 잃습니다.


헤더에서 날짜를 제거하고, 날짜는 "최근 완료" 표의 각 PR 행에만 남겼습니다. [orchestrator.md](http://orchestrator.md/) 지침에도 명시했습니다.


```javascript
헤더에 날짜를 포함하지 않는다. 날짜는 최근 완료 행에만 기록한다.
```


또 다른 문제가 있었습니다. PR 생성 후 `CONTEXT.md`를 수정했지만 커밋 없이 세션을 종료한 적이 있었는데, 다음 세션에서 파일이 이전 상태로 복원됐습니다. "현재 상태가 기록됐다"는 사실 자체가 불안정했던 겁니다. 9단계 프로세스에 커밋과 push를 필수 절차로 추가했습니다.


```bash
git add .claude/CONTEXT.md
git commit -m "chore: CONTEXT.md 갱신 — PR #<번호>"
git push
```


cache prefix를 안정적으로 유지하는 것과 세션 메타데이터를 안정적으로 유지하는 것은 레이어만 다를 뿐 같은 원칙입니다. **안정적인 내용이 앞에, 쓴 내용은 사라지지 않아야 합니다.**


---


## 에이전트마다 추론 깊이가 달라야 했다 — Effort / Fast Mode / Thinking 편


코딩 퀘스트 기능(PR #136)에서 fe-feature-builder가 BE API 스펙을 받고도 중첩 타입을 잘못 추론했습니다. testCases, constraints 필드가 실제로는 object[]인데 string[]으로 처리했고, QA 리뷰에서 잡혀 재스폰했는데 수정 과정에서 props drilling 구조까지 바뀌어 상위 컴포넌트도 연쇄 수정됐습니다. 돌아보면 스폰 프롬프트 첫 줄에 ultrathink가 없었고, FE 구현은 타입 정의 → props drilling → 컴포넌트 분리 순서로 연쇄 결정이 필요한 작업이라 낮은 추론 수준으로 시작하면 한 곳에서 생긴 오류가 구조 전체로 번집니다. 이후 fe-feature-builder 스폰 프롬프트 첫 줄에 ultrathink를 추가했고, BE 스펙을 받으면 타입 구조를 재귀적으로 분석한 뒤 구현을 시작하게 됩니다.


비슷한 문제가 design-reviewer에서도 있었습니다. 오케스트레이터가 "참고할 기존 컴포넌트 경로"를 전달하는데도 경로를 파일 목록으로만 처리하고 실제 색상·간격·구조 규칙을 깊이 분석하지 않았고, fe-feature-builder가 그 스펙을 그대로 따르다 보니 기존 컴포넌트와 시각적으로 어긋난 UI가 만들어졌습니다. 컴포넌트 간 일관성은 파일을 열어보는 것만으로는 파악하기 어렵고 기존 패턴에서 추상화 원칙을 끌어내는 작업이 필요하기 때문에, design-reviewer에도 스폰 프롬프트 첫 줄에 ultrathink를 추가했습니다.


ultrathink를 모든 에이전트에 무조건 박는 것은 맞지 않습니다. 오케스트레이터는 "무엇을 누구에게 시킬지" 빠르게 분기하는 역할이라 깊은 추론보다 빠른 판단이 더 중요하고, 구현·설계·검토처럼 연쇄 결정이 필요한 에이전트에만 ultrathink를 두는 것이 "작업 복잡도에 맞게 추론 깊이를 조정하라"는 원칙과 맞습니다. 스폰 프롬프트 첫 줄 한 단어가 그 조정의 전부입니다.


---


## 정리


| 편                     | 문제                                       | 적용                                         |
| --------------------- | ---------------------------------------- | ------------------------------------------ |
| Auto Compaction       | 거부 이유가 사라짐                               | `## Compact Instructions`  • 수동 `/compact` |
| Micro Compaction      | 도구 결과가 지워짐                               | 에이전트 간 정보는 텍스트로 명시                         |
| Token Budget          | context가 예상보다 빨리 참                       | grep 범위 제한, tail 파이프, JSON 조회 범위 고정        |
| Cache Architecture    | system/user 분리 없이 캐시 불가                  | `SYSTEM_ONLY` 전략 + 프로퍼티 외부화                |
| Cache Break Detection | 캐시 hit 여부를 몰랐음                           | `CacheMetricsAdvisor` (Phase 2만 적용)        |
| Cache Optimization    | [CONTEXT.md](http://context.md/)가 매일 변경됨 | 날짜 제거 + 커밋 필수화                             |
| Effort / Thinking     | 에이전트 추론 깊이가 균일했음                         | 구현·설계·검토 에이전트 스폰 프롬프트 첫 줄에 ultrathink 추가   |


시리즈를 쓰기 전에도 AI를 쓰고 있었습니다. 달라진 건 AI의 동작이 아니라, 무엇을 파일에 박고 무엇을 텍스트로 전달하며 어떤 규칙을 대화가 아닌 구조로 고정하는지였습니다.


---


_참고: Harness Engineering: From Claude Code Internals to AI Coding Best Practices — Chapter 9, 10, 12, 13, 14, 15, 21_

