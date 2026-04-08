'use client'

import { motion, useReducedMotion } from 'framer-motion'
import { ReactNode } from 'react'
import { easings } from '@/constants/animations'
import { cn } from '@/lib/utils'

interface FadeInProps {
  children: ReactNode
  delay?: number
  duration?: number
  className?: string
  direction?: 'up' | 'down' | 'left' | 'right'
  disabled?: boolean
  whileInView?: boolean
}

export function FadeIn({ 
  children, 
  delay = 0, 
  duration = 0.5,
  className = '',
  direction = 'up',
  disabled = false,
  whileInView = false,
}: FadeInProps) {
  const prefersReducedMotion = useReducedMotion()
  const shouldAnimate = !disabled && !prefersReducedMotion
  
  const directionVariants = {
    up: { y: 20 },
    down: { y: -20 },
    left: { x: 20 },
    right: { x: -20 },
  }

  return (
    <motion.div
      initial={shouldAnimate ? { opacity: 0, ...directionVariants[direction] } : undefined}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ 
        duration, 
        delay,
        ease: easings.smooth,
      }}
      className={cn('will-change-transform', className)}
      viewport={whileInView ? { once: true, margin: '-50px' } : undefined}
    >
      {children}
    </motion.div>
  )
}
