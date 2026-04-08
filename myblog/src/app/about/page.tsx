'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { Github, Twitter, Mail, Code2, Heart, Zap } from 'lucide-react';
import GlassCard from '@/components/glass/GlassCard';
import Button from '@/components/ui/Button';
import Footer from '@/components/layout/Footer';

const skills = [
  { name: 'Next.js', level: 90 },
  { name: 'React', level: 95 },
  { name: 'TypeScript', level: 85 },
  { name: 'Three.js', level: 75 },
  { name: 'Framer Motion', level: 80 },
  { name: 'Tailwind CSS', level: 90 },
];

export default function AboutPage() {
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
            <span className="gradient-text">关于我</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-white/60 text-lg"
          >
            热爱技术与设计的开发者
          </motion.p>
        </div>
      </section>

      {/* Profile Card */}
      <section className="px-4 md:px-8 py-8">
        <div className="max-w-4xl mx-auto">
          <GlassCard>
            <div className="flex flex-col md:flex-row gap-8 items-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
                className="w-48 h-48 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center"
              >
                <span className="text-6xl font-bold text-white">JD</span>
              </motion.div>

              <motion.div
                initial={false}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
                className="flex-1"
              >
                <h2 className="text-3xl font-bold text-white mb-4">
                  John Doe
                </h2>
                <p className="text-white/70 mb-6 leading-relaxed">
                  我是一名全栈开发者，热衷于探索前沿技术和创建美观的用户体验。
                  擅长使用 React、Next.js 和现代前端技术栈构建高性能的 Web 应用。
                  相信技术可以改变世界，设计可以打动人心。
                </p>
                <div className="flex items-center gap-4">
                  <a
                    href="https://github.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-12 h-12 glass rounded-full flex items-center justify-center text-white/80 hover:text-white transition-all hover:scale-110"
                  >
                    <Github size={24} />
                  </a>
                  <a
                    href="https://twitter.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-12 h-12 glass rounded-full flex items-center justify-center text-white/80 hover:text-white transition-all hover:scale-110"
                  >
                    <Twitter size={24} />
                  </a>
                  <a
                    href="mailto:hello@example.com"
                    className="w-12 h-12 glass rounded-full flex items-center justify-center text-white/80 hover:text-white transition-all hover:scale-110"
                  >
                    <Mail size={24} />
                  </a>
                </div>
              </motion.div>
            </div>
          </GlassCard>
        </div>
      </section>

      {/* Stats */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <GlassCard>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5 }}
                className="text-center"
              >
                <Code2 className="mx-auto mb-4 text-indigo-400" size={48} />
                <div className="text-4xl font-bold text-white mb-2">3+</div>
                <div className="text-white/60">年开发经验</div>
              </motion.div>
            </GlassCard>

            <GlassCard>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="text-center"
              >
                <Heart className="mx-auto mb-4 text-pink-400" size={48} />
                <div className="text-4xl font-bold text-white mb-2">50+</div>
                <div className="text-white/60">完成项目</div>
              </motion.div>
            </GlassCard>

            <GlassCard>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="text-center"
              >
                <Zap className="mx-auto mb-4 text-yellow-400" size={48} />
                <div className="text-4xl font-bold text-white mb-2">100%</div>
                <div className="text-white/60">客户满意度</div>
              </motion.div>
            </GlassCard>
          </div>
        </div>
      </section>

      {/* Skills */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-4xl mx-auto">
          <GlassCard>
            <h3 className="text-2xl font-bold text-white mb-6">技能专长</h3>
            <div className="space-y-4">
              {skills.map((skill, index) => (
                <motion.div
                  key={skill.name}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <div className="flex justify-between mb-2">
                    <span className="text-white font-medium">{skill.name}</span>
                    <span className="text-white/60">{skill.level}%</span>
                  </div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${skill.level}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 1, delay: index * 0.1 + 0.3 }}
                      className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-4xl mx-auto text-center">
          <GlassCard>
            <h3 className="text-2xl font-bold text-white mb-4">
              有兴趣合作吗？
            </h3>
            <p className="text-white/60 mb-6">
              我随时准备接受新的挑战和机会。让我们一起创造些精彩的东西！
            </p>
            <Link href="/contact">
              <Button size="lg">
                联系我
              </Button>
            </Link>
          </GlassCard>
        </div>
      </section>

      <Footer />
    </div>
  );
}
