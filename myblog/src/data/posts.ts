import { Post } from '@/types/blog'

export const posts: Post[] = [
  {
    id: '1',
    slug: 'getting-started-with-nextjs-14',
    title: 'Next.js 14 入门指南',
    excerpt: '探索 Next.js 14 的新特性，包括 App Router、Server Actions 和更多激动人心的改进。',
    content: `
# Next.js 14 入门指南

Next.js 14 带来了许多激动人心的新特性和改进。本文将带你了解最重要的变化。

## App Router

App Router 是 Next.js 13 引入的新路由系统，在 14 中更加成熟稳定。它基于 React Server Components 构建。

## Server Actions

Server Actions 让你可以在客户端直接调用服务器端函数，无需创建 API 路由。

\`\`\`typescript
'use server'

export async function createTodo(formData: FormData) {
  const title = formData.get('title')
  // 处理数据...
}
\`\`\`

## 性能优化

Next.js 14 引入了 partial prerendering，可以混合静态和动态渲染。
`,
    date: '2024-01-15',
    tags: ['Next.js', 'React', '前端开发'],
    category: '前端开发',
    author: '博主',
    readingTime: 5,
  },
  {
    id: '2',
    slug: 'building-3d-interfaces-with-react-three-fiber',
    title: '使用 React Three Fiber 构建 3D 界面',
    excerpt: '学习如何在 Web 应用中集成 Three.js，创建令人惊叹的 3D 交互体验。',
    content: `
# 使用 React Three Fiber 构建 3D 界面

React Three Fiber 是 Three.js 的 React 渲染器，让创建 3D 场景变得简单。

## 基础设置

首先安装依赖：

\`\`\`bash
npm install three @react-three/fiber
\`\`\`

## 创建第一个 3D 场景

\`\`\`tsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'

function Scene() {
  return (
    <Canvas>
      <mesh>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="hotpink" />
      </mesh>
      <OrbitControls />
    </Canvas>
  )
}
\`\`\`

## 性能优化

使用 InstancedMesh 处理大量相同物体，使用 useFrame 优化动画循环。
`,
    date: '2024-02-20',
    tags: ['Three.js', 'React', '3D', '前端开发'],
    category: '3D开发',
    author: '博主',
    readingTime: 8,
  },
  {
    id: '3',
    slug: 'advanced-framer-motion-techniques',
    title: 'Framer Motion 高级技巧',
    excerpt: '深入探索 Framer Motion 的高级功能，创建流畅的动画效果和微交互。',
    content: `
# Framer Motion 高级技巧

Framer Motion 是 React 最强大的动画库之一。

## 布局动画

使用 layout prop 自动处理元素位置变化的动画。

\`\`\`tsx
<motion.div
  layout
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
>
  内容
</motion.div>
\`\`\`

## 交错动画

使用 stagger 实现列表项依次出现的动画效果。

\`\`\`tsx
const variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      staggerChildren: 0.1,
    },
  },
}
\`\`\`

## 手势和拖拽

Framer Motion 提供了内置的手势系统。

\`\`\`tsx
<motion.div
  drag
  dragConstraints={{ left: -100, right: 100 }}
  whileHover={{ scale: 1.1 }}
>
  拖拽我
</motion.div>
\`\`\`
`,
    date: '2024-03-10',
    tags: ['Framer Motion', 'React', '动画', '前端开发'],
    category: '动画',
    author: '博主',
    readingTime: 6,
  },
  {
    id: '4',
    slug: 'modern-css-techniques',
    title: '现代 CSS 技术探索',
    excerpt: '了解 CSS Grid、Container Queries、CSS Nesting 等现代 CSS 特性。',
    content: `
# 现代 CSS 技术探索

CSS 正在不断进化，让我们来看看最新的特性。

## CSS Grid

Grid 是最强大的 CSS 布局系统。

\`\`\`css
.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}
\`\`\`

## Container Queries

根据容器尺寸应用样式，而非视口尺寸。

\`\`\`css
@container (min-width: 300px) {
  .card {
    grid-template-columns: 1fr 1fr;
  }
}
\`\`\`

## CSS Nesting

原生支持 CSS 嵌套。

\`\`\`css
.card {
  padding: 1rem;
  
  &:hover {
    background: #f0f0f0;
  }
}
\`\`\`
`,
    date: '2024-04-05',
    tags: ['CSS', '前端开发', '设计'],
    category: 'CSS',
    author: '博主',
    readingTime: 4,
  },
  {
    id: '5',
    slug: 'typescript-best-practices',
    title: 'TypeScript 最佳实践',
    excerpt: '掌握 TypeScript 3D的高级类型系统和最佳实践，提升代码质量。',
    content: `
# TypeScript 最佳实践

TypeScript 越来越流行，这里是一些最佳实践建议。

## 类型守卫

\`\`typescript
function isString(value: unknown): value is string {
  return typeof value === 'string'
}
\`\`

## 泛型约束

\`\`typescript
interface Lengthwise {
  length: number
}

function logLength<T extends Lengthwise>(arg: T) {
  console.log(arg.length)
}
\`\`

## 工具类型

TypeScript 提供了许多内置工具类型。

- \`Partial<T>\` - 将所有属性设为可选
- \`Pick<T>\` - 选择指定属性
- \`Omit<T>\` - 排除指定属性
- \`Record<K, T>\` - 创建对象类型
`,
    date: '2024-04-12',
    tags: ['TypeScript', 'JavaScript', '前端开发'],
    category: 'TypeScript',
    author: '博主',
    readingTime: 7,
  },
]

export const categories = ['前端开发', '3D开发', '动画', 'CSS', 'TypeScript']

export const allTags = ['Next.js', 'React', '前端开发', 'Three.js', '3D', 'Framer Motion', '动画', 'CSS', '设计', 'TypeScript', 'JavaScript']

export function getPostBySlug(slug: string): Post | undefined {
  return posts.find(post => post.slug === slug)
}

export function getPostsByTag(tag: string): Post[] {
  return posts.filter(post => post.tags.includes(tag))
}

export function getAllTags(): string[] {
  const tags = posts.flatMap(post => post.tags)
  return Array.from(new Set(tags))
}
