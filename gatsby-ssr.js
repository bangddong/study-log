/**
 * Implement Gatsby's SSR (Server Side Rendering) APIs in this file.
 *
 * See: https://www.gatsbyjs.com/docs/ssr-apis/
 */

const React = require("react")
const { adsense } = require("./blog-config")

exports.onRenderBody = ({ setHeadComponents }) => {
  if (adsense && adsense.client) {
    setHeadComponents([
      React.createElement("script", {
        key: "google-adsense",
        async: true,
        src: `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${adsense.client}`,
        crossOrigin: "anonymous",
      }),
    ])
  }
}
