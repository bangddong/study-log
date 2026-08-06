// contents/posts 안에서 같은 URL로 해석되는 마크다운이 둘 이상 있는지 검사한다.
//
// Gatsby의 createFilePath는 아래 둘을 같은 슬러그로 만든다.
//   contents/posts/a/b.md        -> /posts/a/b/
//   contents/posts/a/b/index.md  -> /posts/a/b/
// 이 경우 MarkdownRemark 노드가 2개 생기고, createPage가 같은 path로 두 번 호출되며,
// 목록 렌더링에서 React key가 충돌해 태그 필터링이 깨진다.
// 2026-08 실제로 38쌍이 쌓여 Spring/JPA/Transaction 태그가 동작하지 않았다.
//
// 빌드를 통과시키지 않는 것이 목적이다. 배포된 뒤에 발견하면 이미 늦다.

import fs from 'fs';
import path from 'path';

const ROOT = 'contents/posts';

const walk = dir =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });

const toSlug = file =>
  file
    .replace(/^contents\/posts\//, '/posts/')
    .replace(/\/index\.md$/, '/')
    .replace(/\.md$/, '/');

const files = walk(ROOT).filter(f => f.endsWith('.md'));

const bySlug = new Map();
for (const file of files) {
  const slug = toSlug(file);
  if (!bySlug.has(slug)) bySlug.set(slug, []);
  bySlug.get(slug).push(file);
}

const collisions = [...bySlug.entries()].filter(([, group]) => group.length > 1);

if (collisions.length > 0) {
  console.error(`\n✖ 슬러그가 겹치는 마크다운 ${collisions.length}건\n`);
  for (const [slug, group] of collisions) {
    console.error(`  ${slug}`);
    for (const file of group) {
      const bytes = fs.statSync(file).size;
      console.error(`      ${file}  (${bytes} bytes)`);
    }
  }
  console.error(
    '\n한쪽을 지워야 한다. 보통 본문이 있는 쪽을 남기고 프론트매터만 있는 쪽을 지운다.' +
      '\n이미지가 딸린 글은 {slug}/index.md 쪽이 원본이다.\n'
  );
  process.exit(1);
}

console.log(`✔ 슬러그 중복 없음 (마크다운 ${files.length}개)`);
