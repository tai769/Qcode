'use client';

import { motion } from 'framer-motion';
import GlassCard from '@/components/glass/GlassCard';

export default function Home() {
  const articles = [
    {
      title: 'React Three Fiber 入门指南',
      description: '探索 3D WebGL 在 React 中的应用，打造沉浸式网页体验',
      date: '2024-01-15',
      tags: ['React', 'Three.js', '3D']
    },
    {
      title: 'Framer Motion 动画艺术',
      description: '如何使用 Framer Motion 创建流畅的 UI 动画和过渡效果',
      date: '2024-01-10',
      tags: ['React', 'Animation', 'UI/UX']
    },
    {
      title: 'Next.js 14 最佳实践',
      description: '深度解析 Server Components、App Router 和性能优化策略',
      date: '2024-01-05',
      tags: ['Next.js', 'React', 'Performance']
    }
  ];

  return (
    <main className="min-h-screen text-white">
      
      <div className="container mx-auto px-4 py-16 relative z-10">
        {/* 标题区域 */}
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <motion.h1
            className="text-6xl font-bold mb-4 bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent"
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            欢迎来到我的博客
          </motion.h1>
          <motion.p
            className="text-xl text-gray-300"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            探索技术、设计与创造力的交汇点
          </motion.p>
        </motion.div>

        {/* 文章卡片网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {articles.map((article, index) => (
            <GlassCard key={index} className="p-6">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.6 + index * 0.1 }}
              >
                <div className="flex flex-wrap gap-2 mb-4">
                  {article.tags.map((tag, tagIndex) => (
                    <motion.span
                      key={tagIndex}
                      className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm"
                      whileHover={{ scale: 1.1, backgroundColor: 'rgba(168, 85, 247, 0.3)' }}
                    >
                      {tag}
                    </motion.span>
                  ))}
                </div>
                
                <h3 className="text-2xl font-semibold mb-3 text-white">
                  {article.title}
                </h3>
                
                <p className="text-gray-300 mb-4 line-clamp-3">
                  {article.description}
                </p>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">{article.date}</span>
                  <motion.button
                    className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg text-sm font-medium"
                    whileHover={{ scale: 1.05, boxShadow: '0 0 20px rgba(168, 85, 247, 0.4)' }}
                    whileTap={{ scale: 0.95 }}
                  >
                    阅读更多
                  </motion.button>
                </div>
              </motion.div>
            </GlassCard>
          ))}
        </div>

        {/* 底部信息 */}
        <motion.div
          className="text-center mt-16"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 1.2 }}
        >
          <GlassCard className="inline-block px-8 py-4">
            <p className="text-gray-300">
              使用{' '}
              <span className="text-purple-400">Next.js 14</span> +{' '}
              <span className="text-blue-400">React Three Fiber</span> +{' '}
              <span className="text-pink-400">Framer Motion</span>
              {' '}构建
            </p>
          </GlassCard>
        </motion.div>
      </div>
    </main>
  );
}
