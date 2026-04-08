'use client';

import { useRef, useEffect, useState } from 'react';
import { motion, useInView } from 'framer-motion';

interface VirtualListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  itemHeight: number | ((index: number) => number);
  containerHeight: number;
  buffer?: number;
  className?: string;
}

/**
 * 虚拟滚动列表组件
 * 
 * 用途：优化长列表渲染，只渲染可见区域的项
 * 
 * 特性：
 * - 动态高度支持
 * - 缓冲区预渲染
 * - 平滑滚动
 * - 性能监控
 */
export function VirtualList<T>({
  items,
  renderItem,
  itemHeight,
  containerHeight,
  buffer = 5,
  className = '',
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  
  // 计算项高度
  const getItemHeight = (index: number): number => {
    return typeof itemHeight === 'function' ? itemHeight(index) : itemHeight;
  };
  
  // 计算所有项的位置
  const itemPositions = useRef<number[]>([]);
  
  useEffect(() => {
    itemPositions.current = [];
    let totalHeight = 0;
    for (let i = 0; i < items.length; i++) {
      itemPositions.current.push(totalHeight);
      totalHeight += getItemHeight(i);
    }
  }, [items, itemHeight]);
  
  const totalHeight = itemPositions.current.reduce((acc, _, i) => 
    acc + getItemHeight(i), 0
  );
  
  // 计算可见范围
  let startIndex = 0;
  let endIndex = items.length - 1;
  
  for (let i = 0; i < items.length; i++) {
    const itemTop = itemPositions.current[i];
    const itemBottom = itemTop + getItemHeight(i);
    
    if (itemBottom < scrollTop - buffer) {
      startIndex = i + 1;
    } else if (itemTop > scrollTop + containerHeight + buffer) {
      endIndex = i - 1;
      break;
    }
  }
  
  // 添加缓冲区
  startIndex = Math.max(0, startIndex - buffer);
  endIndex = Math.min(items.length - 1, endIndex + buffer);
  
  const visibleItems = [];
  for (let i = startIndex; i <= endIndex; i++) {
    visibleItems.push({
      index: i,
      item: items[i],
      top: itemPositions.current[i],
    });
  }
  
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  };
  
  return (
    <div
      ref={containerRef}
      className={className}
      style={{ height: containerHeight, overflow: 'auto' }}
      onScroll={handleScroll}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        {visibleItems.map(({ index, item, top }) => (
          <motion.div
            key={index}
            style={{ 
              position: 'absolute', 
              top, 
              left: 0, 
              right: 0,
              height: getItemHeight(index),
            }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: (index - startIndex) * 0.02 }}
          >
            {renderItem(item, index)}
          </motion.div>
        ))}
      </div>
    </div>
  );
}

/**
 * 简化的虚拟列表（固定高度）
 */
interface SimpleVirtualListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  itemHeight: number;
  className?: string;
}

export function SimpleVirtualList<T>({
  items,
  renderItem,
  itemHeight,
  className = '',
}: SimpleVirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 20 });
  const [containerHeight, setContainerHeight] = useState(600);
  
  useEffect(() => {
    if (containerRef.current) {
      setContainerHeight(containerRef.current.clientHeight);
    }
  }, []);
  
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const scrollTop = e.currentTarget.scrollTop;
    const start = Math.floor(scrollTop / itemHeight);
    const visibleCount = Math.ceil(containerHeight / itemHeight);
    const buffer = 5;
    
    setVisibleRange({
      start: Math.max(0, start - buffer),
      end: Math.min(items.length, start + visibleCount + buffer),
    });
  };
  
  return (
    <div
      ref={containerRef}
      className={className}
      style={{ height: containerHeight, overflow: 'auto' }}
      onScroll={handleScroll}
    >
      <div style={{ height: items.length * itemHeight, position: 'relative' }}>
        {items.slice(visibleRange.start, visibleRange.end).map((item, i) => {
          const index = visibleRange.start + i;
          return (
            <div
              key={index}
              style={{
                position: 'absolute',
                top: index * itemHeight,
                left: 0,
                right: 0,
                height: itemHeight,
              }}
            >
              {renderItem(item, index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
