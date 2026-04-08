'use client'

import { motion, useScroll, useTransform, useSpring } from 'framer-motion'
import { ReactNode, RefObject } from 'react'
import { easings, durations } from '@/constants/animations'
import { cn } from '@/lib/utils'

interface ParallaxProps {
  children: ReactNode
  className?: string
  speed?: number // 视差速度（0.1-2，1为正常速度，0.5为慢一半）
  offset?: number // 初始偏移
  direction?: 'vertical' | 'horizontal' // 滚动方向
  containerRef?: RefObject<HTMLElement> // 可选的容器引用（用于局部滚动）
  smooth?: boolean // 是否启用平滑动画
  disabled?: boolean // 是否禁用视差效果
}

export function Parallax({
  children,
  className = '',
  speed = 0.5,
  offset = 0,
  direction = 'vertical',
  containerRef,
  smooth = true,
  disabled = false,
}: ParallaxProps) {
  // 获取滚动进度
  const { scrollY, scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start end', 'end start'],
  })
  
  // 计算视差偏移
  const rawOffset = useTransform(
    scrollY,
    [0, 1000],
    [0, -1000 * speed]
  )
  
  // 根据方向选择 transform
  const transform = direction === 'vertical' 
    ? useTransform(rawOffset, val => `translateY(${val}px)`)
    : useTransform(rawOffset, val => `translateX(${val}px)`)
  
  // 可选的平滑动画
  const smoothedOffset = smooth 
    ? useSpring(rawOffset, { 
        stiffness: 80, 
        damping: 20, 
        restDelta: 0.001 
      })
    : rawOffset
  
  const smoothTransform = direction === 'vertical' 
    ? useTransform(smoothedOffset, val => `translateY(${val + offset}px)`)
    : useTransform(smoothedOffset, val => `translateX(${val + offset}px)`)

  if (disabled) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      className={cn('will-change-transform', className)}
      style={{
        [direction === 'vertical' ? 'y' : 'x']: smooth ? smoothedOffset : rawOffset,
      }}
      transition={{
        duration: durations.normal,
        ease: easings.smooth,
      }}
    >
      {children}
    </motion.div>
  )
}

// === 进阶：多层视差容器 ===
interface ParallaxLayerProps {
  children: ReactNode
  depth: number // 深度层级（0-2，越大越近，移动越快）
  className?: string
  offset?: number
}

export function ParallaxLayer({
  children,
  depth,
  className = '',
  offset = 0,
}: ParallaxLayerProps) {
  const { scrollYProgress } = useScroll()
  
  // 根据深度计算不同的移动速度
  const y = useTransform(
    scrollYProgress,
    [0, 1],
    [offset * (1 + depth), -offset * (1 + depth)]
  )
  
  // 透明度渐变（可选效果）
  const opacity = useTransform(
    scrollYProgress,
    [0, 0.1, 0.9, 1],
    [0, 1, 1, 0]
  )
  
  return (
    <motion.div
      className={cn('absolute inset-0 will-change-transform', className)}
      style={{ y, opacity }}
    >
      {children}
    </motion.div>
  )
}

// === 简化的视差包装器 ===
interface SimpleParallaxProps {
  children: ReactNode
  className?: string
  translateY?: [number, number] // [开始Y, 结束Y]
  translateX?: [number, number] // [开始X, 结束X]
  scale?: [number, number] // [开始Scale, 结束Scale]
  opacity?: [number, number] // [开始Opacity, 结束Opacity]
  rotate?: [number, number] // [开始Rotate, 结束Rotate]
  smooth?: boolean
}

export function SimpleParallax({
  children,
  className = '',
  translateY,
  translateX,
  scale,
  opacity,
  rotate,
  smooth = true,
}: SimpleParallaxProps) {
  const { scrollYProgress } = useScroll()
  
  const y = translateY 
    ? useTransform(scrollYProgress, [0, 1], translateY)
    : 0
  const x = translateX
    ? useTransform(scrollYProgress, [0, 1], translateX)
    : 0
  const s = scale
    ? useTransform(scrollYProgress, [0, 1], scale)
    : 1
  const o = opacity
    ? useTransform(scrollYProgress, [0, 1], opacity)
    : 1
  const r = rotate
    ? useTransform(scrollYProgress, [0, 1], rotate)
    : 0
  
  const smoothY = smooth ? useSpring(y, { stiffness: 80, damping: 20 }) : y
  const smoothX = smooth ? useSpring(x, { stiffness: 80, damping: 20 }) : x
  const smoothS = smooth ? useSpring(s, { stiffness: 80, damping: 20 }) : s
  const smoothO = smooth ? useSpring(o, { stiffness: 80, damping: 20 }) : o
  const smoothR = smooth ? useSpring(r, { stiffness: 80, damping: 20 }) : r
  
  return (
    <motion.div
      className={cn('will-change-transform', className)}
      style={{
        y: smoothY,
        x: smoothX,
        scale: smoothS,
        opacity: smoothO,
        rotate: smoothR,
      }}
    >
      {children}
    </motion.div>
  )
}
