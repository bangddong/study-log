# 스타터 커스터마이징 가이드

이 템플릿은 빠르고 유연한 커스터마이징을 염두에 두고 만들어졌습니다.

## 🧠 SEO 메타태그 수정

`src/components/SEO/index.jsx` 파일을 수정하면 메타 정보 등을 조정할 수 있습니다.

## 💻 Header, Footer 커스터마이징

- Header: `src/components/layout/Header/index.jsx`
- Footer: `src/components/layout/Footer/index.jsx`

메뉴, 로고, 다크모드 토글 등도 이곳에서 수정 가능합니다.

## ☺️ Customization
`blog-config.js` 파일의 내용을 수정해 다양한 설정을 적용할 수 있습니다.

```javascript
module.exports = {
   title: "YOUR:BLOG:NAME",    // 블로그 제목 (SEO)
   headerTitle: "YOUR:<em style='color:#ed6c02'>BLOG</em>:NAME", // 로고 1
   headerSubTitle: "<em style='color:#ed6c02'>YOUR</em>:BLOG:<em style='color:#ed6c02'>NAME</em>", // 로고 2
   copyright: "©YOUR:BLOG:NAME", // 저작권
   author: "YOUR:NAME",  // 작성자 이름
   siteUrl: "https://6developer.com/", // 사이트 주소
   description: "Hi, Nice to meet you !",  // 블로그 소개 문구
   links: {
      github: "https://github.com/rundevelrun",
      ...
   },
   giscus: {
      ...
   },
   adsense: {
      ...
   }
}
```
