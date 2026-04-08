'use client'

import { motion, useMotionValue, useSpring, useTransform, AnimatePresence } from 'framer-motion'
import { ReactNode, useRef, useState } from 'react'
import { easings, durations, hoverAnimations } from '@/constants/animations'
import { cn } from '@/lib/utils'

interface MagneticCardProps {
  children: ReactNode
  className?: string
  strength?: number // 磁性吸附强度（像素）
  rotationStrength?: number // 3D旋转强度（度）
  stiffness?: number // 弹簧刚度
  damping?: number // 阻尼
  onClick?: () => void
  disabled?: boolean
  showGlow?: boolean // 是否显示光泽效果
}

export function MagneticCard({
  children,
  className = '',
  strength = 20,
  rotationStrength = 5,
  stiffness = 120,
  damping = 25,
  onClick,
  disabled = false,
  showGlow = true,
}: MagneticCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [isHovered, setIsHovered] = useState(false)
  
  // 鼠标相对于卡片中心的偏移
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  
  // 按钮中心偏移
  const offsetX = useMotionValue(0)
  const offsetY = useMotionValue(0)
  
  // 平滑动画的偏移值
  const springX = useSpring(offsetX, { stiffness, damping })
  const springY = useSpring(offsetY, { stiffness, damping })
  
  // 根据偏移值创建3D旋转效果
  const rotateX = useTransform(springY, [-strength, strength], [-rotationStrength, rotationStrength])
  const rotateY = useTransform(springX, [-strength, strength], [rotationStrength, -rotationStrength])
  
  // 光泽效果的位置
  const glareX = useTransform(mouseX, val => `${val}%`)
  const glareY = useTransform(mouseY, val => `${val}%`)
  
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (disabled || !ref.current) return
    
    const rect = ref.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    
    // 计算鼠标相对于中心的距离
    const distanceX = e.clientX - centerX
    const distanceY = e.clientY - centerY
    
    // 计算鼠标在卡片内的相对位置（用于光泽效果）
    const relativeX = ((e.clientX - rect.left) / rect.width) * 100
    const relativeY = ((e.clientY - rect.top) / rect.height) * 100
    mouseX.set(relativeX)
    mouseY.set(relativeY)
    
    // 限制在强度范围内
    offsetX.set(Math.max(-strength, Math.min(strength, distanceX / 4)))
    offsetY.set(Math.max(-strength, Math.min(strength, distanceY / 4)))
  }
  
  const handleMouseLeave = () => {
    offsetX.set(0)
    offsetY.set(0)
    setIsHovered(false)
  }
  
  const handleMouseEnter = () => {
    setIsHovered(true)
  }
  
  return (
    <motion.div
      ref={ref}
      className={cn('relative cursor-pointer', className)}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={handleMouseEnter}
      onClick={onClick}
      // 使用 GPU 加速的 transform
      style={{
        x: springX,
        y: springY,
        rotateX,
        rotateY,
        transformStyle: 'preserve-3d',
      }}
      // 悬停动画
      whileHover={!disabled ? { scale: 1.02 } : undefined}
      whileTap={!disabled ? { scale: 0.98 } : undefined}
      transition={{
        duration: durations.normal,
        ease: easings.smooth,
      }}
    >
      {/* 光泽效果层 */}
      <AnimatePresence>
        {showGlow && isHovered && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4 }}
            exit={{ opacity: 0 }}
            transition={{ duration: durations.fast }}
            className="absolute inset-0 pointer-events-none overflow-hidden rounded-inherit"
            style={{
              background: `radial-gradient(circle at ${glareX} ${glareY}, rgba(255, 255, 255, 0.3) 0%, transparent 60%)`,
              mixBlendMode: 'overlay',
            }}
          />
        )}
      </AnimatePresence>
      
      {/* 内容层 */}
      <div className="relative z-10" style={{ transform: 'translateZ(10px)' }}>
        {children}
      </div>
    </motion.div>
  )
}
