'use client';

import { useState, useEffect } from 'react';

interface UseGlassEffectOptions {
  blurStrength?: number;
  opacity?: number;
  borderOpacity?: number;
  enableGlow?: boolean;
  glowColor?: string;
}

/**
 * 玻璃态效果 Hook
 * 提供玻璃态卡片的动态样式参数
 */
export function useGlassEffect(options: UseGlassEffectOptions = {}) {
  const {
    blurStrength = 16,
    opacity = 0.1,
    borderOpacity = 0.2,
    enableGlow = true,
    glowColor = 'rgba(168, 85, 247, 0.2)',
  } = options;

  const [isHovered, setIsHovered] = useState(false);

  const baseStyle = {
    background: `rgba(255, 255, 255, ${opacity})`,
    backdropFilter: `blur(${blurStrength}px)`,
    border: `1px solid rgba(255, 255, 255, ${borderOpacity})`,
  };

  const hoverStyle = {
    ...baseStyle,
    background: `rgba(255, 255, 255, ${opacity + 0.03})`,
    border: `1px solid rgba(255, 255, 255, ${borderOpacity + 0.1})`,
    boxShadow: enableGlow
      ? `0 8px 32px rgba(0, 0, 0, 0.3), 0 0 20px ${glowColor}`
      : `0 8px 32px rgba(0, 0, 0, 0.3)`,
  };

  const computedStyle = isHovered ? hoverStyle : baseStyle;

  return {
    style: computedStyle,
    isHovered,
    setIsHovered,
    baseStyle,
    hoverStyle,
  };
}

/**
 * 响应式玻璃态效果 Hook
 * 根据屏幕尺寸调整玻璃态参数
 */
export function useResponsiveGlassEffect(options: UseGlassEffectOptions = {}) {
  const [isMobile, setIsMobile] = useState(false);
  const glassEffect = useGlassEffect(options);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 移动端降低模糊强度以提升性能
  const adjustedStyle = isMobile
    ? {
        ...glassEffect.style,
        backdropFilter: `blur(${Math.min(8, parseInt(glassEffect.style.backdropFilter.match(/\d+/)?.[0] || '8'))}px)`,
      }
    : glassEffect.style;

  return {
    ...glassEffect,
    style: adjustedStyle,
    isMobile,
  };
}
