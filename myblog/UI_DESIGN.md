# 个人博客 UI 设计文档

> **目标**: 打造玻璃态3D风格的个人博客界面  
> **风格关键词**: 深色主题、毛玻璃、发光边框、流体背景、流畅动画  
> **技术栈**: Next.js 14 + Tailwind + shadcn/ui + Framer Motion

---

## 一、色彩系统 (Color System)

### 1.1 核心色板 - 深色主题

#### 主色调 (Primary Colors)
```css
/* 主品牌色 - 赛博蓝紫渐变 */
--primary-from: #6366f1;  /* Indigo-500 */
--primary-to: #a855f7;     /* Purple-500 */

/* 辅助色 - 青色 */
--accent: #06b6d4;          /* Cyan-500 */
```

#### 背景色系 (Background Colors)
```css
/* 深色背景渐变 */
--bg-base: #0f172a;         /* Slate-900 */
--bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #1e293b 100%);

/* 玻璃态背景 */
--glass-bg: rgba(30, 41, 59, 0.4);           /* Slate-800, 40% opacity */
--glass-bg-strong: rgba(15, 23, 42, 0.7);    /* Slate-900, 70% opacity */
--glass-bg-light: rgba(148, 163, 184, 0.1);  /* Slate-400, 10% opacity */
```

#### 文字颜色 (Text Colors)
```css
--text-primary: #f8fafc;    /* Slate-50 - 标题、正文 */
--text-secondary: #94a3b8;  /* Slate-400 - 次要文字 */
--text-muted: #64748b;      /* Slate-500 - 弱化文字 */
--text-accent: #67e8f9;     /* Cyan-300 - 强调文字 */
```

#### 边框颜色 (Border Colors)
```css
--border-glass: rgba(255, 255, 255, 0.1);
--border-glow: rgba(99, 102, 241, 0.5);
--border-hover: rgba(168, 85, 247, 0.8);
```

#### 发光效果 (Glow Effects)
```css
--glow-primary: 0 0 20px rgba(99, 102, 241, 0.4);
--glow-accent: 0 0 20px rgba(6, 182, 212, 0.4);
--glow-hover: 0 0 30px rgba(168, 85, 247, 0.6);
```

### 1.2 功能色系 (Functional Colors)

#### 成功 / 警告 / 错误
```css
--success: #10b981;    /* Emerald-500 */
--warning: #f59e0b;    /* Amber-500 */
--error: #ef4444;      /* Red-500 */
```

### 1.3 渐变定义 (Gradients)

```css
/* 主渐变 */
.gradient-primary {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
}

/* 发光渐变 */
.gradient-glow {
  background: linear-gradient(135deg, 
    rgba(99, 102, 241, 0.5) 0%, 
    rgba(168, 85, 247, 0.5) 50%, 
    rgba(6, 182, 212, 0.5) 100%);
}

/* 文字渐变 */
.gradient-text {
  background: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

---

## 二、排版系统 (Typography)

### 2.1 字体家族

```css
/* 标题字体 - 现代、几何感 */
--font-heading: 'Inter', system-ui, sans-serif;

/* 正文字体 - 易读 */
--font-body: 'Inter', system-ui, sans-serif;

/* 代码字体 */
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### 2.2 字体大小层级

| 用途 | 大小 | 行高 | 字重 | Tailwind Class |
|------|------|------|------|----------------|
| H1 (页面标题) | 48px | 1.1 | 700 | text-4xl font-bold |
| H2 (区块标题) | 36px | 1.2 | 600 | text-3xl font-semibold |
| H3 (卡片标题) | 24px | 1.3 | 600 | text-2xl font-semibold |
| H4 (小标题) | 20px | 1.4 | 500 | text-xl font-medium |
| Body (正文) | 16px | 1.6 | 400 | text-base |
| Small (辅助文字) | 14px | 1.5 | 400 | text-sm |
| Tiny (标签等) | 12px | 1.4 | 400 | text-xs |

### 2.3 字距与间距

```css
--letter-spacing-tight: -0.025em;  /* 标题紧凑 */
--letter-spacing-normal: 0;         /* 默认 */
--letter-spacing-wide: 0.025em;     /* 宽松 */
```

---

## 三、玻璃态组件规范 (Glass Component Specs)

