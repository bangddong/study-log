import React from "react"
import { flow, map, groupBy, sortBy, filter, reverse } from "lodash/fp"
import styled from "styled-components"
import SEO from "components/SEO"

import { graphql } from "gatsby"

import Layout from "components/Layout"
import SeriesList from "components/SeriesList"
import VerticleSpace from "components/VerticalSpace"
import NoContent from "components/NoContent"

import { title, description, siteUrl } from "../../blog-config"

const Subtitle = styled.h3`
  display: inline-block;
  padding: 2px 0px;
  margin-top: 32px;
  margin-bottom: 8px;
  width: 100%;  
  text-align: center;
  font-size: 20px;
  font-weight: bold;
  background-color:${props => props.theme.colors.text};
  color: ${props => props.theme.colors.bodyBackground};
  letter-spacing: -1px;
`

const SeriesPage = ({ data }) => {
  const posts = data.allMarkdownRemark.nodes
  const series = flow(
    map(post => ({ ...post.frontmatter, slug: post.fields.slug })),
    groupBy("series"),
    map(series => ({
      name: series[0].series,
      posts: series,
      lastUpdated: series[0].date,
    })),
    sortBy(series => new Date(series.lastUpdated)),
    filter(series => series.name),
    reverse
  )(posts)

  return (
    <Layout>
      <SEO title={title} description={description} url={siteUrl} />

      <Subtitle> SERIES </Subtitle>

      {series.length === 0 && <NoContent name="series" />}

      <VerticleSpace size={32} />

      <SeriesList seriesList={series} />
    </Layout>
  )
}

export default SeriesPage

export const pageQuery = graphql`
  query {
    site {
      siteMetadata {
        title
      }
    }
    allMarkdownRemark(
      sort: { fields: [frontmatter___date], order: DESC }
      filter: { fileAbsolutePath: { regex: "/contents/posts/" } }
    ) {
      group(field: frontmatter___tags) {
        fieldValue
        totalCount
      }
      nodes {
        excerpt(pruneLength: 200, truncate: true)
        fields {
          slug
        }
        frontmatter {
          date(formatString: "MMMM DD, YYYY")
          update(formatString: "MMM DD, YYYY")
          title
          tags
          series
          emoji
        }
      }
    }
  }
`
