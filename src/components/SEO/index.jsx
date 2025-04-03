import React from "react"
import { Helmet } from "react-helmet"
import { siteUrl, title as blogName } from "../../../blog-config"

const SEO = ({ title, description, url }) => {
  return (
    <Helmet>
      {title === blogName ? (
        <title>{blogName}</title>
      ) : (
        <title>{title + ' | ' + blogName}</title>
      ) }
      <meta property="og:url" content={url} />
      <meta property="og:title" content={title} />
      <meta property="og:image" content={`${siteUrl}/og-image.png`} />
      {description && <meta name="description" content={description} />}
      {description && <meta property="og:description" content={description} />}
    </Helmet>
  )
}

export default SEO
