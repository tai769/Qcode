# 个人博客项目架构设计文档 (MVP)

## 🎯 MVP 范围界定

**纯展示型个人博客** - 无交互功能，专注于视觉效果展示

---

## 项目概述

**技术栈**: Next.js 14 + TypeScript + Tailwind + shadcn/ui + React. Three Fiber + Framer Motion

**设计风格**: 玻璃态3D风格 - 毛玻璃卡片、3D流体背景、平滑滚动动画、悬浮发光边框、渐变模糊背景

**部署目标**: Vercel

**MVP核心优先级**: 视觉效果 > 响应式 > 核心功能 > 性能

---

## 📌 MVP 功能边界（扩展版）

| 功能 | MVP状态 | 说明 |
|------|---------|------|
| 首页文章列表 | ✅ 包含 | 首页展示所有博客文章卡片 |
| 文章详情页 | ✅ 包含 | 展示文章完整内容 + 阅读进度条 + 文章目录 |
| 3D流体背景 | ✅ 包含 | 全页面动态背景 |
| 玻璃态卡片 | ✅ 包含 | 所有卡片组件 |
| 滚动动画 | ✅ 包含 | 页面滚动时的交互动画 |
| 文章列表页 | ✅ 包含 | 独立文章列表页面（搜索+分类过滤） |
| 关于页面 | ✅ 包含 | 个人介绍 + 技能展示 |
| 联系页面 | ✅ 包含 | 联系表单（纯展示，无后端） |
| 导航栏 | ✅ 包含 | 响应式毛玻璃导航栏 |
| 页脚 | ✅ 包含 | 社交链接 + 版权信息 |
| 评论区 | ❌ 不包含 | 无交互功能 |
| 暗色主题 | ❌ 不包含 | MVP仅支持单色主题 |

---

## 一、项目目录结构

```
myblog/
├── src/
│   ├── app/                      # Next.js 14 App Router
│   │   ├── layout.tsx            # 根布局（全局样式、3D背景）
│   │   ├── page.tsx              # 首页（博客列表）
│   │   └── blog/
│   │       └── [slug]/
│   │           └── page.tsx      # 博客详情页
│   │
│   ├── components/               # 组件分层
│   │   ├── layout/               # 布局组件
│   │   │   ├── Header.tsx        # 头部（简洁Logo）
│   │   │   └── Footer.tsx        # 页脚（版权信息）
│   │   │
│   │   ├── ui/                   # 基础UI组件（shadcn/ui）
│   │   │   ├── button.tsx        # 仅需基础button（如"返回首页"）
│   │   │   └── card.tsx          # 基础卡片
│   │   │
│   │   ├── glass/                # 玻璃态组件（核心视觉组件）
│   │   │   ├── GlassCard.tsx     # 毛玻璃卡片
│   │   │   └── GlassContainer.tsx # 玻璃容器
│   │   │
│   │   ├── animation/            # 动画组件（Framer Motion）
│   │   │   ├── FadeIn.tsx        # 淡入动画
│   │   │   └── SlideUp.tsx       # 上滑动画
│   │   │
│   │   ├── three/                # 3D场景组件（核心视觉组件）
│   │   │   ├── Background3D.tsx  # 3D背景容器
│   │   │   ├── FluidBackground.tsx # 流体背景
│   │   │   └── Particles.tsx     # 粒子效果
│   │   │
│   │   └── blog/                 # 博客相关组件
│   │       ├── BlogCard.tsx      # 博客卡片（玻璃态）
│   │       ├── BlogList.tsx      # 博客列表
│   │       ├── BlogDetail.tsx    # 博客详情
│   │       └── TagBadge.tsx      # 标签徽章
│   │
│   ├── lib/                      # 工具库和配置
│   │   ├── utils.ts              # 通用工具函数
│   │   ├── cn.ts                 # classnames合并工具
│   │   └── constants.ts          # 常量配置
│   │
│   ├── hooks/                    # 自定义Hooks
│   │   ├── useScroll.ts          # 滚动监听
│   │   └── useMouse.ts           # 鼠标位置（用于3D交互）
│   │
│   ├── types/                    # TypeScript类型定义
│   │   ├── blog.ts               # 博客相关类型
│   │   └── common.ts             # 通用类型
│   │
│   ├── data/                     # 静态数据
│   │   └── posts.ts              # 博客文章数据
│   │
│   └── styles/                   # 全局样式
│       └── globals.css           # Tailwind + 玻璃态基础样式
│
├── public/                       # 静态资源
│   ├── images/
│   └── fonts/
│
├── components.json               # shadcn/ui配置
├── tailwind.config.ts            # Tailwind配置
├── next.config.js                # Next.js配置
├── tsconfig.json                 # TypeScript配置
└── package.json                  # 依赖配置
```

