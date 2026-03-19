# Writing Blog Posts

This starter uses file-based routing. All posts live in the `contents/posts/` directory. Each post is a folder with an `index.md` inside.

## 📁 Basic Structure

A 2-depth directory structure is recommended to organise posts by topic and sub-topic:

```
contents/
  posts/
    <topic>/              ← depth 1  (e.g. spring)
      <sub-topic>/        ← depth 2  (e.g. jpa)
        <article>/        ← depth 3  (e.g. jpa-what-is-jpa)
          index.md
```

**Example:**

```
contents/
  posts/
    spring/
      jpa/
        jpa-what-is-jpa/
          index.md
      transaction/
        transaction-propagation-basic/
          index.md
```

The URL for each post is derived automatically from its path (e.g. `/posts/spring/jpa/jpa-what-is-jpa/`).

## 📝 Frontmatter

```md
---
emoji: "🚀"
title: "How do we get started?"
date: 2025-01-19 13:55:00
update: 2025-01-19 13:55:00
tags:
   - rundevelrun
   - howto
series: "Getting Started with Gatsby Blog"
---
```

## ✍️ Writing Content

Use standard Markdown syntax. Code blocks, images, and tables are all supported.

Example:

````md
## Introduction

This blog is powered by Gatsby and Markdown.

```js
console.log("Hello Gatsby!");
```
````