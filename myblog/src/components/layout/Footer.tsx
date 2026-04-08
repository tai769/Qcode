'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Github, Twitter, Mail } from 'lucide-react';

const socialLinks = [
  { href: 'https://github.com', icon: Github, label: 'GitHub' },
  { href: 'https://twitter.com', icon: Twitter, label: 'Twitter' },
  { href: 'mailto:hello@example.com', icon: Mail, label: 'Email' },
];

export default function Footer() {
  return (
    <footer className="mt-20 px-4 md:px-8 py-8">
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="glass rounded-2xl p-8 max-w-6xl mx-auto"
      >
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-center md:text-left">
            <div className="text-2xl font-bold gradient-text mb-2">MyBlog</div>
            <p className="text-white/60 text-sm">
              使用 Next.js 14 + React Three Fiber 构建
            </p>
          </div>

          <div className="flex items-center gap-4">
            {socialLinks.map((link) => (
              <motion.a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                whileHover={{ scale: 1.2, rotate: 5 }}
                whileTap={{ scale: 0.9 }}
                className="w-10 h-10 glass rounded-full flex items-center justify-center text-white/80 hover:text-white transition-colors"
                aria-label={link.label}
              >
                <link.icon size={20} />
              </motion.a>
            ))}
          </div>

          <div className="text-white/60 text-sm text-center md:text-right">
            © 2024 MyBlog. All rights reserved.
          </div>
        </div>
      </motion.div>
    </footer>
  );
}
