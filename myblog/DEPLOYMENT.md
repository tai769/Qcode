# Vercel 部署指南

本项目已配置为直接部署到 Vercel 平台。

## 🚀 快速部署

### 方法1: 通过 Vercel CLI

```bash
# 安装 Vercel CLI
npm install -g vercel

# 登录 Vercel
vercel login

# 部署（首次）
vercel

# 生产环境部署
vercel --prod
```

### 方法2: 通过 Vercel Dashboard

1. 访问 [vercel.com](https://vercel.com)
2. 点击 "Add New Project"
3. 导入 GitHub 仓库
4. Vercel 会自动检测 Next.js 配置
5. 配置环境变量（见下方）
6. 点击 "Deploy"

## 🔧 环境变量配置

在 Vercel 项目设置中添加以下环境变量：

```bash
# 站点基础配置
NEXT_PUBLIC_SITE_NAME=My Blog
NEXT_PUBLIC_SITE_URL=https://your-domain.vercel.app
NEXT_PUBLIC_SITE_DESCRIPTION=个人博客

# 功能开关
NEXT_PUBLIC_ENABLE_3D_BACKGROUND=true
NEXT_PUBLIC_ENABLE_ANIMATIONS=true
```

## 📦 部署配置说明

### vercel.json

项目包含 `vercel.json` 配置文件，自动设置：

- **Framework**: Next.js 14
- **Region**: Hong Kong (hkg1) - 优化亚洲访问
- **Security Headers**: XSS 保护、Clickjacking 防护
- **Build Command**: `npm run build`

### 构建优化

- Next.js 自动启用：
  - 静态资源优化 (图片、字体)
  - 代码分割
  - Tree shaking
  - CSS 压缩

## 🔍 部署前检查

确保本地构建成功：

```bash
# 安装依赖
npm install

# 构建测试
npm run build

# 本地预览生产构建
npm start
```

## 📊 监控与分析

部署后可集成：

- **Vercel Analytics**: 内置性能监控
- **Google Analytics**: 在环境变量中配置 `NEXT_PUBLIC_GA_ID`

## 🔄 CI/CD 集成

连接 GitHub 仓库后，Vercel 自动：

- 监听 `main` 分支推送
- 自动运行构建测试
- 构建成功后自动部署预览环境
- 合并到 main 分支后自动部署生产环境

## 🛠️ 故障排查

### 构建失败

1. 检查 `npm run build` 是否在本地成功
2. 查看 Vercel 构建日志
3. 确认 Node.js 版本兼容（Next.js 14 需要 Node.js 18+）

### 环境变量未生效

- 确保变量名以 `NEXT_PUBLIC_` 开头（客户端可用）
- 部署后需要重新构建才能生效

### 3D 资源加载问题

- Vercel 自动优化 Three.js 静态资源
- 如遇加载慢，检查 CDN 配置

## 📞 支持

如遇部署问题，联系 DevOps 团队或查看：
- [Vercel 文档](https://vercel.com/docs)
- [Next.js 部署文档](https://nextjs.org/docs/deployment)
