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
      or: [
        { property: '배포상태', select: { equals: '작성완료' } },
        { property: '배포상태', select: { equals: '배포완료' } },
      ],
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
    const content = matter.stringify(markdownBody, frontMatter);
    const filename = (slug || title.replace(/\s+/g, '-').toLowerCase()) + '.md';

    const filepath = `${outputDir}/${filename}`;
    fs.mkdirSync(filepath.substring(0, filepath.lastIndexOf('/')), { recursive: true });
    fs.writeFileSync(filepath, content);
    console.log(`✔ ${filename} written`);

    const deployStatus = props['배포상태']?.select?.name;
    if (deployStatus === '작성완료') {
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
}

run();
