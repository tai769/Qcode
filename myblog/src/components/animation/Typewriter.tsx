'use client'

import { motion } from 'framer-motion'
import { ReactNode, useEffect, useState } from 'react'
import { easings, durations } from '@/constants/animations'
import { cn } from '@/lib/utils'

interface TypewriterProps {
  text: string
  className?: string
  speed?: number // 打字速度（毫秒/字符）
  delay?: number // 开始延迟（毫秒）
  cursor?: boolean // 是否显示光标
  cursorChar?: string // 光标字符
  cursorClassName?: string // 光标样式
  onComplete?: () => void // 打字完成回调
  loop?: boolean // 是否循环播放
  loopDelay?: number // 循环延迟（毫秒）
  scramble?: boolean // 是否启用乱码效果
  scrambleChars?: string // 乱码字符集
}

export function Typewriter({
  text,
  className = '',
  speed = 50,
  delay = 0,
  cursor = true,
  cursorChar = '|',
  cursorClassName = '',
  onComplete,
  loop = false,
  loopDelay = 2000,
  scramble = false,
  scrambleChars = '!<>-_\\/[]{}—=+*^?#________',
}: TypewriterProps) {
  const [displayText, setDisplayText] = useState('')
  const [isComplete, setIsComplete] = useState(false)
  const [showCursor, setShowCursor] = useState(true)

  useEffect(() => {
    let timeout: NodeJS.Timeout
    let currentIndex = 0
    let animationFrame: number
    
    // 延迟开始
    const startAnimation = () => {
      const typeChar = () => {
        if (currentIndex < text.length) {
          if (scramble) {
            // 乱码效果
            let scrambleCount = 0
            const maxScramble = 3
            
            const scrambleAnimation = () => {
              if (scrambleCount < maxScramble) {
                const scrambleText = text.slice(0, currentIndex) + 
                  scrambleChars[Math.floor(Math.random() * scrambleChars.length)] +
                  text.slice(currentIndex + 1)
                setDisplayText(scrambleText)
                scrambleCount++
                animationFrame = requestAnimationFrame(() => 
                  setTimeout(scrambleAnimation, 30)
                )
              } else {
                // 最终显示正确字符
                setDisplayText(text.slice(0, currentIndex + 1))
                currentIndex++
                timeout = setTimeout(typeChar, speed)
              }
            }
            scrambleAnimation()
          } else {
            // 普通打字
            setDisplayText(text.slice(0, currentIndex + 1))
            currentIndex++
            timeout = setTimeout(typeChar, speed)
          }
        } else {
          // 打字完成
          setIsComplete(true)
          if (onComplete) {
            onComplete()
          }
          
          // 循环播放
          if (loop) {
            timeout = setTimeout(() => {
              setIsComplete(false)
              setDisplayText('')
              currentIndex = 0
              typeChar()
            }, loopDelay)
          }
        }
      }
      typeChar()
    }
    
    timeout = setTimeout(startAnimation, delay)
    
    // 光标闪烁
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev)
    }, 500)
    
    return () => {
      clearTimeout(timeout)
      clearInterval(cursorInterval)
      cancelAnimationFrame(animationFrame)
    }
  }, [text, speed, delay, scramble, scrambleChars, loop, loopDelay, onComplete])

  return (
    <span className={cn('inline', className)}>
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: durations.fast, ease: easings.smooth }}
      >
        {displayText}
      </motion.span>
      {cursor && (
        <motion.span
          className={cn('inline-block', cursorClassName)}
          animate={{ opacity: showCursor ? 1 : 0 }}
          transition={{ duration: durations.instant }}
        >
          {cursorChar}
        </motion.span>
      )}
    </span>
  )
}

// === 逐词打字效果 ===
interface WordTypewriterProps {
  words: string[]
  className?: string
  wordDelay?: number // 每个词的显示时间（毫秒）
  fadeDuration?: number // 淡入淡出持续时间（毫秒）
  cursor?: boolean
  cursorClassName?: string
}

export function WordTypewriter({
  words,
  className = '',
  wordDelay = 2000,
  fadeDuration = 300,
  cursor = true,
  cursorClassName = '',
}: WordTypewriterProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isVisible, setIsVisible] = useState(true)
  const [showCursor, setShowCursor] = useState(true)

  useEffect(() => {
    let timeout: NodeJS.Timeout
    
    // 淡出
    timeout = setTimeout(() => {
      setIsVisible(false)
      
      // 切换到下一个词
      timeout = setTimeout(() => {
        setCurrentIndex(prev => (prev + 1) % words.length)
        setIsVisible(true)
      }, fadeDuration)
    }, wordDelay)
    
    // 光标闪烁
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev)
    }, 500)
    
    return () => {
      clearTimeout(timeout)
      clearInterval(cursorInterval)
    }
  }, [words, wordDelay, fadeDuration, currentIndex])

  return (
    <span className={cn('inline', className)}>
      <motion.span
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: isVisible ? 1 : 0, y: isVisible ? 0 : -20 }}
        transition={{ 
          duration: fadeDuration / 1000, 
          ease: easings.smooth 
        }}
        className="inline-block"
      >
        {words[currentIndex]}
      </motion.span>
      {cursor && (
        <motion.span
          className={cn('inline-block', cursorClassName)}
          animate={{ opacity: showCursor ? 1 : 0 }}
          transition={{ duration: durations.instant }}
        >
          |
        </motion.span>
      )}
    </span>
  )
}

// === 光标闪烁组件（独立使用）===
export function BlinkingCursor({ 
  char = '|', 
  className = '' 
}: { 
  char?: string
  className?: string 
}) {
  const [visible, setVisible] = useState(true)
  
  useEffect(() => {
    const interval = setInterval(() => setVisible(prev => !prev), 500)
    return () => clearInterval(interval)
  }, [])
  
  return (
    <motion.span
      className={className}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: durations.instant }}
    >
      {char}
    </motion.span>
  )
}
