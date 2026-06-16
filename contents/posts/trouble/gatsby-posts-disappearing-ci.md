---
title: 배포했는데 글이 사라졌다 — Gatsby + Notion CI 삽질기
date: '2026-06-16'
tags:
  - Troubleshooting
series: null
emoji: "\U0001F47B"
---

분명히 배포했는데 글이 없습니다. 🫥


GitHub Actions CI 로그에는 초록불이 떠 있고, Notion에서 상태도 `배포완료`로 바뀌어 있는데, 막상 사이트에 가보면 `study/` 카테고리 글들이 통째로 사라져 있습니다. Spring 글은 멀쩡한데 AI 시리즈 글은 흔적도 없습니다. 처음엔 Notion 연동 문제인 줄 알았고, 다음엔 Gatsby 빌드 문제인 줄 알았고, 마지막엔 GitHub Pages 문제인 줄 알았습니다.


정답은 셋 다 아니었습니다. 아주 단순한 구조적 문제였고, 이해하고 나면 "아, 당연하지" 싶은 것이었습니다.

> 이 블로그의 Gatsby + Notion 초기 구성이 궁금하다면 [Gatsby + Notion으로 GitHub Pages 배포 자동화하기](https://dhbang.co.kr/posts/study/gatsby-notion-github-pages/)를 먼저 읽어보시면 맥락이 잡힙니다.

---


## 🏗️ 구조부터 이해해야 합니다


Gatsby는 **정적 사이트 생성기(Static Site Generator)** 입니다. 빌드 시점에 존재하는 파일을 읽어서 HTML로 변환하고, 그 결과물만 배포합니다. 서버가 없습니다. 런타임에 파일을 읽는 일이 없습니다.


이 블로그의 CI 파이프라인은 이렇게 생겼습니다:


```plain text
git push → GitHub Actions 트리거
  → actions/checkout   ← git에 있는 파일만 가져옴
  → node convert-notion.mjs  ← Notion에서 마크다운 생성
  → gatsby build  ← 마크다운 → HTML
  → GitHub Pages 배포
```


여기서 **`actions/checkout`****은 git에 커밋된 파일만 가져옵니다.** Notion에서 생성한 파일은 git에 없으면 `checkout` 이후에도 없습니다. 그래서 `convert-notion.mjs`가 그 공백을 채워줘야 합니다.


---


## 🔍 왜 Spring 글은 살아있었나


`convert-notion.mjs`는 Notion DB에서 `배포상태 = 작성완료`인 페이지만 조회합니다. 처리 후엔 상태를 `배포완료`로 업데이트합니다.


```javascript
const response = await notion.databases.query({
  database_id: process.env.DATABASE_ID,
  filter: {
    property: '배포상태',
    select: { equals: '작성완료' },
  },
});
```


Spring 글들은 오래전에 `배포완료`가 됐는데, 그 마크다운 파일이 **git에 직접 커밋되어 있었습니다.** `contents/posts/spring/` 폴더가 레포에 통째로 들어있었던 거죠. 그러니 `checkout`만 해도 Spring 글은 살아있었습니다.


AI 시리즈 글은? Notion에서 처음 배포할 때 CI가 마크다운을 생성했지만, 그 파일을 **git에 커밋하지 않았습니다.** 다음 CI 실행 때 `checkout`하면 파일이 없고, Notion 상태는 이미 `배포완료`라서 `convert-notion.mjs`도 그냥 넘어갑니다. 결과: 없는 파일 = 없는 글.


```plain text
[최초 배포]
Notion 작성완료 → CI → 마크다운 생성 → gatsby build → 배포 ✅
                                ↑
                         git에 커밋 안 됨 🚨

[다음 CI 실행]
git checkout → spring/ 있음, study/ 없음
Notion 조회 → 배포완료라 스킵
gatsby build → study/ 글 없음
결과: AI 글 전부 사라짐 👻
```


---


## 🔧 해결 방법: 마크다운을 git에 커밋한다


### 🙈 첫 번째 시도: 매번 Notion을 전부 다시 읽기


처음엔 `convert-notion.mjs` 필터를 `작성완료`와 `배포완료` 둘 다 포함하도록 바꿨습니다. 이러면 매 빌드마다 Notion의 모든 글을 가져오니까 파일이 사라질 일이 없습니다.


```javascript
filter: {
  or: [
    { property: '배포상태', select: { equals: '작성완료' } },
    { property: '배포상태', select: { equals: '배포완료' } },
  ],
}
```


동작은 합니다. 근데 글이 100개, 1,000개가 되면요? 매 빌드마다 Notion API를 1,000번 찌르는 셈입니다. Notion API에는 rate limit도 있고, 빌드 시간도 글 수에 비례해서 늘어납니다. 근본적인 해결이 아니라 증상 억제였습니다. 다시 원점으로.


### ✅ 올바른 접근: 파일을 git에 보존한다


Gatsby 블로그에서 Notion을 CMS로 쓸 때 핵심 원칙은 하나입니다.

> **생성된 마크다운 파일은 반드시 git에 커밋해야 합니다.**

CI에 마크다운 커밋 step을 추가했습니다:


```yaml
- name: Commit generated markdown
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add contents/posts/
    git diff --staged --quiet || git commit -m "chore: sync posts from Notion [skip ci]"
    git pull --rebase origin main
    git push
```


`[skip ci]` 태그로 커밋 후 CI가 재귀적으로 다시 트리거되는 것을 막았습니다.


### 🙈 두 번째 삽질: git push rejected


처음 이 step을 추가할 때 `git pull --rebase` 없이 `git push`만 했습니다. 결과는 rejected였습니다.


```plain text
! [rejected]  main -> main (fetch first)
error: failed to push some refs to 'https://github.com/...'
hint: Updates were rejected because the remote contains work that you do not have locally.
```


CI가 마크다운 커밋을 만드는 동안 다른 커밋이 remote에 push되면서 remote가 앞서버린 겁니다. `git pull --rebase origin main`을 push 전에 추가해서 해결했습니다.


이제 흐름이 이렇게 바뀌었습니다:


```plain text
git push → CI 트리거
  → convert-notion.mjs (작성완료 페이지 → 마크다운 생성)
  → git commit contents/posts/ [skip ci]
  → gatsby build (git에 있는 모든 마크다운 → HTML)
  → GitHub Pages 배포
```


신규 글만 Notion에서 가져오고, 이미 배포된 글은 git에 보존됩니다. 글이 1,000개가 돼도 Notion API 호출은 신규 글 수만큼만 발생합니다.


---


## 🪤 추가 삽질: visitor counter 콘솔 에러


태그 검색 페이지에서 `ERR_NAME_NOT_RESOLVED` 에러가 발생하고 있었습니다. 처음엔 태그 필터 로직 문제인 줄 알았는데, 알고 보니 Header 컴포넌트에 박혀있던 외부 방문자 카운터가 원인이었습니다.


```javascript
import { FreeVisitorCounter } from "@rundevelrun/free-visitor-counter"
// → visitor.6developer.com 호출 → 도메인 죽어있음 💀
```


페이지 이동할 때마다 Header가 마운트되면서 죽은 API를 찌르고 있었던 겁니다. 코드 한 줄 추가한 게 아니라, 과거에 붙여둔 위젯의 외부 의존성이 서비스 종료된 케이스입니다. 과감하게 제거했습니다.


---


## 📋 정리


| 증상                           | 원인                           | 해결                 |
| ---------------------------- | ---------------------------- | ------------------ |
| 배포 후 일부 글이 사라짐               | 마크다운이 git에 없어 다음 빌드에서 누락     | CI에서 마크다운을 git에 커밋 |
| Spring 글은 멀쩡함                | 해당 파일이 git에 직접 커밋되어 있었음      | —                  |
| 태그 페이지 ERR_NAME_NOT_RESOLVED | 죽은 외부 visitor counter API 호출 | 컴포넌트 제거            |


**Gatsby + 외부 CMS 조합에서는, 빌드 시점에 필요한 파일이 git에 있어야 한다는 원칙을 항상 기억해야 합니다.** CI가 파일을 생성하더라도 git에 커밋하지 않으면 다음 빌드에서 사라집니다.

