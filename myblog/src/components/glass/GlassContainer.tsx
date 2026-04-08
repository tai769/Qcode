'use client';

import { ReactNode, HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { ContainerProps, SpacingType, RoundedType } from '@/types';
import { useResponsiveGlassEffect } from '@/hooks';

/**
 * 毛玻璃容器组件
 * 
 * 用途：包裹整个页面或大块内容，提供统一的玻璃态背景
 * 
 * 特性：
 * - 可配置内边距
 * - 可配置圆角
 * - 可配置最大宽度
 * - 响应式性能优化
 * - 居中对齐选项
 */
export default function GlassContainer({
  children,
  maxWidth = 'xl',
  centered = true,
  padding = 'md',
  className = '',
  ...props
}: ContainerProps) {
  // 响应式玻璃态效果
  const { style, isMobile } = useResponsiveGlassEffect({
    blurStrength: isMobile ? 8 : 16,
    opacity: 0.05,
    borderOpacity: 0.15,
    enableGlow: false,
  });

  // 最大宽度映射
  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    full: 'max-w-full',
  };

  // 内边距映射
  const paddingClasses = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6 md:p-8',
    lg: 'p-8 md:p-12',
    xl: 'p-12 md:p-16',
  };

  return (
    <div
      className={cn(
        // 基础玻璃态
        'relative',
        'bg-white/5',
        'backdrop-blur-sm',
        'border border-white/10',
        
        // 布局
        centered ? 'mx-auto' : '',
        maxWidthClasses[maxWidth],
        paddingClasses[padding],
        
        // 圆角
        'rounded-3xl',
        
        className
      )}
      style={style}
      {...props}
    >
      {children}
    </div>
  );
}
