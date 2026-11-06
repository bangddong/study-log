import React from "react"
import { Helmet } from "react-helmet"
import { siteUrl, title as blogName, author, links } from "../../../blog-config"

// article 을 넘기면 글 페이지로 보고 canonical·발행일·구조화 데이터(JSON-LD)를 붙인다.
// 목록 페이지는 url 이 사이트 루트라서 canonical 을 달면 홈과 중복으로 잡히므로 붙이지 않는다.
const SEO = ({ title, description, url, article }) => {
  const image = `${siteUrl}/og-image.png`

  const jsonLd = article && {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: title,
    description,
    datePublished: article.datePublished,
    dateModified: article.dateModified || article.datePublished,
    inLanguage: "ko",
    url,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    image,
    keywords: article.tags?.join(", "),
    author: { "@type": "Person", name: author, url: links.github },
    publisher: { "@type": "Person", name: author, url: siteUrl },
    ...(article.series && {
      isPartOf: { "@type": "CreativeWorkSeries", name: article.series },
    }),
  }

  return (
    <Helmet>
      {title === blogName ? (
        <title>{blogName}</title>
      ) : (
        <title>{title + ' | ' + blogName}</title>
      ) }
      <meta property="og:url" content={url} />
      <meta property="og:title" content={title} />
      <meta property="og:image" content={image} />
      <meta property="og:site_name" content={blogName} />
      <meta property="og:locale" content="ko_KR" />
      <meta property="og:type" content={article ? "article" : "website"} />
      <meta name="twitter:card" content="summary" />
      {description && <meta name="description" content={description} />}
      {description && <meta property="og:description" content={description} />}
      {article && <link rel="canonical" href={url} />}
      {article && (
        <meta property="article:published_time" content={article.datePublished} />
      )}
      {article?.dateModified && (
        <meta property="article:modified_time" content={article.dateModified} />
      )}
      {article && (
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      )}
    </Helmet>
  )
}

export default SEO
