import React from "react"
import SEO from "components/SEO"
import { graphql } from "gatsby"

import Layout from "components/Layout"
import Article from "components/Article"

import { siteUrl } from "../../blog-config"

const Post = ({ data }) => {
  const post = data.markdownRemark
  const { previous, next, seriesList } = data

  const { title, date, update, tags, series, emoji, isoDate, isoUpdate } =
    post.frontmatter
  const { readingTime, slug, description } = post.fields

  let filteredSeries = []
  if (series !== null) {
    filteredSeries = seriesList.edges.map(seriesPost => {
      if (seriesPost.node.id === post.id) {
        return {
          ...seriesPost.node,
          currentPost: true,
        }
      } else {
        return {
          ...seriesPost.node,
          currentPost: false,
        }
      }
    })
  }

  return (
    <Layout>
      <SEO
        title={title}
        description={description}
        url={`${siteUrl}${slug}`}
        article={{
          datePublished: isoDate,
          dateModified: isoUpdate,
          tags,
          series,
        }}
      />
      <Article>
        <Article.Header
          emoji={emoji}
          title={title}
          date={date}
          update={update}
          tags={tags}
          minToRead={Math.round(readingTime.minutes)}
        />
        {filteredSeries.length > 0 && (
          <Article.Series header={series} series={filteredSeries} />
        )}
        <Article.Body html={post.html} />
        <Article.Footer previous={previous} next={next} />
      </Article>
    </Layout>
  )
}

export default Post

export const pageQuery = graphql`
  query BlogPostBySlug(
    $id: String!
    $series: String
    $previousPostId: String
    $nextPostId: String
  ) {
    site {
      siteMetadata {
        title
      }
    }
    markdownRemark(id: { eq: $id }) {
      id
      html
      frontmatter {
        title
        date(formatString: "MMMM DD, YYYY")
        update(formatString: "MMMM DD, YYYY")
        isoDate: date(formatString: "YYYY-MM-DD")
        isoUpdate: update(formatString: "YYYY-MM-DD")
        tags
        series
        emoji
      }
      fields {
        slug
        description
        readingTime {
          minutes
        }
      }
    }
    seriesList: allMarkdownRemark(
      sort: [{ frontmatter: { date: ASC } }, { fields: { slug: ASC } }]
      filter: { frontmatter: { series: { eq: $series } } }
    ) {
      edges {
        node {
          id
          fields {
            slug
          }
          frontmatter {
            title
            emoji
          }
        }
      }
    }
    previous: markdownRemark(id: { eq: $previousPostId }) {
      fields {
        slug
      }
      frontmatter {
        title
      }
    }
    next: markdownRemark(id: { eq: $nextPostId }) {
      fields {
        slug
      }
      frontmatter {
        title
        emoji
      }
    }
  }
`
