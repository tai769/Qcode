'use client';

import { Suspense, lazy, ComponentType } from 'react';
import { motion } from 'framer-motion';

interface LazyComponentProps {
  fallback?: React.ReactNode;
  delay?: number;
}

/**
 * 懒加载高阶组件
 * 
 * 用途：延迟加载非关键组件，减少初始 bundle 大小
 * 
 * 特性：
 * - 自定义 fallback
 * - 延迟加载选项
 * - 自动处理 Suspense
 */
export function createLazyComponent<T extends object>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  options: LazyComponentProps = {}
) {
  const LazyComponent = lazy(importFn);
  
  return function LazyWrapper(props: T) {
    const { fallback, delay } = options;
    
    // 默认 fallback
    const defaultFallback = (
      <motion.div
        className="w-full h-full flex items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <div className="w-12 h-12 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </motion.div>
    );
    
    return (
      <Suspense fallback={fallback || defaultFallback}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}

/**
 * 预加载组件
 * 
 * 用途：在空闲时预加载组件，提升后续导航体验
 */
export function preloadComponent(importFn: () => Promise<any>) {
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    (window as any).requestIdleCallback(() => {
      importFn();
    }, { timeout: 2000 });
  } else {
    // 浏览器不支持 requestIdleCallback，使用 setTimeout
    setTimeout(() => {
      importFn();
    }, 2000);
  }
}

/**
 * 视口内触发加载的组件
 * 
 * 用途：当组件进入视口时才加载，提升性能
 */
'use client';

import { useState, useRef, useEffect } from 'react';
import { useInView } from 'framer-motion';

interface ViewportLazyProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  threshold?: number;
  margin?: string;
}

export function ViewportLazy({
  children,
  fallback,
  threshold = 0.1,
  margin = '-100px',
}: ViewportLazyProps) {
  const [isInView, setIsInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  
  const inView = useInView(ref, {
    amount: threshold,
    margin,
    once: true,
  });
  
  useEffect(() => {
    if (inView) {
      setIsInView(true);
    }
  }, [inView]);
  
  return (
    <div ref={ref} style={{ minHeight: '100px' }}>
      {isInView ? children : fallback}
    </div>
  );
}
