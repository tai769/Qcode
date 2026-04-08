# 个人博客 UI 设计规范 - 增强版 v2.0

> **目标**: 打造极致视觉体验的玻璃态3D个人博客  
> **增强重点**: 色彩丰富度、玻璃态精致度、3D交互性、布局美学、微交互动画

---

## 增强概览

### v1.0 → v2.0 核心改进

| 维度 | v1.0 | v2.0 增强 |
|------|------|-----------|
| **色彩** | 3色渐变 | 7色光谱 + 动态色相偏移 |
| **玻璃态** | 单层毛玻璃 | 多层堆叠 + 辉光层次 |
| **3D背景** | 静态粒子 | 动态流体 + 鼠标力场 + 性能分级 |
| **布局** | 基础网格 | 呼吸式间距 + 视觉节奏 |
| **动画** | 基础过渡 | 物理弹簧 + 视差 + 弹性反馈 |

---

## 一、增强色彩系统

### 1.1 扩展色板 - 7色光谱

```css
/* 主光谱色 */
--spectrum-1: #6366f1;  /* Indigo - 深邃 */
--spectrum-2: #8b5cf6;  /* Violet - 神秘 */
--spectrum-3: #a855f7;  /* Purple - 华丽 */
--spectrum-4: #d946ef;  /* Fuchsia - 活力 */
--spectrum-5: #ec4899;  /* Pink - 温暖 */
--spectrum-6: #f43f5e;  /* Rose - 激情 */
--spectrum-7: #06b6d4;  /* Cyan - 清新 */

/* 辉光色 */
--glow-indigo: 0 0 30px rgba(99, 102, 241, 0.5);
--glow-purple: 0 0 30px rgba(168, 85, 247, 0.5);
--glow-cyan: 0 0 30px rgba(6, 182, 212, 0.5);
--glow-multi: 0 0 40px rgba(99, 102, 241, 0.3),
               0 0 60px rgba(168, 85, 247, 0.2),
               0 0 80px rgba(6, 182, 212, 0.1);
```

### 1.2 动态渐变系统

#### 流体渐变（动态色相偏移）
```css
/* 时间变量（JS更新） */
--hue-offset: 0deg;

/* 动态光谱渐变 */
.gradient-fluid {
  background: linear-gradient(
    calc(135deg + var(--hue-offset)), 
    var(--spectrum-1) 0%, 
    var(--spectrum-3) 25%, 
    var(--spectrum-5) 50%, 
    var(--spectrum-7) 75%, 
    var(--spectrum-1) 100%
  );
  animation: hue-rotate 20s linear infinite;
}

@keyframes hue-rotate {
  0% { --hue-offset: 0deg; }
  100% { --hue-offset: 360deg; }
}
```

#### 多层渐变叠加
```css
/* 深度渐变背景 */
.gradient-deep {
  background: 
    /* 底层：深色 */
    linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%),
    /* 中层：网格纹理 */
    radial-gradient(at 50% 50%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
    /* 顶层：光晕 */
    radial-gradient(at 0% 0%, rgba(168, 85, 247, 0.15) 0%, transparent 50%),
    radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.15) 0%, transparent 50%);
}

/* 扫描线效果 */
.gradient-scanline {
  background: repeating-linear-gradient(
    0deg,
    transparent 0px,
    transparent 2px,
    rgba(99, 102, 241, 0.02) 2px,
    rgba(99, 102, 241, 0.02) 4px
  );
}
```

---

## 二、精致玻璃态组件

### 2.1 多层毛玻璃架构

