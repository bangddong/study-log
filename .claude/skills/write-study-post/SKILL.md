---
name: write-study-post
description: study-log 블로그 글을 study-log 양식으로 작성하고 Notion→CI로 발행한다. 새 글/초안 작성, 시리즈(연재) 편 작성, 기존 초안 다듬기, Notion 등록·배포 요청 시 사용.
---

# study-log 글 작성·발행 스킬

study-log(Gatsby + Notion 블로그, https://dhbang.co.kr)의 글을 **일관된 양식**으로 쓰고 발행하기 위한 절차. 이 파일은 오케스트레이션만 담고, 세부는 아래 두 문서를 **반드시 먼저 읽어** 따른다.

- `study-log/.claude/writing-style.md` — 문체·구조 원칙 (필수)
- `study-log/.claude/CLAUDE.md` — Notion 스키마, 발행 워크플로, Slug 규칙

---

## 1. 원고·소스 확보

- 사용자가 원고/PDF/링크를 준다 → 그 내용을 **재구성**한다(번역·복붙 금지, 저작권 유의: 직접 인용 최소화).
- 소스가 없으면 주제만 받아 초안을 쓴다.
- 시리즈 편이면 앞 편들과의 연결(Series, 이전 개념 재호출)을 확인한다.

## 2. 구조 — 일반 글

writing-style.md의 구조를 따른다. 뼈대:

```
> 출처/시리즈 attribution (한 줄)
## 도입        — 독자가 겪는 구체적 장면·현상 (의문형은 "~한 적이 있으신가요")
## 개념/메커니즘 — 소제목마다 핵심 한 줄, 항상 "왜?"에 답, 코드·구조는 인용(요약 금지)
## 정리        — 표(2열+) + 한 줄 결론
## 참고        — 출처·링크
```

**직접 겪은 사례 섹션은 넣지 않는다** (2026-07 결정). 정리형 글은 원문 해부에 집중하고, 개인 경험은 trouble/ 삽질기로 분리한다.

- 대섹션은 `---`로 구분, 표·인용구·코드펜스(언어 명시) 적극 사용.
- 경어체 `합니다/입니다`. 현상→원인 구조("버그처럼 보이지만 설계 의도다").

## 3. 시리즈(연재) 템플릿

연재 글은 위 구조 대신 **4단계 스파인**을 쓴다(각 편 일관성 유지):

```
> [저자·책/출처] · 시리즈 주제 (attribution 한 줄)
## 도입
## 핵심 개념 (무엇을·왜)
## 메커니즘·구조 (어떻게)
## (정리 + 한 줄 결론)
## 참고
```

- **Series 필드**를 시리즈명으로 설정 → `/series/<이름>` 페이지 + 편 간 prev/next 자동 생성.
- **Slug 중첩**: `study/<시리즈-슬러그>/<토픽>` (예: `study/agentic-design-patterns/prompt-chaining`).
  - 시리즈 랜딩/서문은 `study/<시리즈-슬러그>/intro`.
  - 파일과 하위 폴더는 이름이 달라 공존 OK, URL도 별개 → 충돌 없음.

## 4. Notion 등록

`notion-create-pages`, parent = Study Log data source (`cfc0dc32-0c20-4846-aefe-3ced8939b68d`).

```json
{
  "Title": "...", "Emoji": "🧩",
  "Slug": "study/...", "Series": "시리즈명(단독글이면 생략)",
  "배포상태": "작성중",
  "date:Date:start": "YYYY-MM-DD", "date:Date:is_datetime": 0,
  "date:Last Updated:start": "YYYY-MM-DD", "date:Last Updated:is_datetime": 0
}
```

- **Tags는 생성 시 넣지 말 것** (multi_select는 create에서 실패). 생성 직후 `notion-update-page`로:
  `{ "Tags": "[\"AI\"]" }`  (허용값: Spring/JPA/Querydsl/Transaction/AI/Claude Code/Troubleshooting)
- 본문에는 제목을 넣지 않는다(제목은 properties). attribution 인용구부터 시작.
- 시리즈 편은 date를 앞 편보다 뒤로 (prev/next가 date ASC 정렬).

## 5. 검토 게이트 (필수 — push 전 정지)

Notion 작성 완료 후 **반드시 멈추고** 사용자에게 보여준다:

- Notion 페이지 URL
- 제목 / Slug / Tags / Series
- 배포 예정 URL: `https://dhbang.co.kr/posts/{slug}/`

**사용자가 명시적으로 승인하기 전까지 배포하지 않는다.**

## 6. 배포 (승인 후)

1. Notion `배포상태` → `작성완료` (CI가 이 상태만 가져감), Last Updated 갱신.
2. study-log 레포에서:
   ```bash
   git pull origin main
   git commit --allow-empty -m "chore: trigger deploy - <글 slug>"
   git push origin main
   ```
   (`git pull` 없이 push하면 rejected)
3. CI 완료 확인: `gh run watch <id>` → success. CI가 마크다운 생성 + Notion을 `배포완료`로 자동 처리.

---

## 발행 전 체크리스트

- [ ] 도입에 공감할 구체적 장면이 있는가
- [ ] 모든 "왜?"에 답했는가
- [ ] 직접 겪은 사례 섹션을 넣지 않았는가 (정리형 글 제외 규칙)
- [ ] 코드/구조를 인용했는가(요약만 아님)
- [ ] 정리 표 + 한 줄 결론이 있는가 (단, 서문/랜딩성 글은 생략 가능)
- [ ] Slug에 카테고리 경로 포함, 시리즈면 중첩 규칙 준수
- [ ] Tags는 생성 후 별도 설정했는가
- [ ] 검토 게이트에서 사용자 승인을 받았는가
