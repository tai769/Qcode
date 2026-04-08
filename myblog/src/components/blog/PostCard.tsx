'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Calendar, Clock, ArrowRight } from 'lucide-react';
import GlassCard from '@/components/glass/GlassCard';
import { Post } from '@/types/blog';

interface PostCardProps {
  post: Post;
  index?: number;
}

export default function PostCard({ post, index = 0 }: PostCardProps) {
  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getReadTimeFromMinutes = (minutes: number) => {
    return `${minutes} min`;
  };

  return (
    <Link href={`/posts/${post.slug}`}>
      <GlassCard hover>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: index * 0.1 }}
          className="h-full"
        >
          <div className="flex items-center gap-3 mb-4">
            <span className="px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-sm">
              {post.category}
            </span>
            {post.featured && (
              <span className="px-3 py-1 rounded-full bg-pink-500/20 text-pink-300 text-sm">
                精选
              </span>
            )}
          </div>

          <h3 className="text-2xl font-bold text-white mb-3 line-clamp-2">
            {post.title}
          </h3>

          <p className="text-white/70 mb-6 line-clamp-3">
            {post.excerpt}
          </p>

          <div className="flex items-center justify-between border-t border-white/10 pt-4">
            <div className="flex items-center gap-4 text-white/50 text-sm">
              <div className="flex items-center gap-1">
                <Calendar size={14} />
                <span>{formatDate(post.date)}</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock size={14} />
                <span>{post.readingTime ? getReadTimeFromMinutes(post.readingTime) : '未设置'}</span>
              </div>
            </div>

            <motion.div
              className="text-white/50 hover:text-white transition-colors flex items-center gap-1"
              whileHover={{ x: 5 }}
            >
              <span className="text-sm">阅读更多</span>
              <ArrowRight size={16} />
            </motion.div>
          </div>

          {post.tags && post.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-1 rounded text-xs text-white/40 bg-white/5"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </motion.div>
      </GlassCard>
    </Link>
  );
}