---

## 二、技术架构设计

### 2.1 组件分层原则（MVP简化版）

```
应用层 (app/)
  ↓
页面组件 (page.tsx + blog/[slug]/page.tsx)
  ↓
业务组件 (components/blog/*)
  ↓
核心视觉组件 (components/glass/* + components/three/*)
  ↓
动画层 (components/animation/*)
  ↓
工具层 (lib/*, hooks/*, types/*)
```

### 2.2 核心依赖说明（MVP必需）

| 依赖 | 用途 | MVP必要性 |
|------|------|-----------|
| Next.js 14 | 全栈框架 | ✅ 必需 |
| TypeScript | 类型安全 | ✅ 必需 |
| Tailwind CSS | 原子化CSS | ✅ 必需 |
| shadcn/ui | UI组件库 | ✅ 必需（仅button/card） |
| React Three Fiber | 3D渲染 | ✅ 必需（核心视觉） |
| @react-three/drei | 3D辅助组件 | ✅ 必需 |
| Framer Motion | 动画库 | ✅ 必需 |
| lucide-react | 图标库 | ✅ 必需 |

---

## 🚨 三、路由设计（扩展版）

### 3.1 完整路由结构（5个页面）

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 | Hero区域 + 文章卡片展示 |
| `/posts` | 文章列表 | 搜索功能 + 分类/标签过滤 |
| `/posts/[slug]` | 博客详情 | 文章完整内容 + 阅读进度条 + 文章目录 |
| `/about` | 关于页面 | 个人介绍 + 技能标签 + 社交链接 |
| `/contact` | 联系页面 | 联系表单（纯展示）+ 联系信息 |

### 3.2 布局策略

- **根布局** (`app/layout.tsx`): 全局样式、字体、3D背景容器
- **首页**: 所有博客文章卡片网格布局
- **详情页**: 文章内容展示，带"返回首页"按钮

---

## 四、3D背景集成方案（核心视觉组件）

### 4.1 技术选择

- **渲染引擎**: React Three Fiber (R3F)
- **辅助库**: @react-three/drei
- **效果**: 流体背景 + 粒子效果

### 4.2 实现方案

```typescript
// components/three/Background3D.tsx
<Canvas>
  <FluidBackground />  // 流体网格/波浪
  <Particles />         // 漂浮粒子
  <ambientLight />
  <directionalLight />
</Canvas>
```

### 4.3 MVP视觉重点

- 流体效果需要足够动态（展示玻璃态3D风格）
- 粒子效果增强空间感
- 移动端降级为简化版本（性能考虑）

### 4.4 性能优化

- 移动端禁用或简化3D效果
- 使用 `useMemo` 缓存几何体

---

## 五、玻璃态UI设计（核心视觉组件）

### 5.1 核心属性

```css
.glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}
```

### 5.2 MVP组件封装（聚焦视觉）

- **GlassCard**: 基础玻璃卡片（博客卡片使用）
- **GlassContainer**: 大型玻璃容器（用于页面区域）

**已移除非MVP组件**:
- ~~GlassButton~~ （简单功能用基础button即可）

### 5.3 MVP动画效果（视觉优先）

- 悬浮时发光边框渐变
- 滚动时卡片依次上滑淡入
- 卡片hover时轻微缩放

---

## 六、状态管理方案（MVP极简）

### 6.1 架构决策

MVP纯展示型，**无复杂状态管理需求**。

### 6.2 MVP状态管理策略

| 状态类型 | 管理方式 | MVP必要性 |
|----------|----------|-----------|
| 页面路由 | Next.js 路由参数 | ✅ 必需 |
| 滚动位置 | 自定义 Hook (useScroll) | ✅ 必需（动画触发） |
| 鼠标位置 | 自定义 Hook (useMouse) | ✅ 必需（3D交互） |
| 3D效果状态 | useState + useEffect | ✅ 必需 |
| 博客数据 | 静态导入 | ✅ 必需 |

**已移除非MVP状态管理**:
- ~~主题切换~~ （MVP仅单色主题）
- ~~表单状态~~ （无交互功能）

---

