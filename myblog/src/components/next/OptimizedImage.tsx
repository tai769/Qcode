'use client';

import Image from 'next/image';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  priority?: boolean;
  fill?: boolean;
  placeholder?: 'blur' | 'empty';
  blurDataURL?: string;
}

/**
 * 优化的图片组件
 * 
 * 特性：
 * - 使用 Next.js Image 组件
 * - 懒加载（非 priority 图片）
 * - 加载占位符
 * - 骨架屏效果
 * - 响应式优化
 */
export default function OptimizedImage({
  src,
  alt,
  width,
  height,
  className = '',
  priority = false,
  fill = false,
  placeholder = 'empty',
  blurDataURL,
}: OptimizedImageProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  return (
    <div 
      className={cn(
        'relative overflow-hidden',
        fill ? 'absolute inset-0' : 'inline-block',
        className
      )}
      style={fill ? undefined : { width: width || 'auto', height: height || 'auto' }}
    >
      {/* 骨架屏 */}
      {isLoading && (
        <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-gray-800 via-gray-700 to-gray-800" />
      )}
      
      {/* 错误状态 */}
      {hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-800/50">
          <span className="text-white/50">图片加载失败</span>
        </div>
      )}
      
      {/* 图片 */}
      <Image
        src={src}
        alt={alt}
        width={width || 800}
        height={height || 600}
        fill={fill}
        className={cn(
          'transition-opacity duration-500',
          isLoading ? 'opacity-0' : 'opacity-100',
          hasError ? 'hidden' : ''
        )}
        priority={priority}
        placeholder={placeholder}
        blurDataURL={blurDataURL}
        loading={priority ? undefined : 'lazy'}
        onLoad={() => setIsLoading(false)}
        onError={() => {
          setIsLoading(false);
          setHasError(true);
        }}
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      />
    </div>
  );
}
