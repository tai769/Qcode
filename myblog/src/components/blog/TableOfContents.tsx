'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, Menu } from 'lucide-react';

interface Heading {
  id: string;
  text: string;
  level: number;
}

interface TableOfContentsProps {
  headings: Heading[];
}

export default function TableOfContents({ headings }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState('');
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const headingElements = headings.map((h) => document.getElementById(h.id)).filter(Boolean) as HTMLElement[];

      let currentHeading = '';

      for (const element of headingElements) {
        if (element.offsetTop - window.scrollY < 200) {
          currentHeading = element.id;
        }
      }

      setActiveId(currentHeading);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // 初始化

    return () => window.removeEventListener('scroll', handleScroll);
  }, [headings]);

  const handleClick = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      const offset = 100; // 导航栏高度
      const elementPosition = element.getBoundingClientRect().top + window.scrollY;
      window.scrollTo({
        top: elementPosition - offset,
        behavior: 'smooth',
      });
    }
  };

  return (
    <div className="fixed right-4 md:right-8 top-24 z-40">
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="glass rounded-2xl overflow-hidden"
      >
        {/* 移动端切换按钮 */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="md:hidden w-full p-3 flex items-center justify-center text-white hover:bg-white/10 transition-colors"
          aria-label="切换目录"
        >
          <Menu size={20} />
        </button>

        <AnimatePresence>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="p-4 w-60"
            >
              <h4 className="text-white/60 text-xs font-medium uppercase tracking-wider mb-3">
                目录
              </h4>
              
              <nav className="space-y-1">
                {headings.map((heading) => (
                  <motion.button
                    key={heading.id}
                    onClick={() => handleClick(heading.id)}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: heading.level * 0.05 }}
                    className={`
                      w-full text-left px-3 py-2 rounded-lg transition-all duration-300
                      flex items-start gap-2 group
                      ${activeId === heading.id 
                        ? 'bg-gradient-to-r from-purple-500/20 to-cyan-500/20 text-white' 
                        : 'text-white/60 hover:text-white hover:bg-white/5'
                      }
                    `}
                    style={{ paddingLeft: `${heading.level * 12 + 12}px` }}
                  >
                    <motion.span
                      animate={{ rotate: activeId === heading.id ? 90 : 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ChevronRight size={14} />
                    </motion.span>
                    <span className="text-sm line-clamp-2">
                      {heading.text}
                    </span>
                  </motion.button>
                ))}
              </nav>

              {/* 装饰性渐变 */}
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="h-1 w-full bg-gradient-to-r from-purple-500/0 via-purple-500/50 to-purple-500/0 rounded-full" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

// 解析文章内容中的标题
export function parseHeadings(content: string): Heading[] {
  const headingRegex = /^(#{2,3})\s+(.+)$/gm;
  const headings: Heading[] = [];
  let match;
  let headingCounter = 0;

  while ((match = headingRegex.exec(content)) !== null) {
    const level = match[1].length; // 2 for ##, 3 for ###
    const text = match[2].trim();
    const id = `heading-${headingCounter++}`;

    headings.push({ id, text, level: level - 1 }); // 转换为 1 和 2 级
  }

  return headings;
}
