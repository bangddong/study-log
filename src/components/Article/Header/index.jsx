import React from "react"
import styled from "styled-components"

import { author } from "../../../../blog-config"

import Divider from "components/Divider"
import TagList from "components/TagList"
import { Link } from "gatsby"

const Wrapper = styled.div`
  margin-top: 32px;
  @media (max-width: 768px) {
    padding: 0 15px;
  }
`

const ArticleTitle = styled.h1`
  margin-bottom: 25.6px;
  line-height: 1.2;
  font-size: 32px;
  font-weight: 700;
  color: ${props => props.theme.colors.text};
`

const Information = styled.div`
  margin-bottom: 32px;
  font-size: 16px;
`

const Date = styled.span`
  font-weight: 300;
  color: ${props => props.theme.colors.secondaryText};
`

const EmojiWrapper = styled.div`
  float:left;
  margin-right: 10px;  
`

const Header = ({ title, date, tags, minToRead, emoji}) => {
  return (
    <Wrapper>
      <ArticleTitle>{emoji ? (
          <EmojiWrapper>{emoji}</EmojiWrapper>
        ) : ''
      }{title} </ArticleTitle>
      <Information>
        <Date>· {date} </Date>
        <Date>· {minToRead} min read </Date>
      </Information>
      {tags && <TagList tagList={tags} />}
      <Divider mt="0" />
    </Wrapper>
  )
}

export default Header
