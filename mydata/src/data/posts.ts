export interface Post {
  id: string;
  title: string;
  excerpt: string;
  content: string;
  date: string;
  category: string;
  tags: string[];
  readTime: number | string;
  featured?: boolean;
}

export const posts: Post[] = [
  {
    id: '1',
    title: '欢迎来到我的博客',
    excerpt: '这是一个使用Next.js 14、React Three Fiber和Framer Motion构建的现代化个人博客。采用了玻璃态UI设计和3D流体背景效果。',
    content: `
# 欢迎来到我的博客

这是一个使用Next.js 14、React Three Fiber和Framer Motion构建的现代化个人博客。

## 技术栈

- **Next.js 14** - React框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 实用优先的CSS框架
- **React Three Fiber** - 3D图形渲染
- **Framer Motion** - 平滑动画

## 设计理念

本博客采用了玻璃态（Glassmorphism）设计风格，包括：
- 毛玻璃卡片
- 3D流体背景
- 平滑滚动动画
- 悬浮发光边框
- 渐变模糊背景

## 开始探索

点击导航栏查看更多文章！
    `,
    date: '2024-01-15',
    category: '简介',
    tags: ['Next.js', 'React', '3D'],
    readTime: '3 min',
    featured: true,
  },
  {
    id: '2',
    title: 'React Three Fiber入门指南',
    excerpt: '学习如何使用React Three Fiber在React应用中创建令人惊叹的3D效果。',
    content: `
# React Three Fiber入门指南

React Three Fiber是一个React渲染器，用于Three.js。

## 安装

\`\`\`bash
npm install three @types/three @react-three/fiber @react-three/drei
\`\`\`

## 基本使用

创建一个简单的3D场景：

\`\`\`jsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'

function App() {
  return (
    <Canvas>
      <mesh>
        <boxGeometry />
        <meshStandardMaterial color="orange" />
      </mesh>
      <OrbitControls />
    </Canvas>
  )
}
\`\`\`

## 流体背景效果

使用着色器和粒子系统创建流体背景。
    `,
    date: '2024-01-10',
    category: '教程',
    tags: ['Three.js', '3D', 'WebGL'],
    readTime: 8,
  },
  {
    id: '3',
    title: 'Framer Motion动画实践',
    excerpt: '探索Framer Motion的强大功能，为你的应用添加流畅的动画效果。',
    content: `
# Framer Motion动画实践

Framer Motion是一个生产就绪的动画库。

## 特性

- 声明式动画
- 手势支持
- 变体系统
- 过渡效果

## 基础动画

\`\`\`jsx
import { motion } from 'framer-motion'

<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
>
  内容
</motion.div>
\`\`\`
    `,
    date: '2024-01-05',
    category: '教程',
    tags: ['动画', 'Framer Motion', 'React'],
    readTime: 6,
  },
  {
    id: '4',
    title: 'Tailwind CSS最佳实践',
    excerpt: '学习如何高效使用Tailwind CSS构建现代化UI。',
    content: `
# Tailwind CSS最佳实践

Tailwind CSS是一个实用优先的CSS框架。

## 配置

自定义tailwind.config.js扩展主题。

## 组织样式

使用@apply指令复用样式类。

## 响应式设计

使用响应式前缀（sm:, md:, lg:等）。
    `,
    date: '2024-01-01',
    category: 'CSS',
    tags: ['Tailwind CSS', 'CSS', 'UI'],
    readTime: 5,
  },
];

export const categories = ['简介', '教程', 'CSS', 'JavaScript', 'React'];

export const allTags = Array.from(new Set(posts.flatMap(post => post.tags)));
