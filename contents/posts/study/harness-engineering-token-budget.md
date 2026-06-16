---
title: Claude가 파일을 디스크에 저장하는 이유 — Token Budget 3중 방어 해부
date: '2026-04-27'
tags:
  - AI
  - Claude Code
series: AI
emoji: "\U0001F5C4️"
---

_이 글은_ [_Harness Engineering: From Claude Code Internals to AI Coding Best Practices_](https://zhanghandong.github.io/harness-engineering-from-cc-to-ai-coding/en/preface.html)_를 참고하여 작성되었습니다. 시리즈 주제: 경로 C — 성능 최적화 (LLM 애플리케이션 비용 및 지연 시간)_


---


Claude Code로 대용량 코드베이스를 검색하다 보면 이런 메시지를 보게 됩니다.

> Output too large (82.3 KB). Full output saved to: /tmp/tool-results/toolu_01XYZ.txt
> Preview (first 2.0 KB): ...

분명히 grep 명령을 실행했는데, 결과가 파일로 저장됐다고 합니다. [지난 글](https://dhbang.co.kr/posts/study/harness-engineering-micro-compaction/)의 `[Old tool result content cleared]`가 오래된 결과를 조용히 지웠다면, 이번엔 처음부터 디스크에 숨겨버리는 겁니다. 이것 역시 Claude의 실패가 아닙니다. **Token Budget** 시스템이 동작한 것입니다.


이 글에서는 Claude Code가 어떻게 토큰 예산을 관리하는지, 3중 방어 시스템을 층별로 해부합니다.


---


## 3중 방어 시스템 개요


```javascript
Layer 1: 개별 tool result    — 50K 초과 시 디스크 저장
Layer 2: 메시지 단위 총합     — 200K 한도 집계 관리
Layer 3: 토큰 카운팅         — 정확도를 위한 이중 계산법
```


Auto Compaction이 167K 토큰에서 전체 대화를 요약하는 "최후의 보루"라면, Token Budget은 그 전에 작동하는 예방 시스템입니다. 이 3중 방어 덕분에 context가 훨씬 느리게 찹니다.


---


## Layer 1 — 50K 방어선: 개별 tool result


### 무엇이 일어나는가


tool result 하나의 크기가 50,000자를 초과하면, 시스템은 전체 내용을 로컬 디스크 임시 파일에 씁니다. 모델이 context에서 받는 것은 두 가지뿐입니다.


```javascript
저장된 파일 경로: /tmp/tool-results/toolu_01XYZ.txt
Preview (앞 2,000바이트): def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', ...
(이하 생략)
```


전체 내용이 사라지는 게 아닙니다. context 밖으로 옮겨진 것이며, 모델이 전체 내용이 필요하다면 Read tool로 파일을 직접 읽으면 됩니다.


### tool별 한도를 결정하는 4단계 우선순위


50K는 기본값일 뿐, 모든 tool에 동일하게 적용되지는 않습니다. 각 tool의 임계값은 다음 우선순위로 결정됩니다.


| 우선순위   | 조건                      | 결과                       |
| ------ | ----------------------- | ------------------------ |
| 1 (최고) | tool이 `Infinity` 선언     | 절대 디스크 저장 안 함            |
| 2      | GrowthBook 플래그 override | 원격 설정값 사용 (배포 없이 실시간 변경) |
| 3      | tool이 커스텀 한도 선언         | `Math.min(선언값, 50K)`     |
| 4 (기본) | 특별 선언 없음                | 50,000자                  |


3순위에서 `Math.min`을 쓰는 이유가 있습니다. tool이 "100K까지 허용"이라고 선언해도 시스템 기본값(50K)을 초과할 수 없습니다. tool 선언이 시스템 한도를 우회하지 못하도록 막는 겁니다.


### Read tool은 왜 예외인가


Read tool은 `maxResultSizeChars = Infinity`를 선언합니다. 이 예외 없이는 순환 루프가 생깁니다.


```javascript
① Read tool로 파일 읽음 (80K)
② 50K 초과 → 디스크에 저장
③ 모델: "결과를 보려면 이 파일을 Read tool로 읽어야 해"
④ Read tool로 임시 파일 읽음 (80K)
⑤ 50K 초과 → 디스크에 저장
⑥ 모델: "또 읽어야 해"
⑦ 무한 루프
```


비용 문제가 아니라 논리적으로 탈출할 수 없는 구조입니다. 그래서 Read tool의 결과는 크기와 무관하게 항상 전체 내용을 context에 포함시킵니다.


### 빈 결과 처리


tool이 결과를 반환하지 않으면 빈 문자열 대신 placeholder를 주입합니다.


```javascript
(toolName completed with no output)
```


일부 모델 버전이 빈 tool result를 대화 경계로 잘못 인식하는 버그를 방지하기 위한 처리입니다.


---


## Layer 2 — 200K 방어선: 메시지 단위 집계


### 왜 Layer 1으로 충분하지 않은가


개별 result가 50K 미만이어도 병렬로 여러 개가 동시에 쌓이면 합산이 폭발합니다.


```javascript
grep_1: 40K  ← Layer 1 통과
grep_2: 40K  ← Layer 1 통과
grep_3: 40K  ← Layer 1 통과
...
grep_10: 40K ← Layer 1 통과
——————————————
합계: 400K   ← context 폭발
```


10개 병렬 grep이 동시에 실행되면 각각 문제 없어 보여도 합산하면 400K가 됩니다. Layer 2는 이 집계를 200K 이하로 제한합니다.


### 선택 알고리즘


200K 한도를 초과하면 fresh 결과물을 크기 내림차순으로 정렬하고, 큰 것부터 디스크로 보냅니다.


```javascript
fresh 결과물 (크기 내림차순 정렬):
  grep_5: 45K  → 디스크 (경로 + 2K preview만 context에)
  grep_3: 42K  → 디스크 (경로 + 2K preview만 context에)
  ——————————————————
  남은 합계: 40K + 38K + 35K = 113K → 200K 이하 ✅
  ——————————————————
  grep_1: 40K  → context에 full content
  grep_4: 38K  → context에 full content
  grep_2: 35K  → context에 full content
```


**중요**: 200K 계산은 원본 크기 기준입니다. 디스크로 보낸 결과물의 preview(~2K)는 계산에 포함되지 않습니다. 결정이 원본 크기 기준으로 고정되어야 매 API 호출마다 동일한 결론이 나오기 때문입니다.


### Tri-state: prompt cache가 만든 복잡성


prompt cache 때문에 복잡성이 생깁니다. 한 번 API 호출에서 내린 결정(context 포함 or 디스크 저장)은 이후 API 호출에서 바꿀 수 없습니다. 바꾸면 cache prefix가 깨집니다.


그래서 각 tool result는 세 가지 상태로 관리됩니다.


| 상태              | 의미                     | 처리 방식                  |
| --------------- | ---------------------- | ---------------------- |
| **fresh**       | 이번 호출에서 처음 등장          | 200K 알고리즘으로 지금 결정      |
| **frozen**      | 이전에 "context 포함"으로 결정됨 | 변경 불가 — 무조건 포함         |
| **mustReapply** | 이전에 "디스크"로 결정됨         | 변경 불가 — 무조건 디스크 경로로 표시 |


```javascript
[API 호출 1]
grep_1 → fresh → "context 포함" 결정 → frozen으로 변경

[API 호출 2]
grep_1 다시 등장 → frozen 확인 → 강제로 context 포함
(디스크로 바꾸면 cache prefix가 깨짐)
```


한 번 결정된 것은 세션 내내 유지됩니다. 복잡해 보이지만 이 구조가 없으면 API 호출마다 결정이 달라져서 prompt cache 자체가 무의미해집니다.


**예외**: frozen 결과만으로 이미 200K를 초과하면, 새로 들어오는 fresh 결과도 그냥 포함시킵니다. "어차피 넘쳤으니 Micro Compaction이 나중에 정리하겠지"라는 설계입니다.


---


## Layer 3 — 토큰 카운팅: 정확도를 위한 이중 계산


compaction을 언제 실행할지 결정하려면 "지금 토큰이 얼마나 쌓였는가"를 알아야 합니다. 그런데 이걸 정확하게 세는 것이 생각보다 복잡합니다.


### 캐노니컬 vs 러프 에스티메이션


| 방식                        | 데이터 소스           | 정확도     | 사용 가능 시점   |
| ------------------------- | ---------------- | ------- | ---------- |
| **캐노니컬 (Canonical)**      | API 응답의 usage 필드 | 정확      | API 호출 후에만 |
| **러프 (Rough Estimation)** | 문자 수 / 바이트 환산    | ±50% 오차 | 언제든        |


캐노니컬 계산식:


```javascript
input_tokens
+ cache_creation_input_tokens
+ cache_read_input_tokens
+ output_tokens
= 정확한 토큰 수
```


API를 호출한 후에야 알 수 있습니다. 호출 전에는 러프 에스티메이션을 씁니다.


### 콘텐츠 유형별 바이트 기준


러프 에스티메이션은 기본적으로 **4바이트 = 1토큰** 공식을 씁니다. 하지만 콘텐츠 유형마다 다른 기준을 적용합니다.


| 콘텐츠 유형       | 기준             | 이유                                 |
| ------------ | -------------- | ---------------------------------- |
| 일반 텍스트 / 코드  | 4바이트 / token   | 영어 기준 평균값                          |
| JSON / JSONL | 2바이트 / token   | `{`, `}`, `:` 같은 단일 문자가 각각 1 token |
| 이미지 / PDF    | 고정 2,000 token | base64 인코딩 시 문자 수 폭발 방지            |


이미지를 문자 수로 추정하면 1MB PDF → 약 1.33M 문자 → 약 325K 토큰으로 계산됩니다. 실제는 2,000 토큰입니다. 고정값이 없으면 치명적인 과대평가로 이어집니다.


또 하나 주의할 것은 **JSON이 코드보다 토큰을 더 많이 씁니다.** 같은 크기의 파일이라도 JSON은 코드보다 약 2배 많은 토큰을 소비합니다. API 응답 데이터를 많이 다루는 프로젝트라면 context가 생각보다 빨리 찹니다.


### 병렬 tool 호출의 카운팅 함정


병렬 tool 호출 시 토큰을 단순하게 계산하면 누락이 생깁니다. 같은 API 응답에서 나온 tool들은 동일한 assistant message ID를 공유하기 때문입니다.


```javascript
메시지 구조 (병렬 tool 2개 실행 시):

  asst(id=msg_001)  user(grep 결과)  asst(id=msg_001)  user(read 결과)
       ↑ usage                           ↑ 같은 ID, 같은 usage
```


"마지막 assistant 메시지부터 추정"하면 두 번째 `asst(id=msg_001)`에서 시작합니다. 그 앞의 grep 결과가 토큰 계산에서 통째로 빠집니다.


**해결: ID가 같은 첫 번째 위치까지 역추적**


```javascript
현재 위치: 두 번째 asst(id=msg_001)
역추적:
  → user(grep 결과): assistant가 아님, 계속 올라감
  → 첫 번째 asst(id=msg_001): 같은 ID, 계속 올라감
  → 이전 메시지: 다른 ID → 멈춤

결과: 첫 번째 msg_001부터 이후 전체를 카운팅
      grep 결과 + read 결과 모두 포함 ✅
```


최종 계산은 **첫 번째 msg_001의 정확한 usage (캐노니컬) + 이후 메시지들의 러프 추정** 조합입니다. 이미 아는 정확한 값과 모르는 부분의 추정을 조합해서 최대한 정확하게 맞춥니다.


### 함수 선택이 장애를 만들 수 있다


token 카운팅에 쓰이는 함수가 세 가지 있는데, 잘못 선택하면 실제 장애로 이어집니다.


| 함수                                     | 무엇을 세나         | 올바른 용도            |
| -------------------------------------- | -------------- | ----------------- |
| `tokenCountWithEstimation`             | 전체 context     | compaction 트리거 결정 |
| `tokenCountFromLastAPIResponse`        | 마지막 응답만        | 단순 응답 크기 확인       |
| `messageTokenCountFromLastAPIResponse` | output_tokens만 | 단일 응답 생성량 측정      |


`tokenCountFromLastAPIResponse`를 compaction 판단에 쓰면, context가 180K여도 "마지막 응답 5K"만 반환합니다. compaction이 영원히 발동하지 않아 결국 context가 꽉 차서 API 호출 자체가 실패합니다.


---


## 설계 철학: 안전이 최적화보다 우선


Token Budget 시스템의 핵심 원칙은 하나입니다.

> "Token budget은 최적화 메커니즘이 아니라 안전 메커니즘이다."

과대평가와 과소평가의 결과가 다릅니다.


|      | 결과                        | 심각도       |
| ---- | ------------------------- | --------- |
| 과대평가 | 조금 이른 compaction          | 사소한 성능 손실 |
| 과소평가 | context overflow → API 실패 | 완전한 장애    |


조금 이르게 compaction되는 건 감수할 수 있는 손실이지만, API 실패는 세션 자체가 망가지는 복구 불가 상황입니다. 그래서 시스템은 항상 보수적으로 설계되어 있습니다. 오차가 날 거면 과대평가 방향으로 틀립니다.


또 하나 주목할 점은 **prompt cache가 모든 복잡성의 근원**이라는 것입니다. Tri-state 시스템, 상태 고정, 바이트 단위 재적용 — 이 모든 복잡성은 "cache prefix를 안정적으로 유지해야 한다"는 단 하나의 제약에서 비롯됩니다. 캐싱이라는 성능 최적화가 예산 집행 시스템의 구조 자체를 제약하는 방식으로 역설계된 것입니다.


---


## 실용 가이드


**grep에 플래그를 쓰세요**


파일 목록만 필요하면 `-l` 플래그로 결과 크기를 줄일 수 있습니다. 50K를 넘지 않으면 디스크 저장 없이 전체 결과를 볼 수 있습니다.


```bash
grep -l "pattern" .  # 파일 경로만 반환 (작음)
grep -r "pattern" .  # 전체 매칭 라인 (클 수 있음)
```


**병렬 검색은 분산하세요**


동시에 실행되는 tool 결과의 합산이 200K를 향해 누적됩니다. 키워드 10개를 동시에 검색하기보다 라운드별로 나눠서 실행하면 Tri-state 상태 고정이 누적되는 속도를 늦출 수 있습니다.


**JSON은 코드보다 토큰을 2배 씁니다**


같은 100KB 파일이라도 JSON은 코드의 2배 토큰을 소비합니다. API 응답 데이터를 많이 다루는 프로젝트는 context가 더 빨리 찬다는 걸 감안하고 compaction 타이밍을 앞당기는 게 좋습니다.


**Read tool은 크기에 관계없이 보존됩니다**


Read tool의 결과는 Infinity 예외로 보호되어 50K를 넘어도 디스크로 가지 않습니다. 모델에게 파일 전체를 보여줘야 한다면 cat 대신 Read tool을 명시적으로 요청하는 게 낫습니다.


**"Output too large"가 보였다면**


결과가 디스크에 있다는 뜻입니다. 파일 경로가 context에 포함되어 있으니 Read tool로 전체를 읽을 수 있습니다. Claude에게 "전체 결과를 읽어줘"라고 하면 됩니다.


---


## 직접 겪은 사례 (switch-job-quest 프로젝트)


### 사례 1: Glob 97개 → 선택적 Read 강제


성장 기록 화면 가독성 개선 작업에서 fe-feature-builder가 `**/*.tsx` Glob으로 97개 파일 목록을 뽑은 뒤 관련 컴포넌트 전체를 Read했습니다. 8개 컴포넌트 파일을 병렬로 묶어 두 라운드에 나눠 읽었는데, 각 파일이 100~200줄이라 tool result 누적만 약 12K tokens입니다. 여기에 이전 대화 맥락이 쌓여 있으면 context 압박이 시작됩니다.


대응책: 에이전트 파일에 "Glob 후 관련 파일만 선택적 Read, 병렬 Read 4개 이하" 규칙을 명시했습니다. 에이전트는 이제 Glob 결과를 훑고 수정 대상 컴포넌트만 골라 읽습니다.


### 사례 2: Bash 출력 전체 캡처로 context 낭비


`./gradlew :core:core-api:test` 실행 결과를 그대로 출력하면 Spring Boot 배너 + 전체 테스트 로그로 2~3K tokens이 날아갑니다. 테스트 결과 판단에 필요한 건 마지막 20줄뿐입니다.


대응책: 에이전트 파일 TDD 섹션에 `2>&1 | tail -20` 패턴을 직접 코드 예시로 박아뒀습니다. "어떻게 쓰라"가 아니라 "이 명령어 형태로 써라" 수준으로 구체화해야 실제로 지켜집니다.


```bash
./gradlew :core:core-api:test 2>&1 | tail -20
```


### 사례 3: auto-compaction 이후 아키텍처 규칙 소실


컨텍스트가 83.5%(167K/200K)에 도달하면 auto-compaction이 트리거됩니다. 문제는 압축 후 살아남는 내용이 '최근 대화'에 집중되다 보니, 세션 초반에 합의한 "core-domain에 Spring 어노테이션 금지", "default export 금지" 같은 아키텍처 규칙이 증발한다는 것입니다.


대응책: [CLAUDE.md](http://claude.md/)에 `## Compact Instructions` 섹션을 만들고, 이 섹션이 auto-compaction 시 자동으로 새 컨텍스트에 주입되도록 했습니다. 구조 규칙과 "다음 작업" 상태를 이 섹션 안에 모아두면 compaction 이후에도 에이전트가 동일한 아키텍처 규칙 아래서 작동합니다.


### 사례 4: JSON 컬럼이 토큰을 2배로 먹는다


`quest_history` 테이블의 `ai_evaluation_json` 컬럼에는 AI 평가 전체 JSON이 저장됩니다. QA 리뷰어가 이 데이터를 Grep으로 탐색하거나, 에이전트가 DB 스키마를 Read할 때 JSON 구조 자체가 context에 들어오면 일반 텍스트 대비 약 2배의 token을 소비합니다. (일반 텍스트 ~4 bytes/token vs JSON ~2 bytes/token)


대응책: qa-reviewer 에이전트 파일에 "전달받은 변경 파일 + 직접 연관 파일만" 탐색하도록 범위를 명시했습니다. DB 스키마 전체를 Read하는 대신 오케스트레이터가 변경 파일 목록을 명시적으로 전달하는 구조로 고정했습니다.


---


에이전트에게 "token을 아껴라"고 말하는 것만으로는 부족합니다. 에이전트 정의 파일에 구체적인 사용 패턴을 박아야 auto-compaction 이후에도 동작이 유지됩니다. 규칙은 대화에서 합의하는 게 아니라 파일에 써야 살아남습니다.


---


## 정리


| 방어선           | 기준      | 동작                  |
| ------------- | ------- | ------------------- |
| Layer 1 (개별)  | 50K 초과  | 디스크 저장 + 2K preview |
| Layer 2 (집계)  | 200K 초과 | 큰 것부터 선택적 디스크 저장    |
| Layer 3 (카운팅) | —       | 캐노니컬 + 러프 이중 계산     |


Token Budget은 Auto Compaction이 발동하기 전에 조용히 context를 관리합니다. "Output too large"나 파일로 저장됐다는 메시지가 보여도 당황하지 마세요. Read tool로 접근할 수 있고, [CLAUDE.md](http://claude.md/)는 건드리지 않습니다.


이 시스템을 이해하고 나면 grep 플래그 하나, 검색 순서 하나가 세션 안정성에 어떤 영향을 주는지 감이 옵니다.


---


_참고: Harness Engineering: From Claude Code Internals to AI Coding Best Practices, Chapter 12 — Token Budgeting_