### 3.1 基础玻璃卡片 (GlassCard)

#### 样式定义
```css
.glass-card {
  /* 背景 */
  background: rgba(30, 41, 59, 0.4);
  
  /* 毛玻璃效果 */
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  
  /* 边框 */
  border: 1px solid rgba(255, 255, 255, 0.1);
  
  /* 阴影 */
  box-shadow: 
    0 4px 6px rgba(0, 0, 0, 0.1),
    0 10px 20px rgba(0, 0, 0, 0.15);
  
  /* 圆角 */
  border-radius: 16px;
  
  /* 内边距 */
  padding: 24px;
}
```

#### Tailwind 实现
```tsx
<div className="bg-slate-800/40 backdrop-blur-md border border-white/10 
            rounded-2xl p-6 shadow-lg">
  {/* 内容 */}
</div>
```

### 3.2 悬浮发光卡片 (GlassCard with Glow)

#### Hover 状态
```css
.glass-card:hover {
  border-color: rgba(168, 85, 247, 0.6);
  box-shadow: 
    0 8px 16px rgba(0, 0, 0, 0.2),
    0 0 30px rgba(168, 85, 247, 0.4);
  transform: translateY(-4px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

#### Tailwind 实现
```tsx
<div className="group relative bg-slate-800/40 backdrop-blur-md 
            border border-white/10 rounded-2xl p-6 shadow-lg
            hover:border-purple-500/60 hover:-translate-y-1
            hover:shadow-[0_8px_16px_rgba(0,0,0,0.2),0_0_30px_rgba(168,85,247,0.4)]
            transition-all duration-300 ease-out">
  {/* 发光边框装饰 */}
  <div className="absolute inset-0 rounded-2xl bg-gradient-to-r 
                  from-purple-500/0 via-purple-500/20 to-purple-500/0 
                  opacity-0 group-hover:opacity-100 
                  transition-opacity duration-300 blur-sm" />
  {/* 内容 */}
</div>
```

### 3.3 玻璃按钮 (GlassButton)

#### 主按钮样式
```css
.glass-button {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.8), rgba(168, 85, 247, 0.8));
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 12px 24px;
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.glass-button:hover {
  box-shadow: 0 0 20px rgba(168, 85, 247, 0.6);
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.4);
}

.glass-button:active {
  transform: translateY(0);
}
```

#### 次要按钮（描边样式）
```css
.glass-button-outline {
  background: transparent;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 12px 24px;
  color: rgba(248, 250, 252, 0.9);
}

.glass-button-outline:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(99, 102, 241, 0.6);
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);
}
```

### 3.4 玻璃容器 (GlassContainer)

用于页面大区块，如侧边栏、导航栏
```css
.glass-container {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
```

---

## 四、交互动画规范 (Interaction Design)

### 4.1 Framer Motion 动画参数

#### 淡入 (FadeIn)
```tsx
"fadeIn": {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.5, ease: "easeOut" }
}
```

#### 上滑 (SlideUp)
```tsx
"slideUp": {
  initial: { opacity: 0, y: 40 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }
}
```

#### 交错列表 (Staggered List)
```tsx
"staggerContainer": {
  hidden: { opacity: 0 },
  show: { 
    opacity: 1, 
    transition: { staggerChildren: 0.1 }
  }
}

"staggerItem": {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
}
```

#### 卡片悬浮 (Card Hover)
```tsx
"cardHover": {
  whileHover: { 
    scale: 1.02,
    y: -4,
    transition: { duration: 0.3, ease: "easeOut" }
  }
}
```

### 4.2 滚动触发动画

#### ScrollProgress 组件
- 滚动时显示顶部进度条
- 渐变色的细线条 (2px height)
- 渐变：indigo → purple → cyan

#### 视口触发动画
```tsx
// 使用 useInView 触发
<motion.div
  initial={{ opacity: 0, y: 30 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, margin: "-100px" }}
  transition={{ duration: 0.6 }}
>
  {/* 内容 */}
</motion.div>
```

### 4.3 页面切换动画

```tsx
// 使用 AnimatePresence + layout
<motion.div
  layout
  initial={{ opacity: 0, x: 20 }}
  animate={{ opacity: 1, x: 0 }}
  exit={{ opacity: 0, x: -20 }}
  transition={{ duration: 0.3 }}
