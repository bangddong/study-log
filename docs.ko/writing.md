# 블로그 포스트 작성법

이 스타터는 Gatsby의 파일 기반 라우팅을 활용하여, `contents/posts/` 폴더에 Markdown 파일을 추가하면 자동으로 포스트가 생성됩니다.

## 📁 기본 구조

주제와 서브카테고리 단위로 포스트를 정리하는 2뎁스 디렉터리 구조를 권장합니다.

```
contents/
  posts/
    <주제>/              ← 1뎁스  (예: spring)
      <서브카테고리>/     ← 2뎁스  (예: jpa)
        <글제목>/         ← 3뎁스  (예: jpa-what-is-jpa)
          index.md
```

**예시:**

```
contents/
  posts/
    spring/
      jpa/
        jpa-what-is-jpa/
          index.md
      transaction/
        transaction-propagation-basic/
          index.md
```

각 포스트의 URL은 파일 경로에서 자동으로 생성됩니다 (예: `/posts/spring/jpa/jpa-what-is-jpa/`).

## 📝 Frontmatter

```md
---
emoji: "🚀"
title: "어떻게 시작할까요?"
date: 2025-01-18 13:55:00
update: 2025-01-18 13:55:00
tags:
  - rundevelrun
  - howto
series: "Gatsby 블로그 시작하기"
---
```

## ✍️ 콘텐츠 작성

Markdown 문법을 사용하여 본문을 작성하세요. 코드 블록, 이미지, 표 등도 모두 지원합니다.

예시:

````md
## 서론

이 블로그는 Gatsby와 Markdown을 기반으로 만들어졌습니다.

```js
console.log("Hello Gatsby!");
```
````