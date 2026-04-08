'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter } from 'lucide-react';
import GlassCard from '@/components/glass/GlassCard';
import PostCard from '@/components/blog/PostCard';
import Footer from '@/components/layout/Footer';
import { posts, getAllTags, categories, allTags } from '@/data/posts';

export default function PostsPage() {
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('全部');
  const [selectedTagFilter, setSelectedTagFilter] = useState('全部');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPosts = posts.filter(post => {
    const matchesCategory = selectedCategoryFilter === '全部' || post.category === selectedCategoryFilter;
    const matchesTag = selectedTagFilter === '全部' || post.tags.includes(selectedTagFilter);
    const matchesSearch = searchQuery === '' || 
      post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.excerpt.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesCategory && matchesTag && matchesSearch;
  });

  return (
    <div className="min-h-screen">
      {/* Header */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-6xl mx-auto text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-4xl md:text-6xl font-bold mb-4"
          >
            <span className="gradient-text">所有文章</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-white/60 text-lg"
          >
            探索 {posts.length} 篇技术文章和心得分享
          </motion.p>
        </div>
      </section>

      {/* Filters */}
      <section className="px-4 md:px-8 py-8">
        <div className="max-w-6xl mx-auto">
          <GlassCard>
            {/* Search */}
            <div className="mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" size={20} />
                <input
                  type="text"
                  placeholder="搜索文章..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-indigo-500/50 transition-colors"
                />
              </div>
            </div>

            {/* Category Filter */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                <Filter size={16} className="text-white/60" />
                <span className="text-white/60 text-sm">分类</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSelectedCategoryFilter('全部')}
                  className={`px-4 py-2 rounded-full text-sm transition-all ${
                    selectedCategoryFilter === '全部'
                      ? 'bg-indigo-500 text-white'
                      : 'bg-white/10 text-white/60 hover:bg-white/20'
                  }`}
                >
                  全部
                </button>
                {categories.map(category => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategoryFilter(category)}
                    className={`px-4 py-2 rounded-full text-sm transition-all ${
                      selectedCategoryFilter === category
                        ? 'bg-indigo-500 text-white'
                        : 'bg-white/10 text-white/60 hover:bg-white/20'
                    }`}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>

            {/* Tag Filter */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Filter size={16} className="text-white/60" />
                <span className="text-white/60 text-sm">标签</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSelectedTagFilter('全部')}
                  className={`px-4 py-2 rounded-full text-sm transition-all ${
                    selectedTagFilter === '全部'
                      ? 'bg-purple-500 text-white'
                      : 'bg-white/10 text-white/60 hover:bg-white/20'
                  }`}
                >
                  全部
                </button>
                {allTags.map(tag => (
                  <button
                    key={tag}
                    onClick={() => setSelectedTagFilter(tag)}
                    className={`px-4 py-2 rounded-full text-sm transition-all ${
                      selectedTagFilter === tag
                        ? 'bg-purple-500 text-white'
                        : 'bg-white/10 text-white/60 hover:bg-white/20'
                    }`}
                  >
                    #{tag}
                  </button>
                ))}
              </div>
            </div>
          </GlassCard>
        </div>
      </section>

      {/* Posts Grid */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-6xl mx-auto">
          {filteredPosts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredPosts.map((post, index) => (
                <PostCard key={post.slug} post={post} index={index} />
              ))}
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-20"
            >
              <p className="text-white/60 text-lg">没有找到匹配的文章</p>
            </motion.div>
          )}
        </div>
      </section>

      {/* Footer */}
      <Footer />
    </div>
  );
}