#### 三层玻璃效果
```css
.glass-card-enhanced {
  position: relative;
  
  /* 第一层：基础毛玻璃 */
  background: rgba(30, 41, 59, 0.4);
  backdrop-filter: blur(16px) saturate(120%);
  -webkit-backdrop-filter: blur(16px) saturate(120%);
  
  /* 第二层：内发光 */
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    inset 0 -1px 0 rgba(0, 0, 0, 0.1),
    0 8px 32px rgba(0, 0, 0, 0.3);
  
  /* 边框：多重渐变 */
  border: 1px solid;
  border-image: linear-gradient(
    135deg,
    rgba(99, 102, 241, 0.3) 0%,
    rgba(168, 85, 247, 0.5) 50%,
    rgba(6, 182, 212, 0.3) 100%
  ) 1;
}

/* 第三层：辉光装饰（伪元素） */
.glass-card-enhanced::before {
  content: '';
  position: absolute;
  inset: -2px;
  background: linear-gradient(
    135deg,
    rgba(99, 102, 241, 0.4),
    rgba(168, 85, 247, 0.6),
    rgba(6, 182, 212, 0.4)
  );
  border-radius: inherit;
  filter: blur(8px);
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: -1;
}

.glass-card-enhanced:hover::before {
  opacity: 1;
}
```

#### 堆叠式玻璃卡片
```tsx
// Tailwind 实现
<div className="group relative">
  {/* 外层辉光 */}
  <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/40 
                  via-purple-500/40 to-cyan-500/40 rounded-2xl blur-xl 
                  opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
  
  {/* 中层发光 */}
  <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/20 
                  via-purple-500/20 to-cyan-500/20 rounded-2xl blur-md 
                  opacity-50 group-hover:opacity-75 transition-opacity duration-300" />
  
  {/* 内层卡片 */}
  <div className="relative bg-slate-800/40 backdrop-blur-xl 
                  saturate-120 rounded-2xl p-6 
                  border border-white/10
                  shadow-[inset_0_1px_0_rgba(255,255,255,0.1),
                           inset_0_-1px_0_rgba(0,0,0,0.1),
                           0_8px_32px_rgba(0,0,0,0.3)]
                  hover:-translate-y-1 transition-transform duration-300">
    {children}
  </div>
</div>
```

### 2.2 发光增强效果。

#### 辉光层级系统
```css
/* 三级辉光强度 */
.glow-level-1 { box-shadow: 0 0 15px rgba(99, 102, 241, 0.3); }
.glow-level-2 { box-shadow: 0 0 25px rgba(168, 85, 247, 0.4); }
.glow-level-3 { box-shadow: 0 0 40px rgba(6, 182, 212, 0.5); }

/* 脉冲辉光动画 */
.glow-pulse {
  animation: glow-pulse 3s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% {
    box-shadow: 
      0 0 20px rgba(99, 102, 241, 0.4),
      0 0 40px rgba(168, 85, 247, 0.2);
  }
  50% {
    box-shadow: 
      0 0 30px rgba(168, 85, 247, 0.5),
      0 0 60px rgba(6, 182, 212, 0.3);
  }
}

/* 扫描辉光效果 */
.glow-scan {
  position: relative;
  overflow: hidden;
}

.glow-scan::after {
  content: '';
  position: absolute;
  top: -100%;
  left: -100%;
  width: 300%;
  height: 300%;
  background: conic-gradient(
    from 0deg at 50% 50%,
    transparent 0deg,
    rgba(99, 102, 241, 0.3) 60deg,
    rgba(168, 85, 247, 0.5) 120deg,
    transparent 180deg
  );
  animation: rotate-scan 4s linear infinite;
}

@keyframes rotate-scan {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

#### 按钮发光增强
```tsx
// 辉光按钮
<motion.button
  className="relative px-6 py-3 rounded-xl 
             bg-gradient-to-r from-indigo-600/80 to-purple-600/80 
             backdrop-blur-md border border-white/20
             text-white font-medium overflow-hidden"
  whileHover={{ 
    scale: 1.05,
    boxShadow: "0 0 40px rgba(168, 85, 247, 0.6), 0 0 60px rgba(6, 182, 212, 0.4)"
  }}
  whileTap={{ scale: 0.95 }}
>
  {/* 内部光效 */}
  <div className="absolute inset-0 bg-gradient-to-r from-indigo-400/20 
                  via-purple-400/30 to-cyan-400/20 blur-sm" />
  
  {/* 扫描线 */}
  <div className="absolute inset-0 bg-gradient-to-b from-transparent 
                  via-white/10 to-transparent 
                  animate-[shimmer_2s_infinite]" />
  
  <span className="relative z-10">{children}</span>
