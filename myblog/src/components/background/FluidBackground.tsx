'use client';

import { useRef, useMemo, useEffect, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';

// === 常量 ===
const PERFORMANCE_LEVELS = {
  high: { particleCount: [3000, 4000, 5000], segments: 64 },
  medium: { particleCount: [2000, 3000, 4000], segments: 48 },
  low: { particleCount: [1000, 1500, 2000], segments: 32 },
};

// === Hooks ===

/**
 * 性能检测 Hook
 * 根据设备性能返回优化级别
 */
function usePerformanceLevel() {
  const [level, setLevel] = useState<keyof typeof PERFORMANCE_LEVELS>('high');

  useEffect(() => {
    const checkPerformance = () => {
      const width = window.innerWidth;
      
      // 移动端降低
      if (width < 768) {
        return 'low';
      }
      
      // 平板中等
      if (width < 1024) {
        return 'medium';
      }
      
      // 检查 GPU 性能
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) return 'low';
      
      const rendererInfo = (gl as any).getExtension('WEBGL_debug_renderer_info');
      if (rendererInfo) {
        const renderer = (gl as any).getParameter((rendererInfo as any).UNMASKED_RENDERER_WEBGL);
        // 检测到低端 GPU
        if (renderer && (renderer.includes('Intel') || renderer.includes('Mali') || renderer.includes('Adreno'))) {
          return 'medium';
        }
      }
      
      return 'high';
    };

    setLevel(checkPerformance());
  }, []);

  return level;
}

// === 组件 ===

/**
 * 多层粒子场组件
 * 包含前景、中景、背景三层粒子
 */
