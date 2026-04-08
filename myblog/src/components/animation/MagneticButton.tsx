'use client'

import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { ReactNode, useRef } from 'react'
import { easings, durations, hoverAnimations, tapAnimations } from '@/constants/animations'

interface MagneticButtonProps {
  children: ReactNode
  className?: string
  strength?: number // 磁性吸附强度（像素）
  stiffness?: number // 弹簧刚度
  damping?: number // 阻尼
  onClick?: () => void
  disabled?: boolean
}

export function MagneticButton({
  children,
  className = '',
  strength = 30,
  stiffness = 150,
  damping = 20,
  onClick,
  disabled = false,
}: MagneticButtonProps) {
  const ref = useRef<HTMLButtonElement>(null)
  
  // 鼠标位置
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  
  // 按钮中心偏移
  const offsetX = useMotionValue(0)
  const offsetY = useMotionValue(0)
  
  // 平滑动画的偏移值
  const springX = useSpring(offsetX, { stiffness, damping })
  const springY = useSpring(offsetY, { stiffness, damping })
  
  // 根据偏移值创建轻微的旋转效果
  const rotateX = useTransform(springY, [-strength, strength], [3, -3])
  const rotateY = useTransform(springX, [-strength, strength], [-3, 3])
  
  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled || !ref.current) return
    
    const rect = ref.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    
    // 计算鼠标相对于中心的距离
    const distanceX = e.clientX - centerX
    const distanceY = e.clientY - centerY
    
    // 限制在强度范围内
    offsetX.set(Math.max(-strength, Math.min(strength, distanceX / 3)))
    offsetY.set(Math.max(-strength, Math.min(strength, distanceY / 3)))
  }
  
  const handleMouseLeave = () => {
    offsetX.set(0)
    offsetY.set(0)
  }
  
  return (
    <motion.button
      ref={ref}
      className={className}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      disabled={disabled}
      // 使用 GPU 加速的 transform
      style={{
        x: springX,
        y: springY,
        rotateX,
        rotateY,
        transformStyle: 'preserve-3d',
      }}
      // 悬停动画
      whileHover={!disabled ? hoverAnimations.scale : undefined}
      whileTap={!disabled ? tapAnimations.scale : undefined}
      transition={{
        duration: durations.fast,
        ease: easings.smooth,
      }}
    >
      {children}
    </motion.button>
  )
}
