'use client';

import { motion, AnimatePresence, Variants } from 'framer-motion';
import { usePathname } from 'next/navigation';
import { ReactNode } from 'react';
import { easings, pageTransitions, transitionConfigs } from '@/constants';

interface PageTransitionProps {
  children: ReactNode;
  variant?: 'fade' | 'slideUp' | 'slideDown' | 'scaleIn' | 'slideUpFade';
  customEasing?: [number, number, number, number];
  duration?: number;
}

// 扩展的页面变体
const extendedPageVariants: Record<string, Variants> = {
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  slideUp: {
    initial: { opacity: 0, y: 50, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -50, scale: 0.98 },
  },
  slideDown: {
    initial: { opacity: 0, y: -50, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: 50, scale: 0.98 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.9 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.9 },
  },
  slideUpFade: {
    initial: { opacity: 0, y: 20, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -20, scale: 0.98 },
  },
  // 新增变体
  zoomBlur: {
    initial: { opacity: 0, scale: 1.05, filter: 'blur(10px)' },
    animate: { opacity: 1, scale: 1, filter: 'blur(0px)' },
    exit: { opacity: 0, scale: 0.95, filter: 'blur(10px)' },
  },
  reveal: {
    initial: { opacity: 0, clipPath: 'inset(0 100% 0 0)' },
    animate: { opacity: 1, clipPath: 'inset(0 0% 0 0)' },
    exit: { opacity: 0, clipPath: 'inset(0 0 0 100%)' },
  },
};

export default function PageTransition({ 
  children, 
  variant = 'slideUpFade',
  customEasing,
  duration = 0.4
}: PageTransitionProps) {
  const pathname = usePathname();
  
  const transition = {
    type: 'tween' as const,
    ease: customEasing || easings.anticipate,
    duration,
  };

  const selectedVariants = extendedPageVariants[variant] || extendedPageVariants.slideUpFade;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        initial="initial"
        animate="animate"
        exit="exit"
        variants={selectedVariants}
        transition={transition}
        className="w-full"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
