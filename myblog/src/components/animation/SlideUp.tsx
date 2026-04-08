'use client'

import { motion, Variants, useReducedMotion } from 'framer-motion'
import { ReactNode } from 'react'
import { easings, durations } from '@/constants/animations'
import { cn } from '@/lib/utils'

interface SlideUpProps {
  children: ReactNode
  delay?: number
  staggerChildren?: number
  className?: string
  disabled?: boolean
  viewportOnce?: boolean
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: durations.slow,
      ease: easings.smooth,
    },
  },
}

export function SlideUp({ 
  children, 
  className,
  disabled = false,
  viewportOnce = true,
}: SlideUpProps) {
  const prefersReducedMotion = useReducedMotion()
  const shouldAnimate = !disabled && !prefersReducedMotion

  return (
    <motion.div
      initial={shouldAnimate ? "hidden" : "visible"}
      animate="visible"
      variants={containerVariants}
      className={cn('will-change-transform', className)}
      viewport={viewportOnce ? { once: true, margin: '-50px' } : undefined}
    >
      {children}
    </motion.div>
  )
}

export function SlideUpItem({ 
  children, 
  delay = 0, 
  className,
  disabled = false 
}: Omit<SlideUpProps, 'staggerChildren' | 'viewportOnce'>) {
  const prefersReducedMotion = useReducedMotion()
  const shouldAnimate = !disabled && !prefersReducedMotion

  return (
    <motion.div
      initial={shouldAnimate ? "hidden" : "visible"}
      animate="visible"
      variants={itemVariants}
      transition={{ delay }}
      className={cn('will-change-transform', className)}
    >
      {children}
    </motion.div>
  )
}
