const fs = require('fs');
const matter = require('gray-matter');

// Markdown 변환 결과 예시
let raw = fs.readFileSync('src/posts/my-post.md', 'utf8');

// frontmatter 영역 추출
const matched = raw.match(/<!--frontmatter-->([\s\S]*?)<!--end-->/);

if (matched) {
  const yamlBlock = matched[1].trim();
  const content = raw.replace(matched[0], '').trim();

  const final = matter.stringify(content, matter.load(yamlBlock).data);

  fs.writeFileSync('src/posts/my-post.md', final);
}
