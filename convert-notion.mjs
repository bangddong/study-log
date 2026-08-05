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

    // 본문이 빈 페이지는 쓰지 않는다.
    // 프론트매터만 있는 파일을 쓰면 기존 {slug}/index.md 와 슬러그가 겹쳐
    // MarkdownRemark 노드가 2개 생기고, 목록 렌더링의 React key가 충돌한다.
    // 배포완료로 마킹도 하지 않아 다음 실행에서 다시 잡히게 둔다.
    if (markdownBody.trim() === '') {
      console.warn(`⚠ ${filename} skipped - Notion 본문이 비어 있음 (page ${page.id})`);
      continue;
    }

    const content = matter.stringify(markdownBody, frontMatter);
    const filepath = `${outputDir}/${filename}`;
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