### 七、动画策略（MVP视觉优先）

### 7.1 Framer Motion 应用（MVP范围）

- **列表渲染**: 博客卡片交错上滑动画
- **滚动触发**: 滚动到视口时触发淡入
- **卡片交互**: hover 时的缩放和发光

### 7.2 MVP性能考虑

- 移动端简化动画
- 优先保证视觉流畅性

---

## 八、数据层设计（MVP静态数据）

### 8.1 MVP方案

```typescript
// data/posts.ts
export const posts = [
  {
    slug: "hello-world",
    title: "Hello World",
    excerpt: "我的第一篇博客",
    content: "...",
    date: "2024-01-01",
    tags: ["前端", "Next.js"],
  },
  // 5-10篇示例文章
]
```

### 8.2 MVP范围明确

- **仅支持静态数据** - 无API调用
- **无Markdown解析** - 内容直接存储
- **无CMS集成** - 手动编辑数据文件

---

## 九、TypeScript 类型设计（MVP精简）

```typescript
// types/blog.ts
export interface Post {
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  date: string;
  tags: string[];
}

// 移除了非MVP类型：
// - Category（无分类筛选）
// - Comment（无评论区）
```

---

## 十、部署配置

### 10.1 Vercel 优化（MVP）

- 启用静态生成 (SSG)
- 字体优化 (next/font)

### 10.2 SEO 配置（MVP）

- 首页和详情页配置基础 metadata

---

## 🎨 十一、开发优先级（MVP 3阶段）

### Phase 1: 基础架构 + UI 框架
**目标**: 搭建项目骨架，配置UI基础

- [x] 初始化 Next.js 项目
- [ ] 创建 src 目录结构
- [ ] 配置 Tailwind + TypeScript
- [ ] 配置 shadcn/ui（button组件）
- [ ] 创建基础布局 (Header + Footer)
- [ ] 创建全局样式

### Phase 2: 3D背景 + 玻璃态组件
**目标**: 实现核心视觉效果

- [ ] 实现 Background3D 组件
- [ ] 实现流体背景效果
- [ ] 实现粒子效果
- [ ] 创建 GlassCard 组件
- [ ] 创建 GlassContainer 组件
- [ ] 集成玻璃态到全局样式

### Phase 3: 核心页面 + 动画
**目标**: 实现MVP功能 + 动画效果

- [ ] 创建首页（博客列表）
- [ ] 创建博客详情页
- [ ] 集成 Framer Motion 动画
- [ ] 实现滚动动画（FadeIn + SlideUp）
- [ ] 实现卡片hover动画
- [ ] 添加示例数据
- [ ] 响应式调整

---

## 十二、团队成员任务依赖

### MVP 任务链

1. **架构师 (architect)** - 任务#9 ✅
   - 输出: MVP架构设计文档 (本文件)

2. **UI 设计师 (ui_designer)** - 任务#10
   - 依赖:就绪
   - 输出: 玻璃态组件视觉规范、首页布局设计稿
   - **MVP重点**: GlassCard、GlassContainer视觉效果

3. **开发者 (developer)** - 任务#11-15
   - 依赖: UI设计完成
   - 输出: 可运行的MVP代码
   - **MVP重点**: Phase 1 → Phase 2 → Phase 3

4. **测试工程师 (tester)** - 任务#16-17
   - 依赖: 代码完成
   - 输出: MVP测试报告
   - **MVP重点**: 视觉效果验证、响应式测试

5. **运维工程师 (devops)** - 任务#18
   - 依赖: 测试通过
   - 输出: Vercel部署验证

---

## 📋 MVP 验收标准

### 视觉效果（优先级最高）
- ✅ 3D流体背景流畅运行
- ✅ 玻璃态卡片清晰可见
- ✅ 悬浮发光边框效果明显
- ✅ 滚动动画平滑无卡顿

### 核心功能
- ✅ 首页显示博客列表
- ✅ 点击卡片跳转到详情页
- ✅ 详情页显示完整内容
- ✅ 可返回首页

### 响应式
- ✅ 移动端3D效果降级
- ✅ 卡片布局自适应
- ✅ 字体大小适配

### 性能
- ✅ 首屏加载时间 < 3秒
- ✅ Lighthouse 性能评分 > 70
- ✅ 无明显卡顿

---

**文档版本**: v2.0 (MVP调整版)
**创建时间**: 2024-04-06
**架构师**: architect
**MVP范围**: 纯展示型个人博客，无交互功能
