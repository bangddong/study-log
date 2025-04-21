import { Client } from '@notionhq/client';
import { NotionToMarkdown } from 'notion-to-md';
import fs from 'fs';
import matter from 'gray-matter';
import dotenv from 'dotenv';

dotenv.config();

const notion = new Client({ auth: process.env.NOTION_TOKEN });
const n2m = new NotionToMarkdown({ notionClient: notion });

const outputDir = './content/posts';

async function run() {
  const response = await notion.databases.query({
    database_id: process.env.DATABASE_ID,
  });

  for (const page of response.results) {
    const mdblocks = await n2m.pageToMarkdown(page.id);
    const mdString = n2m.toMarkdownString(mdblocks);
    const metadata = await n2m.metaData(page.id);

    const frontMatter = {
      title: metadata.title || '제목 없음',
      date: metadata.date?.start || metadata.created_time,
      tags: metadata.tags?.map(tag => tag.name) || [],
      series: metadata.series || '',
      emoji: metadata.icon?.emoji || '',
    };

    const content = matter.stringify(mdString, frontMatter);
    const filename = metadata.title.replace(/\s+/g, '-').toLowerCase() + '.md';

    fs.writeFileSync(`${outputDir}/${filename}`, content);
    console.log(`✔ ${filename} written`);
  }
}

run();
