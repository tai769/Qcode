'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';

interface BackButtonProps {
  href?: string;
  label?: string;
}

export default function BackButton({ href = '/posts', label = '返回文章列表' }: BackButtonProps) {
  return (
    <Link href={href}>
      <motion.button
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        whileHover={{ x: -5 }}
        whileTap={{ scale: 0.95 }}
        className="glass px-5 py-3 rounded-full flex items-center gap-2 text-white/80 hover:text-white transition-all duration-300 mb-6"
      >
        <ArrowLeft size={18} />
        <span className="text-sm font-medium">{label}</span>
      </motion.button>
    </Link>
  );
}
