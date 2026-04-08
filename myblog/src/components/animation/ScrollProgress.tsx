'use client'

import { motion, useScroll, useSpring, useReducedMotion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface ScrollProgressProps {
  height?: number
  colors?: string
  className?: string
  position?: 'top' | 'bottom'
  disabled?: boolean
}

export function ScrollProgress({
  height = 1,
  colors = 'from-purple-500 via-cyan-500 to-amber-500',
  className = '',
  position = 'top',
  disabled = false,
}: ScrollProgressProps) {
  const prefersReducedMotion = useReducedMotion()
  
  if (disabled || prefersReducedMotion) {
    return null
  }

  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  })

  return (
    <motion.div
      className={cn(
        'fixed left-0 right-0 origin-left z-50',
        position === 'top' ? 'top-0' : 'bottom-0',
        `h-[${height}px]`,
        `bg-gradient-to-r ${colors}`,
        className
      )}
      style={{ 
        scaleX,
        height: `${height}px`,
      }}
    />
  )
}
