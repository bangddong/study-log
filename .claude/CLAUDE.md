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
| Series | select | 강의 시리즈명 (없으면 빈값) |
| Status | status | 시작 전 / 진행 중 / 완료 |
| Deployed | checkbox | 배포 완료 시 자동 체크 (스케줄러) |

### Slug 규칙
Slug가 `contents/posts/` 하위 경로를 결정한다.

```
Slug: study/ai-agent-harness
→ contents/posts/study/ai-agent-harness.md
→ URL: /posts/study/ai-agent-harness/

Slug: spring/jpa/jpa-basic
→ contents/posts/spring/jpa/jpa-basic.md
→ URL: /posts/spring/jpa/jpa-basic/
```

**Slug에 카테고리 경로를 반드시 포함해야 한다.** 빈 Slug는 타이틀을 소문자+하이픈으로 변환해 flat 경로가 된다.

## 새 글 게시 방법

1. Notion Study Log DB에 페이지 생성
2. 위 스키마에 맞게 properties 설정 (Slug 필수)
3. 본문 작성
4. study-log 레포에 아무 변경사항이나 push → CI 자동 실행

변경사항 없이 배포만 트리거하려면:
```bash
git commit --allow-empty -m "chore: trigger deploy" && git push origin main
```

## CI/CD

**파일**: `.github/workflows/ci.yml`

**파이프라인**:
1. `yarn install --frozen-lockfile`
2. `node convert-notion.mjs` — Notion DB → 마크다운 (GitHub secrets 사용)
3. `yarn clean && yarn build`
4. GitHub Pages 배포

**GitHub Secrets** (github-pages environment):
- `NOTION_TOKEN`: Notion integration 토큰
- `DATABASE_ID`: `55818ff384e146fd91737134c3de6233`

**Notion 인테그레이션**: "study-log github action"이 Study Log DB에 연결되어 있어야 한다. 연결 해제 시 CI에서 `object_not_found` 에러 발생.

## convert-notion.mjs

Notion DB 전체를 조회해 각 페이지를 마크다운으로 변환 후 저장.

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
