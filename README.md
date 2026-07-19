# study-log

학습한 것을 기록하는 기술 블로그입니다. Notion에서 글을 쓰면 CI가 마크다운으로 변환해 GitHub Pages로 자동 배포합니다.

👉 **https://dhbang.co.kr**

## 아키텍처

```
Notion Study Log DB
        ↓  node convert-notion.mjs  (작성완료 글만 조회 → 마크다운 생성)
contents/posts/{slug}.md
        ↓  gatsby build
public/
        ↓  gh-pages
https://dhbang.co.kr
```

- **소스**: Notion 데이터베이스 — 글 작성·메타데이터(제목, Slug, Tags, Series) 관리
- **변환**: [`convert-notion.mjs`](convert-notion.mjs) — `배포상태 = 작성완료`인 페이지만 가져와 마크다운으로 저장하고, 처리 후 Notion 상태를 `배포완료`로 갱신
- **보존**: 생성된 마크다운은 git에 커밋 — 이미 배포된 글은 Notion을 재조회하지 않음
- **배포**: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — main push 시 변환 → 빌드 → GitHub Pages 배포

## 콘텐츠 구성

| 경로 | 내용 |
|------|------|
| `spring/` | Spring · JPA · Querydsl · Transaction 강의 정리 |
| `study/` | AI, Agentic Design Patterns, Harness Engineering 등 자율 학습 |
| `trouble/` | 삽질 경험, 디버깅 기록 |

## 로컬 개발

```bash
yarn install
yarn develop      # 개발 서버 (localhost:8000)
yarn build        # 프로덕션 빌드
```

Notion 변환을 로컬에서 실행하려면 `.env`에 `NOTION_TOKEN`, `DATABASE_ID`를 설정한 뒤:

```bash
node convert-notion.mjs
```

---

테마는 [gatsby-starter-rundevelrun](https://github.com/rundevelrun/gatsby-starter-rundevelrun)을 기반으로 합니다.
