'use client';

import { motion } from 'framer-motion';
import { ReactNode, ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { ButtonProps, ComponentVariant, ComponentSize } from '@/types';

/**
 * 玻璃态按钮组件
 * 
 * 特性：
 * - 多种变体（primary/secondary/ghost/outline）
 * - 多种尺寸
 * - 悬浮发光效果
 * - 点击反馈
 * - 加载状态
 * - 图标支持
 */
export default function GlassButton({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  leftIcon,
  rightIcon,
  className = '',
  ...props
}: ButtonProps) {
  // 尺寸样式
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
    xl: 'px-8 py-4 text-xl',
  };

  // 变体样式
  const variantClasses = {
    primary: `
      bg-purple-500/20 backdrop-blur-md
      border border-purple-400/30
      text-purple-100
      hover:bg-purple-500/30 hover:border-purple-400/50
      hover:shadow-purple-500/25
    `,
    secondary: `
      bg-blue-500/20 backdrop-blur-md
      border border-blue-400/30
      text-blue-100
      hover:bg-blue-500/30 hover:border-blue-400/50
      hover:shadow-blue-500/25
    `,
    ghost: `
      bg-white/5 backdrop-blur-md
      border border-white/10
      text-white/70
      hover:bg-white/10 hover:border-white/20
      hover:text-white/90
    `,
    outline: `
      bg-transparent backdrop-blur-sm
      border border-purple-400/50
      text-purple-300
      hover:bg-purple-500/10 hover:border-purple-400/70
    `,
  };

  // 变体发光颜色
  const glowColors = {
    primary: 'rgba(168, 85, 247, 0.4)',
    secondary: 'rgba(59, 130, 246, 0.4)',
    ghost: 'rgba(255, 255, 255, 0.2)',
    outline: 'rgba(168, 85, 247, 0.3)',
  };

  const baseClassName = cn(
    // 基础样式
    'relative inline-flex items-center justify-center gap-2',
    'font-medium',
    'rounded-xl',
    'transition-all duration-300',
    'backdrop-contrast-100',
    
    // 尺寸和变体
    sizeClasses[size],
    variantClasses[variant],
    
    // 状态
    disabled && 'opacity-50 cursor-not-allowed',
    
    className
  );

  const hoverAnimation = !disabled && !loading ? {
    scale: 1.05,
    boxShadow: `0 0 20px ${glowColors[variant]}`,
    transition: { duration: 0.2, ease: [0.22, 1, 0.36, 1] },
  } : undefined;

  const tapAnimation = !disabled && !loading ? {
    scale: 0.95,
  } : undefined;

  return (
    <motion.button
      className={baseClassName}
      disabled={disabled || loading}
      whileHover={hoverAnimation}
      whileTap={tapAnimation}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      {...props}
    >
      {/* 加载状态 */}
      {loading && (
        <motion.div
          className="absolute inset-0 flex items-center justify-center bg-black/20 rounded-xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <motion.div
            className="w-5 h-5 border-2 border-current border-t-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          />
        </motion.div>
      )}

      {/* 左图标 */}
      {leftIcon && !loading && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          {leftIcon}
        </motion.span>
      )}

      {/* 内容 */}
      <span className={loading ? 'opacity-0' : ''}>
        {children}
      </span>

      {/* 右图标 */}
      {rightIcon && !loading && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          {rightIcon}
        </motion.span>
      )}

      {/* 发光效果 */}
      {!disabled && !loading && (
        <motion.div
          className="absolute inset-0 rounded-xl"
          initial={{ opacity: 0 }}
          whileHover={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          style={{
            background: `radial-gradient(circle at center, ${glowColors[variant]} 0%, transparent 70%)`,
            pointerEvents: 'none',
          }}
        />
      )}
    </motion.button>
  );
}