</motion.button>
```

---

## 三、3D背景视觉增强

### 3.1 粒子系统增强

#### 分级粒子配置
```typescript
// 性能分级配置
const particleConfigs = {
  // 高性能模式（桌面）
  high: {
    count: 150,
    size: { min: 2, max: 6 },
    speed: { min: 0.5, max: 2 },
    colors: ['#6366f1', '#8b5cf6', '#a855f7', '#06b6d4'],
'connections': true,
    connectionsDistance: 120,
    mouseInfluence: 0.15,
  },
  
  // 标准模式（笔记本）
  medium: {
    count: 80,
    size: { min: 2, max: 5 },
    speed: { min: 0.3, max: 1.5 },
    colors: ['#6366f1', '#a855f7', '#06b6d4'],
    connections: true,
    connectionsDistance: 100,
    mouseInfluence: 0.1,
  },
  
  // 省电模式（移动端）
  low: {
    count: 30,
    size: { min: 1.5, max: 4 },
    speed: { min: 0.2, max: 1 },
    colors: ['#6366f1', '#a855f7'],
    connections: false,
    connectionsDistance: 0,
    mouseInfluence: 0.05,
  },
};

// 自动检测
const config = isMobile ? particleConfigs.low :
               isTablet ? particleConfigs.medium :
               particleConfigs.high;
```

#### 粒子交互增强
```typescript
// 鼠标力场效果
interface Particle {
  position: Vector3;
  velocity: Vector3;
  color: string;
  size: number;
}

// 更新粒子位置
function updateParticle(particle: Particle, mouse: Vector3, time: number) {
  // 基础流动
  particle.position.addScaledVector(particle.velocity, deltaTime);
  
  // 鼠标引力场
  const distanceToMouse = particle.position.distanceTo(mouse);
  if (distanceToMouse < 200) {
    const force = mouse
      .clone()
      .sub(particle.position)
      .normalize()
      .multiplyScalar(0.5 * (1 - distanceToMouse / 200));
    particle.position.add(force);
  }
  
  // 正弦波动（呼吸效果）
  particle.position.y += Math.sin(time * 2 + particle.position.x) * 0.02;
  
  // 边界循环
  if (particle.position.x > width) particle.position.x = 0;
  if (particle.position.x < 0) particle.position.x = width;
  if (particle.position.y > height) particle.position.y = 0;
  if (particle.position.y < 0) particle.position.y = height;
}
```

### 3.2 流体波浪增强

#### 多层波浪叠加
```typescript
// 三层波浪配置
const waveConfigs = [
  {
    amplitude: 1.2,    // 振幅
    frequency: 0.8,    // 频率
    speed: 1.0,        // 速度
    phase: 0,          // 相位
    color: '#6366f1',  // 颜色
    opacity: 0.3,      // 透明度
    points: 100,       // 顶点数
  },
  {
    amplitude: 0.8,
    frequency: 1.2,
    speed: 1.5,
    phase: Math.PI / 3,
    color: '#a855f7',
    opacity: 0.25,
    points: 150,
  },
  {
    amplitude: 0.5,
    frequency: 1.6,
    speed: 2.0,
    phase: Math.PI / 2,
    color: '#06b6d4',
    opacity: 0.2,
    points: 200,
  },
];

// 波浪更新
function updateWaves(time: number) {
  waveConfigs.forEach((wave, index) => {
    wave.phase = (time * wave.speed) % (Math.PI * 2);
    
    for (let i = 0; i < wave.points; i++) {
      const x = (i / wave.points) * width;
      const y = baseHeight + 
                Math.sin((x / width) * Math.PI * wave.frequency + wave.phase) * wave.amplitude;
      
      // 更新顶点
      wave.geometry.attributes.position.setXYZ(i, x, y, 0);
    }
    wave.geometry.attributes.position.needsUpdate = true;
  });
}
```

### 3.3 交互反馈增强

#### 鼠标追踪光晕
```typescript
// 光晕球体
const glowSphere = useRef<Mesh>(null);

// 更新光晕位置
useFrame((state, delta) => {
  if (glowSphere.current && mousePosition) {
    // 平滑跟随
    const target = new Vector3(mousePosition.x, mousePosition.y, 0);
    glowSphere.current.position.lerp(target, 0.1);
    
    // 脉冲效果
    const scale = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.2;
    glowSphere.current.scale.setScalar(scale);
  }
});

