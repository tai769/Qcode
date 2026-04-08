/**
 * 动画常量定义
 * 统一管理 Framer Motion 动画参数
 */

// === 缓动函数 ===
export const easings = {
  // 平滑
  smooth: [0.22, 1, 0.36, 1],
  // 弹性
  bounce: [0.34, 1.56, 0.64, 1],
  // 预期
  anticipate: [0, 0, 0.58, 1],
  // 快速
  quick: [0.25, 0.46, 0.45, 0.94],
  // 慢速
  slow: [0.42, 0, 0.58, 1],
} as const;

// === 持续时间 ===
export const durations = {
  instant: 0.1,
  fast: 0.2,
  normal: 0.4,
  slow: 0.6,
  slower: 0.8,
} as const;

// === 页面过渡动画 ===
export const pageTransitions = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
  },
  slideDown: {
    initial: { opacity: 0, y: -20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.95 },
  },
  slideUpFade: {
    initial: { opacity: 0, y: 20, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -20, scale: 0.98 },
  },
} as const;

// === 悬停动画 ===
export const hoverAnimations = {
  // 缩放
  scale: {
    scale: 1.05,
    transition: { duration: durations.fast },
  },
  // 发光
  glow: {
    boxShadow: '0 0 30px rgba(168, 85, 247, 0.4)',
    transition: { duration: durations.fast },
  },
  // 边框高亮
  borderGlow: {
    borderColor: 'rgba(168, 85, 247, 0.6)',
    transition: { duration: durations.fast },
  },
  // 组合效果
  cardHover: {
    scale: 1.02,
    borderColor: 'rgba(168, 85, 247, 0.4)',
    boxShadow: '0 0 30px rgba(168, 85, 247, 0.2)',
    transition: { duration: durations.normal },
  },
} as const;

// === 点击动画 ===
export const tapAnimations = {
  // 按压缩放
  scale: {
    scale: 0.95,
    transition: { duration: durations.instant },
  },
  // 按压发光
  glow: {
    boxShadow: '0 0 40px rgba(168, 85, 247, 0.6)',
    transition: { duration: durations.instant },
  },
} as const;

// === 滚动触发动画 ===
export const scrollAnimations = {
  // 淡入
  fadeIn: {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  },
  // 上滑淡入
  slideUp: {
    hidden: { opacity: 0, y: 60 },
    visible: { opacity: 1, y: 0 },
  },
  // 下滑淡入
  slideDown: {
    hidden: { opacity: 0, y: -60 },
    visible: { opacity: 1, y: 0 },
  },
  // 左滑淡入
  slideLeft: {
    hidden: { opacity: 0, x: -60 },
    visible: { opacity: 1, x: 0 },
  },
  // 右滑淡入
  slideRight: {
    hidden: { opacity: 0, x: 60 },
    visible: { opacity: 1, x: 0 },
  },
  // 缩放淡入
  scaleIn: {
    hidden: { opacity: 0, scale: 0.9 },
    visible: { opacity: 1, scale: 1 },
  },
} as const;

// === 3D 动画 ===
export const animation3D = {
  // 旋转
  rotation: {
    speed: 0.05,
  },
  // 波动
  wave: {
    frequency: 0.5,
    amplitude: 0.3,
  },
  // 脉冲
  pulse: {
    min: 0.9,
    max: 1.1,
    speed: 2,
  },
} as const;

// === 过渡配置 ===
export const transitionConfigs = {
  // 页面过渡
  page: {
    type: 'tween' as const,
    ease: easings.anticipate,
    duration: durations.normal,
  },
  // 悬停过渡
  hover: {
    type: 'tween' as const,
    ease: easings.smooth,
    duration: durations.fast,
  },
  // 滚动过渡
  scroll: {
    duration: durations.slow,
    ease: easings.smooth,
  },
  // 3D 动画过渡
  threejs: {
    damping: 0.02,
    smoothing: 0.05,
  },
} as const;

// === Viewport 配置 ===
export const viewportConfigs = {
  // 滚动触发一次
  once: {
    once: true,
    margin: '-100px',
  },
  // 多次触发
  multiple: {
    once: false,
    margin: '-50px',
  },
  // 宽范围
  wide: {
    once: true,
    margin: '-200px',
  },
} as const;
