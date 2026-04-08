/**
 * 玻璃态主题系统
 * 
 * 提供可配置的玻璃态主题，支持不同的颜色、透明度、模糊度等
 */

export interface GlassTheme {
  name: string;
  
  // 背景配置
  background: {
    opacity: number;
    color?: string;
    blurStrength: number;
  };
  
  // 边框配置
  border: {
    opacity: number;
    color?: string;
    width: number;
  };
  
  // 发光配置
  glow: {
    enabled: boolean;
    color: string;
    intensity: number;
  };
  
  // 阴影配置
  shadow: {
    enabled: boolean;
    color: string;
    blur: number;
    spread: number;
  };
  
  // 动画配置
  animation: {
    transitionDuration: number;
    hoverScale: number;
  };
}

/**
 * 预定义主题
 */
export const glassThemes: Record<string, GlassTheme> = {
  // 紫色主题（默认）
  purple: {
    name: 'purple',
    background: {
      opacity: 0.1,
      blurStrength: 16,
    },
    border: {
      opacity: 0.2,
      width: 1,
    },
    glow: {
      enabled: true,
      color: 'rgba(168, 85, 247, 0.4)',
      intensity: 1,
    },
    shadow: {
      enabled: true,
      color: 'rgba(168, 85, 247, 0.2)',
      blur: 30,
      spread: 0,
    },
    animation: {
      transitionDuration: 0.3,
      hoverScale: 1.02,
    },
  },
  
  // 蓝色主题
  blue: {
    name: 'blue',
    background: {
      opacity: 0.1,
      blurStrength: 16,
    },
    border: {
      opacity: 0.2,
      width: 1,
    },
    glow: {
      enabled: true,
      color: 'rgba(59, 130, 246, 0.4)',
      intensity: 1,
    },
    shadow: {
      enabled: true,
      color: 'rgba(59, 130, 246, 0.2)',
      blur: 30,
      spread: 0,
    },
    animation: {
      transitionDuration: 0.3,
      hoverScale: 1.02,
    },
  },
  
  // 青色主题
  cyan: {
    name: 'cyan',
    background: {
      opacity: 0.1,
      blurStrength: 16,
    },
    border: {
      opacity: 0.2,
      width: 1,
    },
    glow: {
      enabled: true,
      color: 'rgba(6, 182, 212, 0.4)',
      intensity: 1,
    },
    shadow: {
      enabled: true,
      color: 'rgba(6, 182, 212, 0.2)',
      blur: 30,
      spread: 0,
    },
    animation: {
      transitionDuration: 0.3,
      hoverScale: 1.02,
    },
  },
  
  // 极简主题（无发光，低透明度）
  minimal: {
    name: 'minimal',
    background: {
      opacity: 0.05,
      blurStrength: 8,
    },
    border: {
      opacity: 0.1,
      width: 1,
    },
    glow: {
      enabled: false,
      color: 'transparent',
      intensity: 0,
    },
    shadow: {
      enabled: false,
      color: 'transparent',
      blur: 0,
      spread: 0,
    },
    animation: {
      transitionDuration: 0.2,
      hoverScale: 1.01,
    },
  },
  
  // 强烈主题（高透明度，强发光）
  intense: {
    name: 'intense',
    background: {
      opacity: 0.15,
      blurStrength: 24,
    },
    border: {
      opacity: 0.3,
      width: 2,
    },
    glow: {
      enabled: true,
      color: 'rgba(168, 85, 247, 0.6)',
      intensity: 1.5,
    },
    shadow: {
      enabled: true,
      color: 'rgba(168, 85, 247, 0.3)',
      blur: 40,
      spread: 5,
    },
    animation: {
      transitionDuration: 0.4,
      hoverScale: 1.03,
    },
  },
};

/**
 * 获取主题
 */
export function getGlassTheme(themeName: string): GlassTheme {
  return glassThemes[themeName] || glassThemes.purple;
}

/**
 * 合并主题配置
 */
export function mergeTheme(
  baseTheme: GlassTheme,
  overrides: Partial<GlassTheme>
): GlassTheme {
  return {
    ...baseTheme,
    ...overrides,
    background: { ...baseTheme.background, ...overrides.background },
    border: { ...baseTheme.border, ...overrides.border },
    glow: { ...baseTheme.glow, ...overrides.glow },
    shadow: { ...baseTheme.shadow, ...overrides.shadow },
    animation: { ...baseTheme.animation, ...overrides.animation },
  };
}

/**
 * 将主题转换为 CSS 样式
 */
export function themeToStyles(theme: GlassTheme) {
  const styles: React.CSSProperties = {};
  
  // 背景样式
  styles.background = theme.background.color 
    ? `rgba(${hexToRgb(theme.background.color)}, ${theme.background.opacity})`
    : `rgba(255, 255, 255, ${theme.background.opacity})`;
  
  styles.backdropFilter = `blur(${theme.background.blurStrength}px)`;
  
  // 边框样式
  styles.border = `${theme.border.width}px solid ${theme.border.color || `rgba(255, 255, 255, ${theme.border.opacity})`}`;
  
  // 阴影样式
  if (theme.shadow.enabled) {
    styles.boxShadow = `0 ${theme.shadow.spread}px ${theme.shadow.blur}px ${theme.shadow.color}`;
  }
  
  return styles;
}

/**
 * 将主题转换为 Tailwind 类名
 */
export function themeToClasses(theme: GlassTheme): string {
  const classes: string[] = [];
  
  // 背景类
  classes.push(`bg-white/${Math.round(theme.background.opacity * 100)}`);
  classes.push(`backdrop-blur-${theme.background.blurStrength}`);
  
  // 边框类
  classes.push(`border border-white/${Math.round(theme.border.opacity * 100)}`);
  
  // 发光类
  if (theme.glow.enabled) {
    classes.push(`shadow-${theme.name === 'purple' ? 'purple' : theme.name === 'blue' ? 'blue' : 'cyan'}-500/25`);
  }
  
  return classes.join(' ');
}

/**
 * 辅助函数：Hex 转 RGB
 */
function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
    : '255, 255, 255';
}
