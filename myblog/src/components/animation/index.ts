/**
 * 动画组件统一导出
 * 提供统一的导入入口，方便管理和使用
 */

// === 基础动画组件 ===
export { FadeIn } from './FadeIn'
export { SlideUp, SlideUpItem } from './SlideUp'
export { ScrollProgress } from './ScrollProgress'

// === 交互动画组件 ===
export { MagneticButton } from './MagneticButton'
export { MagneticCard } from './MagneticCard'

// === 视差效果组件 ===
export { Parallax, ParallaxLayer, SimpleParallax } from './Parallax'

// === 文本动画组件 ===
export { 
  Typewriter, 
  WordTypewriter, 
  BlinkingCursor 
} from './Typewriter'
