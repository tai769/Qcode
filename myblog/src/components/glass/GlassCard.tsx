'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { 
  glassColors, 
  gradientColors, 
  hoverAnimations,
  tapAnimations
} from '@/constants';
import { GlassCardProps } from '@/types';
import { useResponsiveGlassEffect } from '@/hooks';

/**
 * 增强版玻璃态卡片组件
 * 
 * 特性：
 * - 多层 backdrop-filter 增强模糊效果
 * - 动态模糊度（可配置）
 * - 多层发光效果
 * - 渐变边框
 * - 响应式性能优化
 * - 主题化配置
 */
export default function GlassCard({
  children,
  className = '',
  hover = true,
  glow = true,
  blurStrength = 16,
  borderOpacity = 0.2,
  rounded = '2xl',
  ...props
}: GlassCardProps) {
  // 响应式玻璃态效果
  const { style: glassStyle, setIsHovered } = useResponsiveGlassEffect({
    blurStrength,
    opacity: 0.1,
    borderOpacity,
    enableGlow: glow,
  });

  // 圆角样式映射
  const roundedClasses = {
    none: 'rounded-none',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    xl: 'rounded-xl',
    '2xl': 'rounded-2xl',
    full: 'rounded-full',
  };

  // 基础样式
  const baseClassName = cn(
    'relative overflow-hidden',
    'bg-white/10',
    `backdrop-blur-${Math.min(24, blurStrength)}`,
    `border border-white/${Math.round(borderOpacity * 100)}`,
    roundedClasses[rounded],
    'shadow-2xl',
    className
  );

  // 悬停动画配置
  const hoverAnimation = hover ? {
    scale: 1.02,
    borderColor: 'rgba(168, 85, 247, 0.5)',
    transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] },
  } : undefined;

  // 点击动画配置
  const tapAnimation = hover ? {
    scale: 0.98,
  } : undefined;

  return (
    <motion.div
      className={baseClassName}
      style={glassStyle}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      whileHover={hoverAnimation}
      whileTap={tapAnimation}
      onHoverStart={() => hover && setIsHovered(true)}
      onHoverEnd={() => hover && setIsHovered(false)}
      {...props}
    >
      {/* 第一层：基础玻璃效果 */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
        }}
      />

      {/* 第二层：渐变边框 */}
      {hover && (
        <motion.div
          className={cn('absolute inset-0', roundedClasses[rounded])}
          initial={{ opacity: 0 }}
          whileHover={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          style={{
            background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(59, 130, 246, 0.15), rgba(6, 182, 212, 0.15))',
            padding: '1px',
          }}
        />
      )}

      {/* 第三层：发光效果 */}
      {glow && hover && (
        <motion.div
          className={cn('absolute inset-0', roundedClasses[rounded])}
          initial={{ opacity: 0, scale: 0.95 }}
          whileHover={{ 
            opacity: 1, 
            scale: 1.05,
            transition: { duration: 0.4 }
          }}
          style={{
            background: 'radial-gradient(circle at center, rgba(168, 85, 247, 0.2) 0%, transparent 70%)',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* 第四层：扫描线效果 */}
      {glow && hover && (
        <motion.div
          className={cn('absolute inset-0 overflow-hidden', roundedClasses[rounded])}
          initial={{ opacity: 0 }}
          whileHover={{ opacity: 1 }}
          style={{ pointerEvents: 'none' }}
        >
          <motion.div
            className="w-full h-1"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.3), transparent)',
            }}
            initial={{ y: -10 }}
            whileHover={{ 
              y: ['100%', '-10%'],
              transition: { 
                duration: 2, 
                repeat: Infinity,
                ease: 'linear'
              }
            }}
          />
        </motion.div>
      )}

      {/* 内容容器 */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
}
