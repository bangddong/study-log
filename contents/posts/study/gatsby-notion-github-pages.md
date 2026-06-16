---
title: Gatsby + Notion으로 GitHub Pages 배포 자동화하기
date: '2026-04-23'
tags:
  - AI
  - Claude Code
series: Blog 개발기
emoji: "\U0001F6E0️"
---

이 블로그는 Gatsby 기반에 Notion DB를 콘텐츠 소스로 씁니다. 원래는 마크다운 파일을 직접 커밋했는데, Notion에 글을 쓰고 push 한 번만 하면 자동 배포되는 구조를 만들고 싶었습니다. 그 과정에서 꽤 막혔습니다. 이 글은 그 과정에서 겪은 삽질들을 기록한 글입니다.


---


## 목표 아키텍처


최종적으로 만들고자 한 흐름은 이렇습니다.


```javascript
노션에 글 작성
    ↓
main 브랜치에 push
    ↓
GitHub Actions: Notion DB → 마크다운 변환
    ↓
Gatsby 빌드
    ↓
GitHub Pages 배포
```


글을 쓰고 push 한 번만 하면 끝나는 구조입니다.


---


## Notion DB 설계


먼저 노션에 Study Log 데이터베이스를 만들었습니다. Gatsby 블로그의 프론트매터와 1:1로 대응되도록 스키마를 설계했습니다.


| 필드       | 타입           | 역할                         |
| -------- | ------------ | -------------------------- |
| Title    | title        | 글 제목                       |
| Emoji    | text         | 대표 이모지                     |
| Date     | date         | 작성일                        |
| Slug     | text         | 파일 경로 (예: `study/my-post`) |
| Tags     | multi_select | 태그 목록                      |
| Series   | select       | 시리즈명                       |
| Deployed | checkbox     | 배포 완료 여부                   |


여기서 **Slug가 핵심**입니다. `study/my-post`로 설정하면 `contents/posts/study/my-post.md`로 생성되고, URL은 `/posts/study/my-post/`가 됩니다. 카테고리 경로를 Slug에 포함하지 않으면 flat하게 루트에 생성됩니다.


---


## convert-notion.mjs 작성


Notion DB를 조회해 마크다운으로 변환하는 스크립트입니다.


```javascript
import { Client } from '@notionhq/client';
import { NotionToMarkdown } from 'notion-to-md';
import fs from 'fs';
import matter from 'gray-matter';
import dotenv from 'dotenv';

dotenv.config();

const notion = new Client({ auth: process.env.NOTION_TOKEN });
const n2m = new NotionToMarkdown({ notionClient: notion });
const outputDir = './contents/posts';

function extractText(richText) {
  return richText?.map(t => t.plain_text).join('') || '';
}

async function run() {
  const response = await notion.databases.query({
    database_id: process.env.DATABASE_ID,
  });

  for (const page of response.results) {
    const props = page.properties;

    const title = extractText(props.Title?.title) || '제목 없음';
    const date = props.Date?.date?.start || page.created_time;
    const tags = props.Tags?.multi_select?.map(t => t.name) || [];
    const series = props.Series?.select?.name || '';
    const emoji = extractText(props.Emoji?.rich_text) || page.icon?.emoji || '';
    const slug = extractText(props.Slug?.rich_text);

    const mdblocks = await n2m.pageToMarkdown(page.id);
    const mdString = n2m.toMarkdownString(mdblocks);

    const frontMatter = { title, date, tags, series, emoji };
    const markdownBody = typeof mdString === 'string' ? mdString : (mdString.parent ?? '');
    const content = matter.stringify(markdownBody, frontMatter);
    const filename = (slug || title.replace(/\s+/g, '-').toLowerCase()) + '.md';

    const filepath = `${outputDir}/${filename}`;
    fs.mkdirSync(filepath.substring(0, filepath.lastIndexOf('/')), { recursive: true });
    fs.writeFileSync(filepath, content);
    console.log(`✔ ${filename} written`);
  }
}

run();
```


포인트는 두 가지입니다.


**Notion API 응답에서** **`page.properties`****를 직접 파싱한다.** 예전 `notion-to-md`에는 `n2m.metaData()` 메서드가 있었지만 v3에서 제거됐습니다. `notion.databases.query()`가 반환하는 `page.properties`에서 직접 꺼내는 방식으로 바꿨습니다.


**하위 디렉토리를 자동 생성한다.** Slug가 `study/my-post`처럼 경로를 포함할 수 있으므로, `fs.mkdirSync(..., { recursive: true })`로 중간 디렉토리를 미리 만들어줍니다.


---


## GitHub Actions 설정


CI 워크플로우에 Notion 변환 단계를 추가했습니다.


