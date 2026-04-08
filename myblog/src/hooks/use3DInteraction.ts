'use client';

import { useRef, useEffect } from 'react';
import * as THREE from 'three';

interface Use3DInteractionOptions {
  enabled?: boolean;
  smoothing?: number;
  influenceRadius?: number;
  attractionStrength?: number;
}

interface MousePosition {
  x: number;
  y: number;
}

/**
 * 3D 交互 Hook，提供鼠标跟踪和交互逻辑
 * 用于处理粒子、网格等 3D 元素的鼠标交互
 */
export function use3DInteraction(options: Use3DInteractionOptions = {}) {
  const {
    enabled = true,
    smoothing = 0.02,
    influenceRadius = 3,
    attractionStrength = 0.2,
  } = options;

  const mouseRef = useRef<MousePosition>({ x: 0, y: 0 });
  const targetMouseRef = useRef<MousePosition>({ x: 0, y: 0 });

  useEffect(() => {
    if (!enabled) return;

    const handleMouseMove = (event: MouseEvent) => {
      // 归一化到 -1 到 1
      targetMouseRef.current = {
        x: (event.clientX / window.innerWidth) * 2 - 1,
        y: -(event.clientY / window.innerHeight) * 2 + 1,
      };
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [enabled]);

  /**
   * 计算粒子受鼠标影响的位移
   * @param originalX 粒子原始 X 坐标
   * @param originalY 粒子原始 Y 坐标
   * @returns 位移向量 [dx, dy, influence]
   */
  const calculateInfluence = (
    originalX: number,
    originalY: number
  ): [number, number, number] => {
    const dx = mouseRef.current.x * 5 - originalX;
    const dy = mouseRef.current.y * 3 - originalY;
    const dist = Math.sqrt(dx * dx + dy * dy);

    // 距离鼠标越近，影响越大（使用 smoothstep）
    const influence = Math.max(0, 1 - dist / influenceRadius);
    const smoothInfluence = influence * influence * (3 - 2 * influence);

    return [
      dx * smoothInfluence * attractionStrength,
      dy * smoothInfluence * attractionStrength,
      smoothInfluence,
    ];
  };

  /**
   * 平滑更新鼠标位置
   * 应该在 useFrame 中调用
   */
  const updateMousePosition = () => {
    mouseRef.current.x += (targetMouseRef.current.x - mouseRef.current.x) * smoothing;
    mouseRef.current.y += (targetMouseRef.current.y - mouseRef.current.y) * smoothing;
  };

  /**
   * 平滑插值到目标值
   */
  const lerp = (current: number, target: number, factor?: number): number => {
    return current + (target - current) * (factor ?? smoothing);
  };

  return {
    mouse: mouseRef.current,
    updateMousePosition,
    calculateInfluence,
    lerp,
  };
}

/**
 * 简化的 3D 鼠标跟踪 Hook
 * 直接从 Three.js state.mouse 获取
 */
export function useThreeMouse() {
  return useRef({ x: 0, y: 0 });
}