function MultiLayerParticleField({ 
  layer = 'middle',
  particleCount = 4000,
  speed = 1,
  size = 0.025,
  colorScheme = 'purple',
  mouseInfluence = 0.2 
}: {
  layer: 'background' | 'middle' | 'foreground';
  particleCount?: number;
  speed?: number;
  size?: number;
  colorScheme?: 'purple' | 'blue' | 'cyan' | 'mixed';
  mouseInfluence?: number;
}) {
  const ref = useRef<THREE.Points>(null);
  const { mouse, clock } = useThree();
  
  // 性能优化：使用 useMemo 预计算
  const { positions, originalPositions, colors, velocities } = useMemo(() => {
    const positions = new Float32Array(particleCount * 3);
    const originalPositions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const velocities = new Float32Array(particleCount * 3);
    
    // 根据层级调整分布范围
    const spread = layer === 'background' ? 8 : layer === 'foreground' ? 4 : 6;
    const depth = layer === 'background' ? -4 : layer === 'foreground' ? -1 : -2;
    
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      const x = (Math.random() - 0.5) * spread * 2;
      const y = (Math.random() - 0.5) * spread * 2;
      const z = depth + (Math.random() - 0.5) * 3;
      
      positions[i3] = x;
      positions[i3 + 1] = y;
      positions[i3 + 2] = z;
      
      originalPositions[i3] = x;
      originalPositions[i3 + 1] = y;
      originalPositions[i3 + 2] = z;
      
      // 随机速度
      velocities[i3] = (Math.random() - 0.5) * 0.001;
      velocities[i3 + 1] = (Math.random() - 0.5) * 0.001;
      velocities[i3 + 2] = (Math.random() - 0.5) * 0.001;
      
      // 颜色方案
      const t = Math.random();
      if (colorScheme === 'purple') {
        colors[i3] = 0.4 + t * 0.3;          // R: 0.4-0.7
        colors[i3 + 1] = 0.2 + t * 0.4;      // G: 0.2-0.6
        colors[i3 + 2] = 0.6 + t * 0.3;      // B: 0.6-0.9
      } else if (colorScheme === 'blue') {
        colors[i3] = 0.2 + t * 0.3;          // R
        colors[i3 + 1] = 0.4 + t * 0.4;      // G
        colors[i3 + 2] = 0.7 + t * 0.2;      // B
      } else if (colorScheme === 'cyan') {
        colors[i3] = 0.1 + t * 0.2;          // R
        colors[i3 + 1] = 0.6 + t * 0.3;      // G
        colors[i3 + 2] = 0.7 + t * 0.2;      // B
      } else { // mixed
        const hue = Math.random();
        const color = new THREE.Color();
        color.setHSL(hue, 0.7, 0.6);
        colors[i3] = color.r;
        colors[i3 + 1] = color.g;
        colors[i3 + 2] = color.b;
      }
    }
    
    return { positions, originalPositions, colors, velocities };
  }, [particleCount, layer, colorScheme]);

  // 鼠标位置缓存（减少计算）
  const mouseRef = useRef({ x: 0, y: 0 });

  useFrame(() => {
    if (!ref.current) return;

    const time = clock.getElapsedTime() * speed;
    
    // 平滑更新鼠标位置
    mouseRef.current.x += (mouse.x * 5 - mouseRef.current.x) * 0.05;
    mouseRef.current.y += (mouse.y * 3 - mouseRef.current.y) * 0.05;
    
    // 缓慢旋转
    ref.current.rotation.x = time * 0.02 * speed;
    ref.current.rotation.y = time * 0.03 * speed;

    const positionsArray = ref.current.geometry.attributes.position.array as Float32Array;
    const colorsArray = ref.current.geometry.attributes.color.array as Float32Array;
    
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      
      // 基础波动
      const waveX = Math.sin(time * 0.5 + i * 0.01) * 0.2;
      const waveY = Math.cos(time * 0.4 + i * 0.01) * 0.2;
      
      // 鼠标交互 - 吸引和排斥
      const dx = mouseRef.current.x - originalPositions[i3];
      const dy = mouseRef.current.y - originalPositions[i3 + 1];
      const dist = Math.sqrt(dx * dx + dy * dy);
      
      // 距离鼠标越近，影响越大
      const influence = Math.max(0, 1 - dist / 3);
      const smoothInfluence = influence * influence * (3 - 2 * influence);
      
      // 目标位置
      const targetX = originalPositions[i3] + waveX + dx * smoothInfluence * mouseInfluence;
      const targetY = originalPositions[i3 + 1] + waveY + dy * smoothInfluence * mouseInfluence;
      const targetZ = originalPositions[i3 + 2] + smoothInfluence * 0.3;
      
      // 平滑插值
      const lerpFactor = 0.02 * speed;
      positionsArray[i3] += (targetX - positionsArray[i3]) * lerpFactor;
      positionsArray[i3 + 1] += (targetY - positionsArray[i3 + 1]) * lerpFactor;
      positionsArray[i3 + 2] += (targetZ - positionsArray[i3 + 2]) * lerpFactor;
      
      // 颜色动态混合 - 靠近鼠标时颜色变化
      if (mouseInfluence > 0) {
        const originalR = colors[i3];
        const originalG = colors[i3 + 1];
        const originalB = colors[i3 + 2];
        
        // 靠近鼠标时变亮
        const brightnessFactor = 1 + smoothInfluence * 0.3;
        colorsArray[i3] = originalR * brightnessFactor;
        colorsArray[i3 + 1] = originalG * brightnessFactor;
        colorsArray[i3 + 2] = originalB * brightnessFactor;
      }
    }
    
    ref.current.geometry.attributes.position.needsUpdate = true;
    if (mouseInfluence > 0) {
      ref.current.geometry.attributes.color.needsUpdate = true;
    }
  });

  return (
    <Points ref={ref} positions={positions} colors={colors} stride={3}>
      <PointMaterial
        transparent
        vertexColors
        size={size}
        sizeAttenuation={true}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        opacity={layer === 'background' ? 0.4 : layer === 'foreground' ? 0.8 : 0.6}
      />
    </Points>
  );
}

/**
 * 增强版流体波浪
 */