>
  {/* 页面内容 */}
</motion.div>
```

---

## 五、响应式布局 (Responsive Design)

### 5.1 断点定义

| 断点名 | Tailwind | 屏幕宽度 | 用途 |
|--------|----------|----------|------|
| Mobile | default | < 640px | 手机竖屏 |
| sm | sm: | ≥ 640px | 手机大屏 |
| md | md: | ≥ 768px | 平板竖屏 |
| lg | lg: | ≥ 1024px | 平板横屏 / 小笔记本 |
| xl | xl: | ≥ 1280px | 桌面 |
| 2xl | 2xl: | ≥ 1536px | 大屏 |

### 5.2 布局结构

#### 首页布局 (Home)
```tsx
// Mobile
- Header (sticky, 简化导航)
- Hero Section (全宽，文字居中)
- Featured Posts (单列)
- Footer

// Desktop
- Header (sticky, 完整导航)
- Hero Section (双列：左侧文字，右侧3D元素)
- Featured Posts (3列网格)
- Recent Posts (2列网格)
- Footer (多列)
```

#### 博客列表页 (Blog List)
```tsx
// Mobile
- Header
- 过滤器 (横向滚动)
- 博客卡片 (单列)
- 分页

// Desktop
- Header
- 侧边栏 (左侧，30% - 分类、标签)
- 博客列表 (右侧，70% - 3列网格)
```

#### 博客详情页 (Blog Detail)
```tsx
// Mobile
- Header
- 文章内容 (单列，最大宽度 100%)
- 相关文章 (单列)

// Desktop
- Header
- 文章内容 (居中，最大宽度 720px)
- 侧边栏 (右侧，目录、标签)
- 相关文章 (2列)
```

### 5.3 网格系统

```tsx
// 博客卡片网格
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* Blog Cards */}
</div>

// 侧边栏 + 主内容布局
<div className="lg:flex lg:gap-8">
  <aside className="lg:w-1/4">
    {/* 侧边栏 */}
  </aside>
  <main className="lg:w-3/4">
    {/* 主内容 */}
  </main>
</div>
```

---

## 六、组件设计清单 (Component Design Specs)

### 6.1 Layout 组件

#### Header 组件
```
样式：
- 固定顶部 (sticky top-0)
- 玻璃态背景 (backdrop-blur-lg)
- 发光下边框 (border-b border-white/10)
- 响应式：移动端汉堡菜单，桌面端完整导航

内容：
[logo] [导航链接] [主题切换] [GitHub图标]
```

#### Footer 组件
```
样式：
- 深色背景
- 多列布局 (Desktop)
- 玻璃态卡片链接

内容：
[关于] [博客] [资源] [社交媒体]
[版权信息]
```

#### Navigation 组件
```
样式：
- 移动端：侧边栏抽屉
- 桌面端：水平链接
- Hover 时文字渐变色 + 下划线动画
```

### 6.2 Blog 组件

#### BlogCard 组件
```
结构：
┌─────────────────────┐
│ [封面图/渐变占位]   │ ← 渐变背景 + 3D图标装饰
│                     │
│ [标签]              │ ← 小圆角胶囊
│                     │
│ [标题]              │ ← 渐变色文字
│ [摘要]              │ ← 浅色文字
│                     │
│ [日期] · [阅读时间] │ ← 小字灰色
└─────────────────────┘

样式：
- 玻璃态卡片
- Hover 时上浮 + 发光边框
- 封面图使用渐变或3D图形（避免图片加载）
```

#### BlogList 组件
```
功能：
- 接收 posts 数组
- 渲染网格布局
- 交错动画
- 支持分类过滤
```

#### BlogDetail 组件
```
结构：
┌──────────────────────────────────┐
│ [标题] - H1, 渐变色              │
│ [元数据] - 日期、标签、阅读时间  │
├──────────────────────────────────┤
│                                  │
│ [文章内容] - Markdown 渲染       │
│   - 代码块：玻璃态容器 + 高亮    │
│   - 引用块：发光边框             │
│   - 图片：圆角 + 阴影            │
│                                  │
├──────────────────────────────────┤
│ [相关文章]                       │
└──────────────────────────────────┘
```

#### TagBadge 组件
```
样式：
- 小圆角胶囊
- 半透明背景
- Hover 时发光
- 可点击筛选
```

### 6.3 Glass 组件

#### GlassCard.tsx
```tsx
interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;        // 是否启用悬浮效果
  glow?: boolean;         // 是否启用发光
}

