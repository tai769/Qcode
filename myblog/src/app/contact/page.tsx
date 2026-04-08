'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Github, Twitter, Mail, MapPin, Send } from 'lucide-react';
import GlassCard from '@/components/glass/GlassCard';
import Footer from '@/components/layout/Footer';

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    // Simulate form submission
    await new Promise(resolve => setTimeout(resolve, 2000));
    alert('消息已发送！我会尽快回复你。');
    setIsSubmitting(false);
    setFormData({ name: '', email: '', subject: '', message: '' });
  };

  const contactInfo = [
    {
      icon: Mail,
      label: 'Email',
      value: 'hello@example.com',
      href: 'mailto:hello@example.com',
    },
    {
      icon: Github,
      label: 'GitHub',
      value: '@johndoe',
      href: 'https://github.com',
    },
    {
      icon: Twitter,
      label: 'Twitter',
      value: '@johndoe',
      href: 'https://twitter.com',
    },
    {
      icon: MapPin,
      label: 'Location',
      value: '中国，北京',
      href: null,
    },
  ];

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
            <span className="gradient-text">联系我</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-white/60 text-lg"
          >
            有问题或合作意向？欢迎随时联系！
          </motion.p>
        </div>
      </section>

      {/* Contact Info */}
      <section className="px-4 md:px-8 py-8">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
            {contactInfo.map((info, index) => (
              <GlassCard key={index} hover={!!info.href}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="text-center"
                >
                  <info.icon className="mx-auto mb-3 text-indigo-400" size={32} />
                  <div className="text-white/60 text-sm mb-1">{info.label}</div>
                  {info.href ? (
                    <a
                      href={info.href}
                      target={info.href.startsWith('http') ? '_blank' : undefined}
                      rel={info.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                      className="text-white font-medium hover:text-indigo-400 transition-colors"
                    >
                      {info.value}
                    </a>
                  ) : (
                    <div className="text-white font-medium">{info.value}</div>
                  )}
                </motion.div>
              </GlassCard>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Form */}
      <section className="px-4 md:px-8 py-8">
        <div className="max-w-2xl mx-auto">
          <GlassCard>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 className="text-2xl font-bold text-white mb-6">发送消息</h2>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label htmlFor="name" className="block text-white/80 mb-2">
                    姓名
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-indigo-500/50 transition-colors"
                    placeholder="你的姓名"
                  />
                </div>

                <div>
                  <label htmlFor="email" className="block text-white/80 mb-2">
                    邮箱
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-indigo-500/50 transition-colors"
                    placeholder="your@email.com"
                  />
                </div>

                <div>
                  <label htmlFor="subject" className="block text-white/80 mb-2">
                    主题
                  </label>
                  <input
                    type="text"
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-indigo-500/50 transition-colors"
                    placeholder="消息主题"
                  />
                </div>

                <div>
                  <label htmlFor="message" className="block text-white/80 mb-2">
                    消息
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    required
                    rows={6}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-indigo-500/50 transition-colors resize-none"
                    placeholder="你的消息内容..."
                  />
                </div>

                <motion.button
                  type="submit"
                  disabled={isSubmitting}
                  whileHover={{ scale: isSubmitting ? 1 : 1.05 }}
                  whileTap={{ scale: isSubmitting ? 1 : 0.95 }}
                  className="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg font-medium text-white flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <span>发送中...</span>
                    </>
                  ) : (
                    <>
                      <Send size={20} />
                      <span>发送消息</span>
                    </>
                  )}
                </motion.button>
              </form>
            </motion.div>
          </GlassCard>
        </div>
      </section>

      {/* Note */}
      <section className="px-4 md:px-8 py-12">
        <div className="max-w-2xl mx-auto text-center">
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-white/50 text-sm"
          >
            我通常会在 24 小时内回复。如果事情比较紧急，也可以通过邮件直接联系我。
          </motion.p>
        </div>
      </section>

      <Footer />
    </div>
  );
}
