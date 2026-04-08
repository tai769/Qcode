export const SITE_CONFIG = {
  name: '我的博客',
  description: '探索技术，分享知识',
  url: 'https://myblog.vercel.app',
  author: '博主',
  email: 'contact@example.com',
  social: {
    github: 'https://github.com',
    twitter: 'https://twitter.com',
    linkedin: 'https://linkedin.com',
  },
}

export const NAVIGATION_ITEMS = [
  { label: '首页', href: '/' },
  { label: '博客', href: '/blog' },
  { label: '关于', href: '/about' },
  { label: '联系', href: '/contact' },
] as const

export const BLOG_CATEGORIES = [
  { name: '前端开发', slug: 'frontend' },
  { name: '后端开发', slug: 'backend' },
  { name: 'DevOps', slug: 'devops' },
  { name: '设计', slug: 'design' },
  { name: '其他', slug: 'other' },
] as const

export const THEME_COLORS = {
  primary: '#8b5cf6',
  secondary: '#06b6d4',
  accent: '#f59e0b',
}