// 渲染光晕
<mesh ref={glowSphere}>
  <sphereGeometry args={[80, 32, 32]} />
  <meshBasicMaterial
    color="#6366f1"
    transparent
    opacity={0.1}
    blending={AdditiveBlending}
  />
</mesh>
```

---

## 四、页面布局美化

### 4.1 呼吸式间距系统

#### 模数化间距
```css
/* 基础间距单位：8px */
--space-unit: 8px;

/* 间距层级 */
--space-xs: calc(var(--space-unit) * 1);   /* 8px */
--space-sm: calc(var(--space-unit) * 2);   /* 16px */
--space-md: calc(var(--space-unit) * 3);   /* 24px */
--space-lg: calc(var(--space-unit) * 4);   /* 32px */
--space-xl: calc(var(--space-unit) * 6);   /* 48px */
--space-2xl: calc(var(--space-unit) * 8);  /* 64px */
--space-3xl: calc(var(--space-unit) * 12); /* 96px */

/* 呼吸式间距（视觉节奏） */
.layout-rhythm {
  padding: var(--space-lg);
  gap: var(--space-lg);
}

.hero-section {
  padding: var(--space-2xl) var(--space-lg);
}

.card-grid {
  gap: var(--space-md);
}
```

#### 比例间距系统
```typescript
// 黄金比例间距
const goldenRatio = 1.618;

const spacing = {
  base: 16,
  small: 16,
  medium: Math.round(16 * goldenRatio),  // 26
  large: Math.round(16 * goldenRatio * goldenRatio),  // 42
  xlarge: Math.round(16 * goldenRatio * goldenRatio * goldenRatio),  // 68
};
```

### 4.2 视觉节奏设计

#### 内容层级间距
```tsx
// 首页布局示例
<section className="min-h-screen flex flex-col">
  {/* Hero: 最大间距 */}
  <div className="py-32 px-8">
    <Hero />
  </div>
  
  {/* 最新文章: 标准间距 */}
  <div className="py-24 px-8">
    <SectionTitle>最新文章</SectionTitle>
    <div className="mt-8 grid grid-cols-3 gap-6">
      <BlogCards />
    </div>
  </div>
  
  {/* 关于我: 紧凑间距 */}
  <div className="py-20 px-8">
    <SectionTitle>关于我</SectionTitle>
    <div className="mt-6">
      <AboutSection />
    </div>
  </div>
  
  {/* Footer: 最小间距 */}
  <div className="py-16 px-8">
    <Footer />
  </div>
</section>
```

#### 留白设计原则
```css
/* 留白比例（内容/总宽） */
--whitespace-content: 0.75;  /* 75% 内容，25% 留白 */
--whitespace-minimal: 0.85;  /* 85% 内容，15% 留白 */

/* 应用留白 */
.content-container {
  max-width: min(calc(var(--whitespace-content) * 100vw), 1200px);
  margin: 0 auto;
}

.minimal-container {
  max-width: min(calc(var(--whitespace-minimal) * 100vw), 1400px);
  margin: 0 auto;
}
```

### 4.3 排版增强

#### 行高优化
```css
/* 精确行高计算 */
--font-base: 16px;
--line-height-body: 1.75;  /* 28px - 增强可读性 */
--line-height-title: 1.2;  /* 紧凑标题 */

/* 垂直韵律（基于字号） */
h1 {
  font-size: 48px;
  line-height: var(--line-height-title);
  margin-bottom: calc(var(--line-height-body) * var(--font-base));
}

p {
  font-size: var(--font-base);
  line-height: var(--line-height-body);
  margin-bottom: var(--line-height-body);
}
```

---

## 五、微交互动画方案

### 5.1 物理弹簧动画

#### Framer Motion 弹簧配置
```typescript
// 弹簧缓动函数
const springPresets = {
  // 快速弹跳
  snappy: {
    type: 'spring',
    stiffness: 500,
    damping: 28,
  },
  
  // 自然弹性
  bouncy: {
    type: 'spring',
    stiffness: 300,
    damping: 20,
  },
  
  // 平滑过渡
  smooth: {
    type: 'spring',
    stiffness: 100,
    damping: 15,
  },
  
  // 柔和回弹
  gentle: {
    type: 'spring',
    stiffness: 150,
    damping: 25,
  },
};

