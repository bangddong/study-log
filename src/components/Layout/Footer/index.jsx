import React from "react"
import styled from "styled-components"

import { copyright } from "../../../../blog-config"

const FooterWrapper = styled.footer`
  margin-top: 32px;
  padding: 40px 15px;
  border-top: 1px solid ${props => props.theme.colors.divider};
  text-align: center;
  font-size: 11pt;
  font-weight: lighter;
    max-width: 680px;
    margin: 0 auto;

    color: ${props => props.theme.colors.secondaryText};
    & > div#copyright {
        float:left;
    }
    & > div#themeby {
        // margin-bottom: 15px;
        text-align: right;
        float:right;
    }

`


const Footer = () => {
  return (
    <FooterWrapper>
        <div id={"themeby"}>
          Theme by <a href="https://github.com/rundevelrun/gatsby-starter-rundevelrun" target="blank">
          RUN:DEVEL:RUN
        </a>
          {" "}Built with Gatsby
        </div>
        <div id={"copyright"} dangerouslySetInnerHTML={{ __html: copyright }}></div>
    </FooterWrapper>
  )
}

export default Footer
