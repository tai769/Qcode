/**
 * 组件类型定义
 * 统一管理组件的 Props 类型
 */

import { ReactNode, HTMLAttributes, ButtonHTMLAttributes, AnchorHTMLAttributes } from 'react';
import { MotionProps } from 'framer-motion';

// === 基础组件类型 ===

/**
 * 玻璃态卡片组件 Props
 */
export interface GlassCardProps {
  children: ReactNode;
  hover?: boolean;
  glow?: boolean;
  blurStrength?: number;
  borderOpacity?: number;
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  className?: string;
}

/**
 * 按钮组件 Props
 */
export interface ButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
}

/**
 * 导航链接组件 Props
 */
export interface NavLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  children: ReactNode;
  href: string;
  active?: boolean;
  disabled?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
}

// === 3D 组件类型 ===

/**
 * 3D 交互配置
 */
export interface ThreeInteractionConfig {
  enabled?: boolean;
  smoothing?: number;
  influenceRadius?: number;
  attractionStrength?: number;
}

/**
 * 粒子场配置
 */
export interface ParticleFieldConfig {
  particleCount?: number;
  particleSize?: number;
  spread?: number;
  colorRange?: {
    r: { min: number; max: number };
    g: { min: number; max: number };
    b: { min: number; max: number };
  };
  enableMouseInteraction?: boolean;
}

/**
 * 流体波浪配置
 */
export interface FluidWaveConfig {
  width?: number;
  height?: number;
  segments?: number;
  waveSpeed?: number;
  waveAmplitude?: number;
  color?: string;
  wireframe?: boolean;
}

/**
 * 发光球体配置
 */
export interface GlowOrbConfig {
  radius?: number;
  color?: string;
  intensity?: number;
  pulseEnabled?: boolean;
  pulseSpeed?: number;
  pulseRange?: { min: number; max: number };
}

// === 动画组件类型 ===

/**
 * 页面过渡 Props
 */
export interface PageTransitionProps {
  children: ReactNode;
  variant?: 'fade' | 'slideUp' | 'slideDown' | 'scaleIn';
  duration?: number;
}

/**
 * 滚动显示 Props
 */
export interface ScrollRevealProps extends MotionProps {
  children: ReactNode;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right';
  distance?: number;
  threshold?: number;
  triggerOnce?: boolean;
}

/**
 * 滚动进度条 Props
 */
export interface ScrollProgressProps {
  position?: 'top' | 'bottom';
  height?: number;
  color?: string;
  rounded?: boolean;
  className?: string;
}

// === 布局组件类型 ===

/**
 * 容器组件 Props
 */
export interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  centered?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

/**
 * 网格组件 Props
 */
export interface GridProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  cols?: number | 'responsive';
  gap?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

/**
 * 分隔线组件 Props
 */
export interface DividerProps extends HTMLAttributes<HTMLHRElement> {
  variant?: 'solid' | 'dashed' | 'dotted';
  color?: string;
  thickness?: number;
  className?: string;
}

// === 表单组件类型 ===

/**
 * 输入框组件 Props
 */
export interface InputProps extends HTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  disabled?: boolean;
  required?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
}

/**
 * 选择框组件 Props
 */
export interface SelectProps extends HTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  disabled?: boolean;
  required?: boolean;
  options: Array<{ value: string; label: string }>;
  className?: string;
}

// === 文章组件类型 ===

/**
 * 文章卡片 Props
 */
export interface ArticleCardProps {
  title: string;
  excerpt: string;
  date: string;
  slug: string;
  tags: string[];
  coverImage?: string;
  className?: string;
}

/**
 * 文章目录项 Props
 */
export interface TocItemProps {
  title: string;
  href: string;
  level: number;
  active?: boolean;
}

/**
 * 文章目录 Props
 */
export interface TableOfContentsProps {
  items: TocItemProps[];
  currentSection?: string;
  className?: string;
}

// === 社交组件类型 ===

/**
 * 社交链接配置
 */
export interface SocialLink {
  name: string;
  url: string;
  icon: ReactNode;
  color?: string;
}

/**
 * 社交链接列表 Props
 */
export interface SocialLinksProps {
  links: SocialLink[];
  variant?: 'icon' | 'card' | 'pill';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

// === 3D 背景组件类型 ===

/**
 * 3D 背景配置
 */
export interface ThreeBackgroundConfig {
  enableParticles?: boolean;
  enableFluidWave?: boolean;
  enableGlowOrb?: boolean;
  particleConfig?: ParticleFieldConfig;
  waveConfig?: FluidWaveConfig;
  orbConfig?: GlowOrbConfig;
}

// === 工具类型 ===

/**
 * 组件变体类型
 */
export type ComponentVariant = 'default' | 'primary' | 'secondary' | 'ghost' | 'outline';

/**
 * 尺寸类型
 */
export type ComponentSize = 'sm' | 'md' | 'lg' | 'xl';

/**
 * 颜色主题类型
 */
export type ColorTheme = 'purple' | 'blue' | 'cyan' | 'pink' | 'green';

/**
 * 圆角类型
 */
export type RoundedType = 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';

/**
 * 间距类型
 */
export type SpacingType = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
