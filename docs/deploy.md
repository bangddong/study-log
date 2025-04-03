# Deployment Guide

This project builds to a static site. You can host it on any static hosting service.

## 🧱 Build the site

```bash
gatsby build
```

The output will be in the `/public` directory.

## 📦 Recommended Platforms

### ✅ Netlify

1. Connect GitHub repo
2. Build command: `gatsby build`
3. Publish directory: `public`

### ✅ Vercel

1. Import GitHub repo
2. Framework: Gatsby (auto-detected)
3. Output directory: `public`

### ✅ GitHub Pages

```bash
npm install gh-pages
npm run deploy
```

Add to `package.json`:

```json
"scripts": {
  "deploy": "gatsby build && gh-pages -d public"
}
```

## 🌐 Custom Domain

Configure in Netlify/Vercel dashboard or via your DNS settings.