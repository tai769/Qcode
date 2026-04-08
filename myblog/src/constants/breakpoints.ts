/**
 * 断点常量定义
 * 统一管理响应式断点
 */

// === 断点值 ===
export const breakpoints = {
  xs: 375,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

// === 断点查询字符串 ===
export const mediaQueries = {
  xs: `(min-width: ${breakpoints.xs}px)`,
  sm: `(min-width: ${breakpoints.sm}px)`,
  md: `(min-width: ${breakpoints.md}px)`,
  lg: `(min-width: ${breakpoints.lg}px)`,
  xl: `(min-width: ${breakpoints.xl}px)`,
  '2xl': `(min-width: ${breakpoints['2xl']}px)`,
  
  // 最大宽度
  maxXs: `(max-width: ${breakpoints.xs - 1}px)`,
  maxSm: `(max-width: ${breakpoints.sm - 1}px)`,
  maxMd: `(max-width: ${breakpoints.md - 1}px)`,
  maxLg: `(max-width: ${breakpoints.lg - 1}px)`,
  maxXl: `(max-width: ${breakpoints.xl - 1}px)`,
  
  // 范围
  smToMd: `(min-width: ${breakpoints.sm}px) and (max-width: ${breakpoints.md - 1}px)`,
  mdToLg: `(min-width: ${breakpoints.md}px) and (max-width: ${breakpoints.lg - 1}px)`,
  lgToXl: `(min-width: ${breakpoints.lg}px) and (max-width: ${breakpoints.xl - 1}px)`,
} as const;

// === Tailwind 断点类 ===
export const tailwindBreakpoints = {
  // Grid
  grid: {
    cols1: 'grid-cols-1',
    cols2Sm: 'sm:grid-cols-2',
    cols3Md: 'md:grid-cols-3',
    cols4Lg: 'lg:grid-cols-4',
  },
  // Flex
  flex: {
    colMobile: 'flex-col',
    rowDesktop: 'md:flex-row',
  },
  // Padding
  padding: {
    mobile: 'px-4 py-8',
    desktop: 'md:px-8 md:py-12',
  },
  // Text
  text: {
    headingMobile: 'text-4xl',
    headingDesktop: 'md:text-6xl',
  },
} as const;

// === 设备类型判断 ===
export const deviceTypes = {
  isMobile: () => typeof window !== 'undefined' && window.innerWidth < breakpoints.md,
  isTablet: () => {
    const w = typeof window !== 'undefined' ? window.innerWidth : 0;
    return w >= breakpoints.md && w < breakpoints.lg;
  },
  isDesktop: () => typeof window !== 'undefined' && window.innerWidth >= breakpoints.lg,
  isLargeScreen: () => typeof window !== 'undefined' && window.innerWidth >= breakpoints.xl,
} as const;

// === 性能优化参数 ===
export const performanceTuning = {
  // 移动端降低动画复杂度
  reducedMotion: {
    enabled: () => {
      if (typeof window === 'undefined') return false;
      return window.innerWidth < breakpoints.md;
    },
    // 降低粒子数量
    particleReduction: 0.5,
    // 降低模糊强度
    blurReduction: 0.5,
  },
  // 桌面端使用全特效
  fullEffects: {
    enabled: () => {
      if (typeof window === 'undefined') return false;
      return window.innerWidth >= breakpoints.lg;
    },
  },
} as const;