// 使用示例
<motion.div
  initial={{ scale: 0.8, opacity: 0 }}
  animate={{ scale: 1, opacity: 1 }}
  transition={springPresets.bouncy}
>
  {children}
</motion.div>
```

### 5.2 视差滚动动画

#### 分层视差效果
```typescript
// 视差层级配置
const parallaxLayers = [
  {
    speed: 0.1,  // 最慢（背景）
    component: <Background3D />,
  },
  {
    speed: 0.3,  // 中速（装饰）
    component: <FloatingShapes />,
  },
  {
    speed: 0.5,  // 正常（内容）
    component: <MainContent />,
  },
  {
    speed: 0.8,  // 较快（前景）
    component: <HeroElement />,
  },
];

// 视差实现
function ParallaxLayer({ speed, children }: ParallaxProps) {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 1000], [0, speed * 1000]);
  
  return (
    <motion.div style={{ y }} className="absolute inset-0">
      {children}
    </motion.div>
  );
}
```

### 5.3 弹性反馈动画

#### 按钮按压反馈
```tsx
<motion.button
  whileTap={{
    scale: 0.95,
    transition: springPresets.snappy,
  }}
  whileHover={{
    scale: 1.02,
    transition: springPresets.smooth,
  }}
>
  点击我
</motion.button>
```

#### 卡片悬停反馈
```tsx
<motion.div
  whileHover={{
    y: -8,
    scale: 1.02,
    transition: springPresets.gentle,
  }}
  className="glass-card-enhanced"
>
  <CardContent />
  
  {/* 悬停时显示的装饰元素 */}
  <motion.div
    initial={{ opacity: 0, scale: 0.8 }}
    whileHover={{
      opacity: 1,
      scale: 1,
      transition: springPresets.bouncy,
    }}
    className="absolute top-4 right-4"
  >
    <SparklesIcon className="w-6 h-6 text-purple-400" />
  </motion.div>
</motion.div>
```

### 5.4 元素组动画

#### 交错进入动画
```tsx
// 父容器
<motion.div
  initial="hidden"
  animate="visible"
  variants={{
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,  // 子元素交错延迟
      },
    },
  }}
>
  {/* 子元素 */}
  {items.map((item, index) => (
    <motion.div
      key={index}
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: {
          opacity: 1,
          y: 0,
          transition: springPresets.smooth,
        },
      }}
    >
      {item}
    </motion.div>
  ))}
