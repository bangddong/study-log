const { createFilePath } = require(`gatsby-source-filesystem`)
const _ = require("lodash")

exports.createPages = async ({ graphql, actions, reporter }) => {
  const { createPage } = actions

  const postTemplate = require.resolve(`./src/templates/Post.jsx`)
  const seriesTemplate = require.resolve(`./src/templates/Series.jsx`)

  const result = await graphql(`
    {
      postsRemark: allMarkdownRemark(
        sort: [{ frontmatter: { date: ASC } }, { fields: { slug: ASC } }]
        filter: { fileAbsolutePath: { regex: "/contents/posts/" } }
        limit: 1000
      ) {
        nodes {
          id
          fields {
            slug
          }
          frontmatter {
            series
          }
        }
      }
      tagsGroup: allMarkdownRemark(limit: 2000) {
        group(field: { frontmatter: { tags: SELECT } }) {
          fieldValue
        }
      }
    }
  `)

  if (result.errors) {
    reporter.panicOnBuild(
      `There was an error loading your blog posts`,
      result.errors
    )
    return
  }

  const posts = result.data.postsRemark.nodes
  const series = _.reduce(
    posts,
    (acc, cur) => {
      const seriesName = cur.frontmatter.series
      if (seriesName && !_.includes(acc, seriesName))
        return [...acc, seriesName]
      return acc
    },
    []
  )

  if (posts.length > 0) {
    posts.forEach((post, index) => {
      const previousPostId = index === 0 ? null : posts[index - 1].id
      const nextPostId = index === posts.length - 1 ? null : posts[index + 1].id

      createPage({
        path: post.fields.slug,
        component: postTemplate,
        context: {
          id: post.id,
          series: post.frontmatter.series,
          previousPostId,
          nextPostId,
        },
      })
    })
  }

  if (series.length > 0) {
    series.forEach(singleSeries => {
      const path = `/series/${_.replace(singleSeries, /\s/g, "-")}`
      createPage({
        path,
        component: seriesTemplate,
        context: {
          series: singleSeries,
        },
      })
    })
  }
}

exports.onCreateNode = ({ node, actions, getNode }) => {
  const { createNodeField } = actions

  if (node.internal.type === `MarkdownRemark`) {
    const slug = createFilePath({ node, getNode })
    // 2뎁스 구조: /contents/posts/주제/서브카테고리/글제목/index.md → /posts/주제/서브카테고리/글제목/
    // 예시: /contents/posts/spring/jpa/jpa-what-is-jpa/index.md → /posts/spring/jpa/jpa-what-is-jpa/
    // createFilePath가 자동으로 올바른 경로 생성하므로 그대로 사용

    createNodeField({
      node,
      name: `slug`,
      value: slug,
    })

    createNodeField({
      node,
      name: `description`,
      value:
        node.frontmatter.description ||
        describe(node.rawMarkdownBody) ||
        describe(node.rawMarkdownBody, { lists: true }) ||
        node.frontmatter.title,
    })
  }
}

// 검색 결과에 쓸 요약을 본문에서 뽑는다.
// excerpt 는 맨 앞 출처 인용구("Antonio Gulli, ...를 정리합니다")부터 잘라서
// 시리즈 글마다 같은 문장으로 시작했다. 출처·구분선·제목을 건너뛰고 첫 산문 문단부터 쓴다.
const DESCRIPTION_MAX = 150
const ATTRIBUTION = /^이 글은 [^.]*(참고|정리|바탕)[^.]*\.\s*/

const AFFILIATE = /이 링크를 통해 구매하시면/

// lists: 산문 문단이 하나도 없는 글(목록·코드 위주인 강의 노트)에서만 목록 항목까지 쓴다.
function describe(markdown = "", { lists = false } = {}) {
  const skip = lists ? /^(>|#|\||!\[|<|---)/ : /^(>|#|\||!\[|<|---|[-*+] |\d+\. )/
  const blocks = markdown
    .replace(/```[\s\S]*?```/g, "\n\n")
    .split(/\n\s*\n/)
    .map(b => b.trim())
    .filter(Boolean)

  const prose = []
  for (const block of blocks) {
    if (skip.test(block)) continue
    if (AFFILIATE.test(block) || /^https?:\/\/\S+$/.test(block)) continue
    // 이탤릭으로만 된 출처 문단 (_이 글은_ [_원서_](...)...)
    if (/^[_*]이 글은/.test(block)) continue
    prose.push(block)
    if (prose.join(" ").length > DESCRIPTION_MAX * 2) break
  }

  const text = prose
    .join(" ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s*(?:[-*+]|\d+\.)\s+/gm, "")
    // 인라인 코드 안의 밑줄(cache_read_input_tokens)은 강조 표시가 아니므로 남긴다.
    // split 결과의 홀수 번째 조각이 백틱 안쪽이다.
    .split("`")
    .map((part, i) => (i % 2 ? part : part.replace(/[*_]/g, "")))
    .join("")
    .replace(/\\\$/g, "$")
    .replace(/\s+/g, " ")
    .trim()
    .replace(ATTRIBUTION, "")

  if (text.length <= DESCRIPTION_MAX) return text
  const cut = text.slice(0, DESCRIPTION_MAX)
  // 문장 끝에서 자를 수 있으면 거기서, 아니면 단어 경계에서 자르고 말줄임표를 붙인다.
  const end = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("? "))
  if (end >= DESCRIPTION_MAX * 0.5) return cut.slice(0, end + 1)
  return cut.slice(0, cut.lastIndexOf(" ")) + "…"
}

exports.createSchemaCustomization = ({ actions }) => {
  const { createTypes } = actions
  const typeDefs = `
  type MarkdownRemark implements Node {
    frontmatter: Frontmatter!
  }
  type Frontmatter {
    title: String!
    description: String
    tags: [String!]
    series: String
  }
  `
  createTypes(typeDefs)
}