```yaml
- name: Convert Notion to Markdown
  env:
    NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
    DATABASE_ID: ${{ secrets.DATABASE_ID }}
  run: node convert-notion.mjs
```


`NOTION_TOKEN`과 `DATABASE_ID`는 GitHub의 `github-pages` Environment Secrets에 저장합니다. 전체 파이프라인은 이렇습니다.


```javascript
yarn install
    ↓
node convert-notion.mjs   ← Notion DB 전체를 마크다운으로 변환
    ↓
yarn clean && yarn build  ← Gatsby 빌드
    ↓
GitHub Pages 배포
```


---


## 겪었던 문제들


### 1. ES Module 오류


```javascript
SyntaxError: Cannot use import statement outside a module
```


`import` 구문을 쓰는데 `package.json`에 `"type": "module"`이 없어서 발생했습니다. Gatsby 프로젝트에 `"type": "module"`을 추가하면 다른 설정이 깨질 수 있어서, 파일 확장자를 `.js`에서 `.mjs`로 바꾸는 것으로 해결했습니다.


### 2. @notionhq/client 버전 문제


```javascript
TypeError: notion.databases.query is not a function
```


`yarn add @notionhq/client`를 실행하면 최신 버전(v5+)이 설치되는데, 이 버전은 API 구조가 바뀌어서 기존 코드와 호환되지 않습니다. v2 API 기준으로 작성된 코드라면 버전을 고정해야 합니다.


```bash
yarn add @notionhq/client@2.2.15
```


`dotenv`도 v17에서 동작 방식이 달라지므로 v16으로 고정했습니다.


```bash
yarn add dotenv@16
```


### 3. notion-to-md v3 API 변경


```javascript
TypeError: n2m.metaData is not a function
```


`notion-to-md` v3에서 `metaData()` 메서드가 제거됐습니다. 페이지 메타데이터는 `notion.databases.query()`가 반환하는 `page.properties`에서 직접 읽도록 변경했습니다.


또한 `toMarkdownString()`의 반환 타입도 바뀌었습니다. v2에서는 문자열을 반환했지만 v3에서는 `{ parent: string, children: object }` 형태의 객체를 반환합니다. `gray-matter`에 넘기기 전에 타입을 체크하고 `.parent`를 꺼내야 합니다.


```javascript
const markdownBody = typeof mdString === 'string' ? mdString : (mdString.parent ?? '');
```


### 4. Notion 인테그레이션 연결 누락


```javascript
Could not find database with ID: xxx. Make sure the relevant pages and databases
are shared with your integration.
```


Notion API를 쓰려면 인테그레이션이 해당 DB에 명시적으로 연결되어 있어야 합니다. DB 페이지에서 `···` → **Connections** → 인테그레이션 추가로 해결했습니다. 이 설정은 DB를 새로 만들거나 인테그레이션을 새로 만들 때마다 해줘야 합니다.


### 5. DATABASE_ID 시크릿 오류


GitHub Secrets에 저장된 `DATABASE_ID`가 엉뚱한 페이지 ID를 가리키고 있었습니다. Notion에서 DB를 여러 개 운영하다 보면 흔히 생기는 실수입니다. Notion MCP나 API로 DB ID를 다시 확인하고 시크릿을 업데이트해서 해결했습니다.


---


## 의존성 버전 정리


겪은 문제들을 바탕으로 검증된 버전 조합입니다.


```json
"@notionhq/client": "2.2.15",
"notion-to-md": "3.1.9",
"dotenv": "^16.0.0",
"gray-matter": "^4.0.3"
```


---


## 완성된 워크플로우


이제 새 글을 게시하는 절차는 이렇습니다.

1. 노션 Study Log DB에 페이지 생성
2. Title, Emoji, Date, Slug, Tags 입력 (Slug 형식: `카테고리/파일명`)
3. 본문 작성
4. `main` 브랜치에 push (내용 변경이 없으면 empty commit)

```bash
git commit --allow-empty -m "chore: trigger deploy"
git push origin main
```


이후 GitHub Actions가 자동으로 Notion DB 전체를 마크다운으로 변환하고 빌드 후 배포합니다.


---


## 마치며


자동화를 완성하고 나니 노션에서 글을 쓰는 것과 블로그에 올리는 것 사이의 마찰이 거의 없어졌습니다. 몇 가지 버전 함정만 조심하면 생각보다 간단하게 구성할 수 있습니다.


전체 코드는 [study-log](https://github.com/bangddong/study-log) 레포에서 확인하실 수 있습니다.


---


## 다음 편


이 구조를 처음부터 직접 구축하는 과정은 다음 글에서 다룹니다.


**➜ Gatsby + Notion으로 GitHub Pages 블로그 직접 구축하기** _(게시 예정)_

