'use client'

import { useAnimation, useInView, useScroll, useTransform, useMotionValue, useSpring } from 'framer-motion'
import { useRef, useEffect } from 'react'
import { easings, durations } from '@/constants/animations'

// === 基础动画控制 Hook ===
export function useAnimationControl() {
  const controls = useAnimation()
  
  return {
    controls,
    play: () => controls.start('visible'),
    reset: () => controls.start('hidden'),
    reverse: () => controls.start({
      opacity: [1, 0],
      y: [0, 20]
    })
  }
}

// === 滚动触发动画 Hook ===
interface UseScrollAnimationOptions {
  threshold?: number
  triggerOnce?: boolean
  margin?: string
}

export function useScrollAnimation(options: UseScrollAnimationOptions = {}) {
  const {
    threshold = 0.1,
    triggerOnce = true,
    margin = '-50px'
  } = options
  
  const ref = useRef<HTMLElement>(null)
  const isInView = useInView(ref, {
    amount: threshold,
    once: triggerOnce,
    margin
  })
  
  return { ref, isInView }
}

// === 平滑滚动 Hook ===
export function useSmoothScroll() {
  const { scrollY, scrollYProgress } = useScroll()
  
  // 平滑滚动值（用于视差效果）
  const smoothScrollY = useSpring(scrollY, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  })
  
  const smoothScrollProgress = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  })
  
  return {
    scrollY,
    scrollYProgress,
    smoothScrollY,
    smoothScrollProgress
  }
}

// === 鼠标跟踪 Hook ===
export function useMouseTracking() {
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  
  const updateMousePosition = (e: MouseEvent) => {
    mouseX.set(e.clientX)
    mouseY.set(e.clientY)
  }
  
  useEffect(() => {
    window.addEventListener('mousemove', updateMousePosition)
    return () => window.removeEventListener('mousemove', updateMousePosition)
  }, [])
  
  return { mouseX, mouseY }
}

// === 元素中心鼠标跟踪 Hook ===
export function useElementMouseTracking(enabled = true) {
  const ref = useRef<HTMLElement>(null)
  const offsetX = useMotionValue(0)
  const offsetY = useMotionValue(0)
  const normalizedX = useMotionValue(0)
  const normalizedY = useMotionValue(0)
  
  const handleMouseMove = (e: MouseEvent) => {
    if (!enabled || !ref.current) return
    
    const rect = ref.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    
    const deltaX = e.clientX - centerX
    const deltaY = e.clientY - centerY
    
    offsetX.set(deltaX)
    offsetY.set(deltaY)
    
    // 归一化到 -1 到 1
    normalizedX.set(deltaX / (rect.width / 2))
    normalizedY.set(deltaY / (rect.height / 2))
  }
  
  useEffect(() => {
    if (!enabled) return
    
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [enabled])
  
  return { ref, offsetX, offsetY, normalizedX, normalizedY }
}

// === 动画状态 Hook ===
export function useAnimationState() {
  const isAnimating = useMotionValue(false)
  
  const startAnimation = () => isAnimating.set(true)
  const endAnimation = () => isAnimating.set(false)
  
  return { isAnimating, startAnimation, endAnimation }
}

// === 视差滚动值 Hook ===
interface UseParallaxScrollOptions {
  speed?: number
  smooth?: boolean
  offset?: number
}

export function useParallaxScroll(options: UseParallaxScrollOptions = {}) {
  const {
    speed = 0.5,
    smooth = true,
    offset = 0
  } = options
  
  const { scrollY } = useScroll()
  
  const rawOffset = useTransform(scrollY, [0, 1000], [0, -1000 * speed])
  
  // 可选的平滑动画
  const smoothedOffset = smooth 
    ? useSpring(rawOffset, { 
        stiffness: 80, 
        damping: 20, 
        restDelta: 0.001 
      })
    : rawOffset
  
  const y = useTransform(smoothedOffset, val => val + offset)
  
  return { y, rawOffset, smoothedOffset }
}

// === 淡入淡出 Hook ===
export function useFadeInOut(duration = durations.normal) {
  const controls = useAnimation()
  
  const fadeIn = async () => {
    await controls.start({
      opacity: 1,
      transition: {
        duration,
        ease: easings.smooth
      }
    })
  }
  
  const fadeOut = async () => {
    await controls.start({
      opacity: 0,
      transition: {
        duration,
        ease: easings.smooth
      }
    })
  }
  
  return { controls, fadeIn, fadeOut }
}
