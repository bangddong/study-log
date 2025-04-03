# 배포 가이드

이 프로젝트는 정적 사이트로 빌드되며, 다양한 플랫폼에 배포할 수 있습니다.

## 🧱 정적 빌드

```bash
gatsby build
```

이 명령어를 실행하면 `/public` 폴더가 생성되며, 이 폴더의 내용을 원하는 호스팅 서비스에 업로드하면 됩니다.

## 📦 배포 플랫폼 예시

### ✅ Netlify

1. GitHub 저장소 연결
2. Build command: `gatsby build`
3. Publish directory: `public`

### ✅ Vercel

1. GitHub 저장소 연결
2. Framework: Gatsby 자동 인식
3. Output Directory: `public`

### ✅ GitHub Pages (gh-pages 브랜치 사용)

```bash
npm install gh-pages
npm run deploy
```

> `package.json`에 다음 스크립트 추가 필요:

```json
"scripts": {
  "deploy": "gatsby build && gh-pages -d public"
}
```

## 🌐 도메인 연결

- Netlify 또는 Vercel 대시보드에서 커스텀 도메인 설정 가능
- DNS 설정에서 CNAME 또는 A 레코드로 연결