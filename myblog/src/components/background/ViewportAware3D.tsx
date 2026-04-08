'use client';

import { useRef, useEffect, useState } from 'react';
import { useInView } from 'framer-motion';

interface ViewportAware3DProps {
  children: React.ReactNode;
  enableVisibilityCheck?: boolean;
  renderWhenInvisible?: boolean;
  threshold?: number;
}

/**
 * 视口感知 3D 组件
 * 
 * 用途：当 3D 场景不在视口内时暂停渲染，节省性能
 * 
 * 特性：
 * - 视口检测
 * - 自动暂停/恢复
 * - 可配置阈值
 * - 性能监控
 */
export function ViewportAware3D({
  children,
  enableVisibilityCheck = true,
  renderWhenInvisible = false,
  threshold = 0.1,
}: ViewportAware3DProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [shouldRender, setShouldRender] = useState(renderWhenInvisible);
  
  const isInView = useInView(ref, {
    amount: threshold,
    margin: '-100px',
  });

  useEffect(() => {
    if (!enableVisibilityCheck) {
      setShouldRender(true);
      return;
    }

    if (isInView) {
      // 进入视口，立即渲染
      setShouldRender(true);
    } else if (!renderWhenInvisible) {
      // 离开视口且不渲染时，延迟卸载
      const timer = setTimeout(() => {
        setShouldRender(false);
      }, 1000); // 1秒延迟，避免频繁切换
      
      return () => clearTimeout(timer);
    }
  }, [isInView, enableVisibilityCheck, renderWhenInvisible]);

  return (
    <div ref={ref} className="relative">
      {shouldRender ? children : null}
    </div>
  );
}

/**
 * 3D 性能监控 Hook
 * 
 * 用途：监控 3D 场景渲染性能，自动降低质量
 */
export function use3DPerformanceMonitor() {
  const frameTimeRef = useRef<number[]>([]);
  const [quality, setQuality] = useState<'high' | 'medium' | 'low'>('high');
  
  useEffect(() => {
    let animationFrameId: number;
    let lastTime = performance.now();
    
    const measureFrame = (currentTime: number) => {
      const frameTime = currentTime - lastTime;
      lastTime = currentTime;
      
      // 记录最近 60 帧的时间
      frameTimeRef.current = [...frameTimeRef.current.slice(-59), frameTime];
      
      // 每 60 帧检查一次
      if (frameTimeRef.current.length >= 60) {
        const avgFrameTime = frameTimeRef.current.reduce((a, b) => a + b, 0) / 60;
        const fps = 1000 / avgFrameTime;
        
        // 根据帧率调整质量
        if (fps < 30) {
          setQuality('low');
        } else if (fps < 50) {
          setQuality('medium');
        } else {
          setQuality('high');
        }
      }
      
      animationFrameId = requestAnimationFrame(measureFrame);
    };
    
    animationFrameId = requestAnimationFrame(measureFrame);
    
    return () => cancelAnimationFrame(animationFrameId);
  }, []);
  
  return quality;
}

/**
 * 获取质量配置
 */
export function getQualityConfig(quality: 'high' | 'medium' | 'low') {
  const configs = {
    high: {
      particleCount: [3000, 4000, 5000],
      segments: 64,
      dpr: 2,
      antialias: true,
      enableGlow: true,
    },
    medium: {
      particleCount: [2000, 3000, 4000],
      segments: 48,
      dpr: 1.5,
      antialias: true,
      enableGlow: true,
    },
    low: {
      particleCount: [1000, 1500, 2000],
      segments: 32,
      dpr: 1,
      antialias: false,
      enableGlow: false,
    },
  };
  
  return configs[quality];
}
