'use client';

import { motion, MotionProps } from 'framer-motion';
import { ReactNode } from 'react';
import { easings } from '@/constants';

interface ScrollRevealProps extends MotionProps {
  children: ReactNode;
  delay?: number;
  staggerDelay?: number; // 子元素交错延迟
  direction?: 'up' | 'down' | 'left' | 'right' | 'scale' | 'fade';
  distance?: number;
  threshold?: number;
  triggerOnce?: boolean;
  duration?: number;
  easing?: [number, number, number, number];
  blur?: boolean; // 是否添加模糊效果
}

const variants = {
  up: {
    hidden: { opacity: 0, y: 60 },
    visible: { opacity: 1, y: 0 },
  },
  down: {
    hidden: { opacity: 0, y: -60 },
    visible: { opacity: 1, y: 0 },
  },
  left: {
    hidden: { opacity: 0, x: -60 },
    visible: { opacity: 1, x: 0 },
  },
  right: {
    hidden: { opacity: 0, x: 60 },
    visible: { opacity: 1, x: 0 },
  },
  scale: {
    hidden: { opacity: 0, scale: 0.9 },
    visible: { opacity: 1, scale: 1 },
  },
  fade: {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  },
};

export default function ScrollReveal({
  children,
  delay = 0,
  staggerDelay,
  direction = 'up',
  distance = 60,
  threshold = 0.1,
  triggerOnce = true,
  duration = 0.6,
  easing = easings.smooth,
  blur = false,
  ...motionProps
}: ScrollRevealProps) {
  // 动态生成变体
  const selectedVariants = {
    hidden: {
      opacity: 0,
      ...(direction === 'up' && { y: distance }),
      ...(direction === 'down' && { y: -distance }),
      ...(direction === 'left' && { x: -distance }),
      ...(direction === 'right' && { x: distance }),
      ...(direction === 'scale' && { scale: 0.9 }),
      ...(blur && { filter: 'blur(10px)' }),
    },
    visible: {
      opacity: 1,
      y: 0,
      x: 0,
      scale: 1,
      ...(blur && { filter: 'blur(0px)' }),
    },
  };

  const transition = {
    duration,
    delay,
    ease: easing,
    staggerChildren: staggerDelay,
  };

  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: triggerOnce, amount: threshold, margin: '-100px' }}
      variants={selectedVariants}
      transition={transition}
      {...motionProps}
    >
      {children}
    </motion.div>
  );
}

/**
 * 组合动画容器
 * 用于包含多个子元素，实现交错动画
 */
export function StaggerContainer({
  children,
  staggerDelay = 0.1,
  delay = 0,
}: {
  children: ReactNode;
  staggerDelay?: number;
  delay?: number;
}) {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-100px' }}
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: staggerDelay,
            delayChildren: delay,
          },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

/**
 * 交错动画子元素
 */
export function StaggerItem({
  children,
  direction = 'up',
  distance = 30,
  delay = 0,
}: {
  children: ReactNode;
  direction?: 'up' | 'down' | 'left' | 'right' | 'scale';
  distance?: number;
  delay?: number;
}) {
  const variants = {
    hidden: {
      opacity: 0,
      ...(direction === 'up' && { y: distance }),
      ...(direction === 'down' && { y: -distance }),
      ...(direction === 'left' && { x: -distance }),
      ...(direction === 'right' && { x: distance }),
      ...(direction === 'scale' && { scale: 0.9 }),
    },
    visible: {
      opacity: 1,
      y: 0,
      x: 0,
      scale: 1,
    },
  };

  return (
    <motion.div
      variants={variants}
      transition={{ duration: 0.5, delay, ease: easings.smooth }}
    >
      {children}
    </motion.div>
  );
}
