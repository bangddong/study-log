import React, { useState, useCallback } from "react"
import styled from "styled-components"
import SEO from "components/SEO"
import { graphql } from "gatsby"

import Layout from "components/Layout"
import PostList from "components/PostList"
import TextField from "components/TextField"
import Badge from '@mui/material/Badge';
import VerticalSpace from "components/VerticalSpace"

import { title, description, siteUrl } from "../../blog-config"
import Divider from "../components/Divider"
import Bio from "../components/Bio"

const SearchWrapper = styled.div`
  margin-top: 20px;
  @media (max-width: 768px) {
    padding: 0 15px;
  }
`

const Search = ({ data }) => {
  const posts = data.allMarkdownRemark.nodes

  const [query, setQuery] = useState("")

  const filteredPosts = useCallback(
    posts.filter(post => {
      const { frontmatter, rawMarkdownBody } = post
      const { title } = frontmatter
      const lowerQuery = query.toLocaleLowerCase()

      if (rawMarkdownBody.toLocaleLowerCase().includes(lowerQuery)) return true

      return title.toLocaleLowerCase().includes(lowerQuery)
    }),
    [query]
  )

  return (
    <Layout>
      <SEO title={title} description={description} url={siteUrl} />
      <VerticalSpace size={30} />
      <Bio/>
      <VerticalSpace size={30} />
      <SearchWrapper>
        <Badge badgeContent={filteredPosts.length} color="warning" max={99} showZero={true}
        sx={{top:'5px', left: '2px'}}>
        </Badge>
        <TextField
          onChange={e => setQuery(e.target.value)}
          placeholder="Search"
        />
      </SearchWrapper>
      <Divider />
      <PostList postList={filteredPosts} />
    </Layout>
  )
}

export default Search

export const pageQuery = graphql`
  query {
    allMarkdownRemark(
      sort: { fields: [frontmatter___date], order: DESC }
      filter: { fileAbsolutePath: { regex: "/contents/posts/" } }
    ) {
      nodes {
        excerpt(pruneLength: 200, truncate: true)
        fields {
          slug
        }
        frontmatter {
          date(formatString: "MMMM DD, YYYY")
          title
          tags
          emoji
          series
        }
        rawMarkdownBody
      }
    }
  }
`
