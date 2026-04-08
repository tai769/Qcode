'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { Calendar, Clock, ArrowLeft, Share2 } from 'lucide-react';
import { getPostBySlug, posts } from '@/data/posts';
import { Post } from '@/types/blog';
import ReadingProgress from '@/components/blog/ReadingProgress';
import TableOfContents, { parseHeadings } from '@/components/blog/TableOfContents';
import BackButton from '@/components/blog/BackButton';
import MarkdownContent from '@/components/blog/MarkdownContent';
import GlassCard from '@/components/glass/GlassCard';
import Navbar from '@/components/layout/Navbar';
import FluidBackground from '@/components/background/FluidBackground';

export default function PostPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [post, setPost] = useState<Post | null>(null);
  const [headings, setHeadings] = useState<Array<{ id: string; text: string; level: number }>>([]);

  useEffect(() => {
    const foundPost = getPostBySlug(slug);
    setPost(foundPost || null);
    
    if (foundPost?.content) {
      setHeadings(parseHeadings(foundPost.content));
    }
  }, [slug]);

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (!post) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white">文章未找到</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <FluidBackground />
      <Navbar />
      <ReadingProgress />
      
      {/* 目录导航 - 固定在右侧 */}
      {headings.length > 0 && <TableOfContents headings={headings} />}

      <main className="pt-28 pb-20 px-4 md:px-8 lg:px-16">
        <div className="max-w-4xl mx-auto">
          {/* 返回按钮 */}
          <BackButton href="/posts" label="返回文章列表" />

          {/* 文章头部信息 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-12"
          >
            {/* 标签和分类 */}
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <span className="px-4 py-1.5 rounded-full bg-gradient-to-r from-purple-500/20 to-cyan-500/20 text-purple-300 text-sm font-medium border border-purple-500/30">
                {post.category}
              </span>
              {post.tags?.map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1.5 rounded-full bg-white/5 text-white/60 text-sm border border-white/10 hover:border-white/20 transition-all"
                >
                  #{tag}
                </span>
              ))}
            </div>

            {/* 标题 */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight"
            >
              {post.title}
            </motion.h1>

            {/* 摘要 */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-xl text-white/70 mb-8 leading-relaxed"
            >
              {post.excerpt}
            </motion.p>

            {/* 元数据 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="glass p-4 rounded-xl flex items-center gap-6 text-white/60 text-sm"
            >
              <div className="flex items-center gap-2">
                <Calendar size={16} className="text-purple-400" />
                <span>{formatDate(post.date)}</span>
              </div>
              <div className="w-px h-4 bg-white/20" />
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-cyan-400" />
                <span>{post.readingTime} 分钟阅读</span>
              </div>
              <div className="w-px h-4 bg-white/20" />
              <div className="flex items-center gap-2">
                <span className="text-amber-400">作者</span>
                <span>{post.author || '博主'}</span>
              </div>
            </motion.div>
          </motion.div>

          {/* 文章内容 */}
          <GlassCard hover={false} className="p-6 md:p-10 lg:p-12">
            <MarkdownContent content={post.content} />
          </GlassCard>

          {/* 相关文章推荐 */}
          {posts.length > 1 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="mt-16"
            >
              <h3 className="text-2xl font-bold text-white mb-8">相关文章</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {posts
                  .filter(p => p.id !== post.id)
                  .slice(0, 2)
                  .map((relatedPost) => (
                    <Link key={relatedPost.id} href={`/posts/${relatedPost.slug}`}>
                      <GlassCard hover className="h-full p-6">
                        <h4 className="text-lg font-semibold text-white mb-3 line-clamp-2">
                          {relatedPost.title}
                        </h4>
                        <p className="text-white/60 text-sm line-clamp-3 mb-4">
                          {relatedPost.excerpt}
                        </p>
                        <div className="flex items-center justify-between text-white/40 text-xs">
                          <span>{formatDate(relatedPost.date)}</span>
                          <ArrowLeft size={14} className="rotate-180" />
                        </div>
                      </GlassCard>
                    </Link>
                  ))}
              </div>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
}