function EnhancedFluidWave({ 
  segments = 64,
  amplitude = 0.5,
  speed = 1 
}: {
  segments?: number;
  amplitude?: number;
  speed?: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const { mouse, clock } = useThree();

  useFrame(() => {
    if (!meshRef.current) return;

    const time = clock.getElapsedTime() * speed;
    const positions = meshRef.current.geometry.attributes.position.array as Float32Array;
    
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i];
      const y = positions[i + 1];
      
      // 鼠标影响
      const mouseInfluence = Math.exp(
        -((x - mouse.x * 5) ** 2 + (y - mouse.y * 3) ** 2) / 2
      );
      
      // 复合波浪效果
      const wave1 = Math.sin(x * 0.5 + time) * amplitude;
      const wave2 = Math.cos(y * 0.3 + time * 0.8) * amplitude * 0.6;
      const wave3 = Math.sin((x + y) * 0.2 + time * 0.6) * amplitude * 0.4;
      const wave4 = Math.sin(x * 0.8 - time * 1.2) * amplitude * 0.3 * mouseInfluence;
      
      positions[i + 2] = wave1 + wave2 + wave3 + wave4;
    }
    
    meshRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -3, -2]}>
      <planeGeometry args={[16, 16, segments, segments]} />
      <meshStandardMaterial
        color="#4f46e5"
        wireframe={true}
        transparent
        opacity={0.12}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

/**
 * 增强版发光球体
 */
function EnhancedGlowOrb({ 
  radius = 0.8,
  pulseEnabled = true,
  followMouse = true
}: {
  radius?: number;
  pulseEnabled?: boolean;
  followMouse?: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const { mouse, clock } = useThree();

  useFrame(() => {
    if (!meshRef.current) return;

    const time = clock.getElapsedTime();
    
    if (followMouse) {
      // 跟随鼠标，带有延迟
      const targetX = mouse.x * 2;
      const targetY = mouse.y * 2;
      
      meshRef.current.position.x += (targetX - meshRef.current.position.x) * 0.03;
      meshRef.current.position.y += (targetY - meshRef.current.position.y) * 0.03;
      meshRef.current.position.z = -2 + Math.sin(time * 0.5) * 0.5;
    }
    
    if (pulseEnabled) {
      // 脉冲缩放
      const scale = 1 + Math.sin(time * 2) * 0.15;
      meshRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshBasicMaterial
        color="#a855f7"
        transparent
        opacity={0.15}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// === 主组件 ===

interface FluidBackgroundProps {
  enableParticles?: boolean;
  enableWave?: boolean;
  enableGlowOrb?: boolean;
  particleCount?: number;
}

export default function FluidBackground({
  enableParticles = true,
  enableWave = true,
  enableGlowOrb = true,
}: FluidBackgroundProps = {}) {
  const performanceLevel = usePerformanceLevel();
  const config = PERFORMANCE_LEVELS[performanceLevel];

  return (
    <div className="fixed inset-0 -z-10">
      <Canvas
        camera={{ position: [0, 0, 4], fov: 75 }}
        gl={{ 
          antialias: true, 
          alpha: true,
          powerPreference: 'high-performance',
        }}
        dpr={[1, performanceLevel === 'high' ? 2 : 1.5]}
      >
        <ambientLight intensity={0.3} />
        
        {enableParticles && (
          <>
            {/* 背景粒子层 */}
            <MultiLayerParticleField
              layer="background"
              particleCount={config.particleCount[0]}
              size={0.015}
              colorScheme="purple"
              speed={0.5}
              mouseInfluence={0.15}
            />
            
            {/* 中景粒子层 */}
            <MultiLayerParticleField
              layer="middle"
              particleCount={config.particleCount[1]}
              size={0.02}
              colorScheme="blue"
              speed={0.7}
              mouseInfluence={0.2}
            />
            
            {/* 前景粒子层 */}
            <MultiLayerParticleField
              layer="foreground"
              particleCount={config.particleCount[2]}
              size={0.03}
              colorScheme="cyan"
              speed={1}
              mouseInfluence={0.3}
            />
          </>
        )}
        
        {enableWave && (
          <EnhancedFluidWave
            segments={config.segments}
            amplitude={0.5}
            speed={1}
          />
        )}
        
        {enableGlowOrb && (
          <EnhancedGlowOrb
            radius={0.8}
            pulseEnabled={performanceLevel !== 'low'}
            followMouse={true}
          />
        )}
      </Canvas>
      
      {/* 渐变背景叠加 */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 via-blue-900/10 to-slate-900/30 backdrop-blur-[1px]" />
      
      {/* 径向渐变，增强中心亮度 */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_transparent_0%,_rgba(0,0,0,0.25)_100%)]" />
    </div>
  );
}