// 使用示例：
<GlassCard hover glow>
  <BlogCard {...post} />
</GlassCard>
```

#### GlassButton.tsx
```tsx
interface GlassButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

// 使用示例：
<GlassButton variant="primary" size="md">
  阅读更多
</GlassButton>
```

### 6.4 Animation 组件

#### FadeIn 组件
```tsx
// 通用淡入包装器
<FadeIn delay={0.2}>
  <div>...</div>
</FadeIn>
```

#### SlideUp 组件
```tsx
// 上滑动画包装器
<SlideUp staggerDelay={0.1}>
  <div>...</div>
</SlideUp>
```

#### ScrollProgress 组件
```tsx
// 顶部滚动进度条
<ScrollProgress color="gradient" />
```

---

## 七、页面视觉规范 (Page Visual Specs)

### 7.1 首页 (Home)

#### Hero Section
```
标题：
  "Hi, I'm [名字]"
  渐变色：indigo → purple → cyan
  字体：H1 (48px, 700)

副标题：
  "前端开发者 / 开源爱好者 / 3D爱好者"
  浅灰色

CTA 按钮：
  [查看博客] - 主按钮，渐变背景
  [联系我] - 描边按钮

右侧元素（Desktop）：
  3D 旋转立方体或球体
  粒子漂浮效果
```

#### 最新文章
```
标题：Latest Posts (H2)
布局：3列网格
卡片：BlogCard（带玻璃态）
动画：交错上滑
```

### 7.2 博客列表页

```
顶部标题：Blog (渐变色，H1)
过滤栏：[全部] [前端] [3D] [随笔] - 可点击筛选
文章网格：响应式网格
分页：玻璃态按钮组
```

### 7.3 博客详情页

```
面包屑：Home > Blog > [标题]
文章容器：最大宽度 720px，居中
代码块：玻璃态背景 + 语法高亮
引用块：发光边框 + 淡背景
```

### 7.4 关于页

```
左侧：头像 + 基本信息
右侧：个人介绍 + 技能栈标签
底部：GitHub 链接 + 社交媒体
```

### 7.5 联系页

```
表单容器：玻璃态卡片
输入框：玻璃态边框 + Focus 发光
按钮：提交按钮
```

---

## 八、Tailwind 配置建议 (Tailwind Config)

### 8.1 扩展配置 (tailwind.config.ts)

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // 主色调
        primary: {
          from: '#6366f1',  // Indigo-500
          to: '#a855f7',     // Purple-500
        },
        accent: {
          DEFAULT: '#06b6d4',  // Cyan-500
          light: '#67e8f9',    // Cyan-300
        },
        
        // 玻璃态
        glass: {
          base: 'rgba(30, 41, 59, 0.4)',
          strong: 'rgba(15, 23, 42, 0.7)',
          light: 'rgba(148, 163, 184, 0.1)',
        },
      },
      
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
        'gradient-glow': 'linear-gradient(135deg, rgba(99,102,241,0.5) 0%, rgba(168,85,247,0.5) 50%, rgba(6,182,212,0.5) 100%)',
        'mesh-gradient': 'radial-gradient(at 0% 0%, rgba(99,102,241,0.3) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(168,85,247,0.3) 0px, transparent 50%)',
      },
      
      boxShadow: {
        glow: '0 0 20px rgba(99, 102, 241, 0.4)',
        'glow-accent': '0 0 20px rgba(6, 182, 212, 0.4)',
        'glow-hover': '0 0 30px rgba(168, 85, 247, 0.6)',
        glass: '0 4px 6px rgba(0, 0, 0, 0.1), 0 10px 20px rgba(0, 0, 0, 0.15)',
     
        
        fontFamily: {
          sans: ['Inter', 'system-ui', 'sans-serif'],
          mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        },
        
        animation: {
          'fade-in': 'fadeIn 0.5s ease-out',
          'slide-up': 'slideUp 0.6s ease-out',
          'pulse-slow': 'pulse 4s ease-in-out infinite',
        },
        
        keyframes: {
          fadeIn: {
            '0%': { opacity: '0' },
            '100%': { opacity: '1' },
          },
          slideUp: {
            '0%': { opacity: '0', transform: 'translateY(20px)' },
            '100%': { opacity: '1', transform: 'translateY(0)' },
          },
        },
      },
    },
  plugins: [],
}
export default config
```

