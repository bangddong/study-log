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
    filter: {
      property: '배포상태',
      select: { equals: '작성완료' },
    },
  });

  for (const page of response.results) {
    const props = page.properties;

    const title = extractText(props.Title?.title) || '제목 없음';
    const date = props.Date?.date?.start || page.created_time;
    const tags = props.Tags?.multi_select?.map(t => t.name) || [];
    const series = props.Series?.select?.name || null;
    const emoji = extractText(props.Emoji?.rich_text) || page.icon?.emoji || '';
    const slug = extractText(props.Slug?.rich_text);

    const mdblocks = await n2m.pageToMarkdown(page.id);
    const mdString = n2m.toMarkdownString(mdblocks);

    const frontMatter = { title, date, tags, series, emoji };
    const markdownBody = typeof mdString === 'string' ? mdString : (mdString.parent ?? '');
    const filename = (slug || title.replace(/\s+/g, '-').toLowerCase()) + '.md';

    const filepath = `${outputDir}/${filename}`;

    // --- 배포 사고 방지 가드 ---
    // 아래 두 경우는 파일을 쓰지 않고 배포완료 마킹도 건너뛴다.
    // 마킹을 건너뛰어야 다음 실행에서 다시 잡히고, 로그로 계속 보인다.

    // 1) 본문이 빈 페이지.
    //    프론트매터만 있는 파일이 만들어진다.
    if (markdownBody.trim() === '') {
      console.warn(`⚠ ${filename} skipped - Notion 본문이 비어 있음 (page ${page.id})`);
      continue;
    }

    // 2) 같은 슬러그의 {slug}/index.md 가 이미 있는 경우.
    //    Gatsby는 a/b.md 와 a/b/index.md 를 같은 URL로 해석한다. 둘 다 두면
    //    노드가 2개 생겨 목록 렌더링의 React key가 충돌한다.
    //    index.md 쪽은 이미지를 로컬 파일로 갖고 있는 경우가 많아 원본으로 취급하고,
    //    덮어쓰지 않는다. Notion 이미지는 5분 만료 presigned URL이라 옮기면 깨진다.
    const indexVariant = `${outputDir}/${filename.replace(/\.md$/, '/index.md')}`;
    if (fs.existsSync(indexVariant)) {
      console.warn(
        `⚠ ${filename} skipped - ${indexVariant} 가 이미 있음 (page ${page.id})\n` +
        `  이 글은 git이 원본이다. 고치려면 ${indexVariant} 를 직접 수정할 것.`
      );
      continue;
    }

    const content = matter.stringify(markdownBody, frontMatter);
    fs.mkdirSync(filepath.substring(0, filepath.lastIndexOf('/')), { recursive: true });
    fs.writeFileSync(filepath, content);
    console.log(`✔ ${filename} written`);

    await notion.pages.update({
      page_id: page.id,
      properties: {
        Deployed: { checkbox: true },
        '배포상태': { select: { name: '배포완료' } },
      },
    });
    console.log(`✔ ${filename} → 배포완료`);
  }
}

run();