</motion.div>
```

#### 列表项动画
```tsx
// 瀑布流进入
{posts.map((post, index) => (
  <motion.div
    key={post.id}
    initial={{ opacity: 0, y: 30 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{
      delay: index * 0.08,  // 基于索引的延迟
      ...springPresets.bouncy,
    }}
    className="col-span-1"
  >
    <BlogCard post={post} />
  </motion.div>
))}
```

---

## 六、性能优化设计

### 6.1 动画性能策略

#### 动画降级
```typescript
// 检测设备性能
const deviceCapabilities = {
  reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  lowEnd: navigator.hardwareConcurrency <= 4,
  mobile: window.innerWidth < 768,
};

// 根据性能调整动画
const animationConfig = deviceCapabilities.reducedMotion
  ? { duration: 0 }  // 禁用动画
  : deviceCapabilities.lowEnd
    ? { duration: 0.3 }  // 简化动画
    : springPresets.bouncy;  // 完整动画
```

#### 动画节流
```typescript
// 使用 useThrottleValue 节流滚动动画
import { useThrottledValue } from '@/hooks/useThrottle';

const scrollY = useScroll().scrollY;
const throttledScrollY = useThrottledValue(scrollY, 100);  // 100ms 节流

<motion.div
  style={{
    y: useTransform(throttledScrollY, [0, 500], [0, -200]),
  }}
>
  视差元素
</motion.div>
```

### 6.2 3D渲染优化

#### 可见性检测
```typescript
// 暂停离屏渲染
const isVisible = useInView(ref, { margin: '100%' });

useFrame((state, delta) => {
  if (isVisible) {
    // 只在可见时渲染
    updateParticles(delta);
  }
});
```

#### 细节级别(LOD)
```typescript
// 根据距离调整细节
const distance = camera.position.distanceTo(object.position);

const detailLevel = distance < 100 ? 'high' :
                   distance < 300 ? 'medium' : 'low';

switch (detailLevel) {
  case 'high':
    object.castShadow = true;
    object.receiveShadow = true;
    break;
  case 'medium':
    object.castShadow = true;
    object.receiveShadow = false;
    break;
  case 'low':
    object.castShadow = false;
    object.receiveShadow = false;
    break;
}
```

---

## 七、Tailwind 配置更新

### 7.1 扩展颜色
```typescript
colors: {
  // 光谱色
  spectrum: {
    1: '#6366f1',
    2: '#8b5cf6',
    3: '#a855f7',
    4: '#d946ef',
    5: '#ec4899',
    6: '#f43f5e',
    7: '#06b6d4',
  },
  
  // 辉光色
  glow: {
    indigo: 'rgba(99, 102, 241, 0.5)',
    purple: 'rgba(168, 85, 247, 0.5)',
    cyan: 'rgba(6, 182, 212, 0.5)',
  },
}
```

### 7.2 扩展阴影
```typescript
boxShadow: {
  'glow-1': '0 0 15px rgba(99, 102, 241, 0.3)',
  'glow-2': '0 0 25px rgba(168, 85, 247, 0.4)',
  'glow-3': '0 0 40px rgba(6, 182, 212, 0.5)',
  'glow-multi': '0 0 40px rgba(99, 102, 241, 0.3), 0 0 60px rgba(168, 85, 247, 0.2), 0 0 80px rgba(6, 182, 212, 0.1)',
  
  'glass-enhanced': 'inset 0 1px 0 rgba(255, 255, 255, 0.1), inset 0 -1px 0 rgba(0, 0, 0, 0.1), 0 8px 32px rgba(0, 0, 0, 0.3)',
}
```

### 7.3 扩展动画
```typescript
animation: {
  'shimmer': 'shimmer 2s infinite',
  'hue-rotate': 'hue-rotate 20s linear infinite',
  'glow-pulse': 'glow-pulse 3s ease-in-out infinite',
  'rotate-scan': 'rotate-scan 4s linear infinite',
},

keyframes: {
  shimmer: {
    '0%': { transform: 'translateX(-100%)' },
    '100%': { transform: 'translateX(100%)' },
  },
  hueRotate: {
    '0%, 100%': { filter: 'hue-rotate(0deg)' },
    '50%': { filter: 'hue-rotate(180deg)' },
  },
}
```

---

## 八、实现优先级

### Phase 1: 基础增强（必须）
- [x] 扩展色彩系统（7色光谱）
- [x] 多层毛玻璃组件
- [ ] 3D粒子性能分级
- [ ] 呼吸式间距系统

### Phase 2: 视觉增强（推荐）
- [ ] 流体渐变动画
- [ ] 辉光层级系统
- [ ] 视差滚动
- [ ] 物理弹簧动画

### Phase 3: 高级特效（可选）
- [ ] 鼠标力场交互
- [ ] 扫描线效果
- [ ] 弹性反馈动画
- [ ] LOD细节级别

---

## 九、设计交付清单

### 文档交付
- [x] UI_DESIGN_ENHANCED.md - 本文档
- [x] 色彩系统规范
- [x] 玻璃态组件规范
- [x] 3D背景增强规范
- [x] 布局美化规范
- [x] 微交互动画规范

### 开发参考
1. 查看 `myblog/UI_DESIGN_ENHANCED.md`（本文件）
2. 参考 `myblog/UI_DESIGN.md`（基础版）
3. 更新 `tailwind.config.ts` 配置
4. 按优先级实现增强效果

---

**文档版本**: v2.0  
**基于**: UI_DESIGN.md v1.0  
**创建时间**: 2024-04-06  
**UI 设计师**: ui_designer  
**优化目标**: 极致视觉体验