### 8.2 自定义工具类 (src/styles/globals.css)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 5%;
    --foreground: 0 0% 98%;
  }
  
  * {
    @apply border-white/10;
  }
  
  body {
    @apply bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900
           text-slate-50 antialiased;
  }
}

@layer components {
  .glass-card {
    @apply bg-slate-800/40 backdrop-blur-md 
           border border-white/10 
           rounded-2xl shadow-glass;
  }
  
  .glass-card-hover {
    @apply hover:border-purple-500/60 hover:-translate-y-1
           hover:shadow-glow-hover
           transition-all duration-300 ease-out;
  }
  
  .text-gradient {
    @apply bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-500
           bg-clip-text text-transparent;
  }
  
  .glass-input {
    @apply bg-slate-900/50 backdrop-blur-sm 
           border border-white/10 
           rounded-xl px-4 py-3
           text-slate-50 placeholder:text-slate-500
           focus:border-purple-500/50 focus:outline-none 
           focus:shadow-glow
           transition-all duration-200;
  }
}

@layer utilities {
  .text-balance {
    text-wrap: balance;
  }
}
```

---

## 九、3D 背景视觉规范 (3D Background Visual Specs)

### 9.1 Background3D 组件

#### 视觉效果
```
背景层：Canvas 全屏覆盖
- 流体网格/波浪：缓慢流动的网格线
- 粒子系统：随机漂浮的发光粒子
- 鼠标交互：粒子跟随鼠标轻微移动
- 颜色：indigo/purple/cyan 渐变透明
```

#### 性能策略
```
- 移动端：简化粒子数量（20 → 5）
- 降低渲染频率（60fps → 30fps on low-end）
- 使用 GPU 加速
- 离屏不可见时暂停渲染
```

### 9.2 颜色配置

```typescript
const colors = {
  particles: [
    '#6366f1',  // Indigo
    '#a855f7',  // Purple
    '#06b6d4',  // Cyan
  ],
  mesh: 'rgba(99, 102, 241, 0.1)',
}
```

---

## 十、图标系统 (Icon System)

### 10.1 图标库
- **主库**: lucide-react
- **备用**: 自定义 SVG 图标

### 10.2 常用图标清单

| 用途 | 图标 | 颜色 |
|------|------|------|
| Logo | Code2 | 渐变 |
| 导航 | Menu / ArrowRight | 白色 |
| 社交 | Github / Twitter / Mail | 白色 |
| 博客 | BookOpen / Calendar / Clock | 浅灰 |
| 操作 | Search / Filter / Download | 紫色 |
| 反馈 | ThumbsUp / MessageCircle | 青色 |

---

## 十一、无障碍设计 (Accessibility)

### 11.1 对比度要求
- 正文文字对比度 ≥ 4.5:1
- 大文字（24px+）对比度 ≥ 3:1
- 当前设计已满足（白色文字 + 深色背景）

### 11.2 键盘导航
- 所有交互元素支持 Tab 键
- Focus 状态可见（发光边框）
- Skip to content 链接

### 11.3 动画尊重
- 检测 `prefers-reduced-motion`
- 提供动画关闭选项

---

## 十二、设计交付清单 (Design Deliverables)

### ✅ 已完成
1. [x] 色彩系统定义
2. [x] 排版系统
3. [x] 玻璃态组件规范
4. [x] 交互动画规范
5. [x] 响应式布局
6. [x] 组件设计清单
7. [x] Tailwind 配置
8. [x] 3D 背景视觉规范

### 📋 开发者参考
1. 查看 `myblog/UI_DESIGN.md`（本文件）
2. 查看 `myblog/ARCHITECTURE.md`（架构文档）
3. 使用提供的 Tailwind 配置
4. 按组件清单实现

---

**文档版本**: v1.0  
**创建时间**: 2024-04-06  
**UI 设计师**: ui_designer  
**依赖**: ARCHITECTURE.md v1.0
