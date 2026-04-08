/**
 * 颜色常量定义
 * 统一管理项目中使用的颜色值
 */

// === 渐变色 ===
export const gradientColors = {
  // 紫色系
  purple: {
    primary: '#a855f7',
    light: '#c084fc',
    dark: '#7c3aed',
    gradient: 'linear-gradient(135deg, #a855f7, #7c3aed)',
  },
  // 蓝色系
  blue: {
    primary: '#3b82f6',
    light: '#60a5fa',
    dark: '#2563eb',
    gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
  },
  // 青色系
  cyan: {
    primary: '#06b6d4',
    light: '#22d3ee',
    dark: '#0891b2',
    gradient: 'linear-gradient(135deg, #06b6d4, #0891b2)',
  },
  // 粉色系
  pink: {
    primary: '#ec4899',
    light: '#f472b6',
    dark: '#db2777',
    gradient: 'linear-gradient(135deg, #ec4899, #db2777)',
  },
} as const;

// === 玻璃态颜色 ===
export const glassColors = {
  background: 'rgba(255, 255, 255, 0.05)',
  backgroundHover: 'rgba(255, 255, 255, 0.08)',
  border: 'rgba(255, 255, 255, 0.1)',
  borderHover: 'rgba(255, 255, 255, 0.2)',
  glow: 'rgba(168, 85, 247, 0.2)',
  glowHover: 'rgba(168, 85, 247, 0.4)',
  shadow: 'rgba(0, 0, 0, 0.3)',
} as const;

// === 背景渐变 ===
export const backgroundGradients = {
  purpleToBlue: 'linear-gradient(135deg, #581c87, #1e3a8a)',
  darkPurple: 'linear-gradient(135deg, #2e1065, #1e1b4b)',
  midnight: 'linear-gradient(135deg, #0f172a, #1e1b4b)',
  aurora: 'linear-gradient(45deg, #a855f7, #3b82f6, #06b6d4)',
  
  // 渐变文本类
  textGradient: 'from-purple-400 via-cyan-400 to-amber-400',
  textGradientAlt: 'from-purple-400 via-pink-400 to-blue-400',
} as const;

// === 粒子颜色 ===
export const particleColors = {
  purple: new THREE.Color('#a855f7'),
  blue: new THREE.Color('#3b82f6'),
  cyan: new THREE.Color('#06b6d4'),
  
  // 渐变范围
  purpleToBlue: {
    r: { min: 0.3, max: 0.6 },
    g: { min: 0.2, max: 0.7 },
    b: { min: 0.6, max: 0.9 },
  },
} as const;

// === UI 颜色 ===
export const uiColors = {
  primary: '#a855f7',
  secondary: '#3b82f6',
  accent: '#06b6d4',
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444',
  
  // 文字颜色
  text: {
    primary: '#ffffff',
    secondary: 'rgba(255, 255, 255, 0.7)',
    muted: 'rgba(255, 255, 255, 0.5)',
    disabled: 'rgba(255, 255, 255, 0.3)',
  },
} as const;

// === Tailwind 颜色类 ===
export const tailwindColors = {
  glass: 'bg-white/10 backdrop-blur-xl border border-white/20',
  glassHover: 'hover:bg-white/15 hover:border-white/30',
  glowPurple: 'shadow-[0_0_30px_rgba(168,85,247,0.3)]',
  glowCyan: 'shadow-[0_0_30px_rgba(6,182,212,0.3)]',
} as const;

import * as THREE from 'three';
