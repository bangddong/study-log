# study-log 프로젝트 가이드

## 개요
Gatsby 기반 기술 블로그. Notion Study Log DB를 소스로 사용하며, main 브랜치에 push하면 CI가 Notion에서 마크다운을 생성하고 GitHub Pages에 자동 배포된다.

배포 URL: https://dhbang.co.kr

## 아키텍처

```
Notion Study Log DB
        ↓ (node convert-notion.mjs)
contents/posts/{slug}.md
        ↓ (gatsby build)
public/
        ↓ (gh-pages)
https://dhbang.co.kr
```

## Notion Study Log DB

- **DB ID**: `55818ff3-84e1-46fd-9173-7134c3de6233`
- **Data Source**: `collection://cfc0dc32-0c20-4846-aefe-3ced8939b68d`
- **위치**: 노션 > 인프런 > Study Log

### 스키마

| 필드 | 타입 | 설명 |
|------|------|------|
| Title | title | 글 제목 |
| Emoji | text | 대표 이모지 (예: 🧰) |
| Date | date | 최초 작성일 |
| Last Updated | date | 마지막 수정일 |
| Slug | text | **파일 경로** — 카테고리 포함 필수 (예: `study/ai-agent-harness`) |
| Tags | multi_select | AI, Claude Code, Spring, JPA, Querydsl, Transaction |
| Series | select | 연재 시리즈명. **연속된 글에만 설정**한다. 단독 글이면 반드시 비워둔다 — 비워두면 시리즈 위젯이 렌더링되지 않고 Tags로만 구분된다. |
| 배포상태 | select | 작성중 / 작성완료 / 배포완료 |
| Deployed | checkbox | CI가 작성완료 처리 후 자동 체크 (배포상태도 배포완료로 변경) |

### Slug 규칙
Slug가 `contents/posts/` 하위 경로를 결정한다.

```
Slug: study/ai-agent-harness
→ contents/posts/study/ai-agent-harness.md
→ URL: /posts/study/ai-agent-harness/

Slug: spring/jpa/jpa-basic
→ contents/posts/spring/jpa/jpa-basic.md
→ URL: /posts/spring/jpa/jpa-basic/

Slug: trouble/post-name
→ contents/posts/trouble/post-name.md
→ URL: /posts/trouble/post-name/
```

**섹션 분류 가이드**:
- `spring/jpa/`, `spring/transaction/` — Spring 강의 정리
- `study/` — AI, Harness Engineering 등 자율 학습
- `trouble/` — 삽질 경험, 디버깅 기록, 실수 모음

**Slug에 카테고리 경로를 반드시 포함해야 한다.** 빈 Slug는 타이틀을 소문자+하이픈으로 변환해 flat 경로가 된다.

## 새 글 게시 방법 (AI 작업 시 필독)

### 1단계 — Notion 페이지 생성

`notion-create-pages` 호출 시 아래 properties를 한 번에 모두 지정한다.

```json
{
  "Title": "글 제목",
  "Emoji": "🗄️",
  "Slug": "study/example-slug",
  "배포상태": "작성완료",
  "date:Date:start": "2026-04-27",
  "date:Date:is_datetime": 0,
  "date:Last Updated:start": "2026-04-27",
  "date:Last Updated:is_datetime": 0
}
```

**Series는 연속된 글에만 설정한다.** 단독 글(삽질기, 개념 정리 등)은 Series를 비워두면 시리즈 위젯 없이 Tags로만 구분된다. Slug가 같은 `spring/` 하위여도 연재가 아니면 Series를 설정하지 않는다.

**Tags는 페이지 생성 시 포함할 수 없다.** multi_select는 create API에서 실패한다.
Tags는 반드시 생성 직후 `notion-update-page`로 별도 설정한다.

```json
{ "Tags": "[\"AI\",\"Claude Code\"]" }
```

Tags 허용값: `Spring`, `JPA`, `Querydsl`, `Transaction`, `AI`, `Claude Code`, `Troubleshooting`

---

### 2단계 — 사용자 검토 (push 전 필수)

Notion 페이지 작성 완료 후 **반드시 멈추고** 사용자에게 아래 정보를 보여준다.

- Notion 페이지 URL
- 글 제목 / Slug / Tags / Series
- 배포 예정 URL (`https://dhbang.co.kr/posts/{slug}/`)

**사용자가 명시적으로 승인하기 전까지 push하지 않는다.**

---

### 3단계 — CI 트리거

사용자 승인 후 main에 push한다. 변경사항이 없으면 빈 커밋을 사용한다.

```bash
git pull origin main
git commit --allow-empty -m "chore: trigger deploy"
git push origin main
```

`git pull` 없이 push하면 rejected된다. pull을 먼저 실행할 것.

## CI/CD

**파일**: `.github/workflows/ci.yml`

**파이프라인**:
1. `yarn install --frozen-lockfile`
2. `node convert-notion.mjs` — `작성완료` 페이지만 조회 → 마크다운 생성 → Notion 상태를 `배포완료`로 업데이트
3. 생성된 `contents/posts/` 를 git commit & push (`[skip ci]` 태그로 재귀 트리거 방지)
4. `yarn clean && yarn build`
5. GitHub Pages 배포

**설계 원칙**: 마크다운 파일을 git에 커밋해 보존한다. 이미 배포된 글은 git에 남아 있으므로 매 빌드마다 Notion을 재조회하지 않아도 된다. 신규 글(`작성완료`)만 Notion에서 가져온다.

**GitHub Secrets** (github-pages environment):
- `NOTION_TOKEN`: Notion integration 토큰
- `DATABASE_ID`: `55818ff384e146fd91737134c3de6233`

**Notion 인테그레이션**: "study-log github action"이 Study Log DB에 연결되어 있어야 한다. 연결 해제 시 CI에서 `object_not_found` 에러 발생.

## convert-notion.mjs

`배포상태 = 작성완료`인 페이지만 조회해 마크다운으로 변환 후 저장. 처리 완료 후 Notion 상태를 `배포완료`로 업데이트한다. 이미 `배포완료`인 글은 git에 파일이 존재하므로 재조회하지 않는다.

- 입력: `process.env.NOTION_TOKEN`, `process.env.DATABASE_ID`
- 출력: `contents/posts/{slug}.md` (하위 디렉토리 자동 생성)
- 프론트매터: `title`, `date`, `tags`, `series`, `emoji`

### 의존성 버전 (변경 주의)
```json
"@notionhq/client": "2.2.15"   // v3+ API 호환 안됨
"notion-to-md": "3.1.9"        // toMarkdownString()이 { parent, children } 객체 반환
"dotenv": "16.x"               // v17은 API 변경
```

## 신규 태그 추가 방법
DB 스키마에 없는 태그는 페이지 생성 시 에러 발생. Notion MCP로 추가:

```
notion-update-data-source (data_source_id: cfc0dc32-0c20-4846-aefe-3ced8939b68d)
statements: ALTER COLUMN "Tags" SET MULTI_SELECT('기존태그1':blue, ..., '신규태그':color)
```

## 로컬 개발

```bash
yarn develop      # 개발 서버 (localhost:8000)
yarn build        # 프로덕션 빌드
yarn clean        # 캐시 제거
```

로컬에서 convert-notion.mjs 실행:
```bash
# .env 파일 생성 후 실행
echo "NOTION_TOKEN=xxx\nDATABASE_ID=55818ff384e146fd91737134c3de6233" > .env
node convert-notion.mjs
```
