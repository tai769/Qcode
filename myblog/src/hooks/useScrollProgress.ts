'use client';

import { useScroll, useSpring } from 'framer-motion';

interface UseScrollProgressOptions {
  stiffness?: number;
  damping?: number;
  restDelta?: number;
}

/**
 * 滚动进度 Hook
 * 返回标准化的滚动进度值（0-1）
 * 支持弹性动画，使进度条运动更流畅
 */
export function useScrollProgress(options: UseScrollProgressOptions = {}) {
  const {
    stiffness = 100,
    damping = 30,
    restDelta = 0.001,
  } = options;

  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness,
    damping,
    restDelta,
  });

  return scaleX;
}

/**
 * 方向性滚动 Hook
 * 返回滚动方向：'up' | 'down' | null
 */
export function useScrollDirection() {
  const lastScrollY = useRef(0);
  const direction = useRef<'up' | 'down' | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      if (currentScrollY > lastScrollY.current) {
        direction.current = 'down';
      } else if (currentScrollY < lastScrollY.current) {
        direction.current = 'up';
      }
      
      lastScrollY.current = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return direction.current;
}

import { useRef, useEffect } from 'react';
