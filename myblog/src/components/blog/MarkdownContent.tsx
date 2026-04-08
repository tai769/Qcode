'use client';

import React, { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { motion } from 'framer-motion';

interface MarkdownContentProps {
  content: string;
}

// 定义代码节点类型
interface CodeProps {
  className?: string;
  children?: React.ReactNode;
  [key: string]: any;
}

export default function MarkdownContent({ content }: MarkdownContentProps) {
  // 添加ID到标题，以便目录导航能工作
  useEffect(() => {
    const headings = document.querySelectorAll('article h2, article h3');
    let headingCounter = 0;

    headings.forEach((heading) => {
      const id = `heading-${headingCounter++}`;
      heading.id = id;
    });
  }, [content]);

  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="prose prose-invert prose-lg max-w-none"
    >
      <ReactMarkdown
        components={{
          // 自定义代码块样式
          code({ className, children, ...props }: CodeProps) {
            const match = /language-(\w+)/.exec(className || '');
            const inline = !match;
            
            return !inline && match ? (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code
                className="bg-white/10 px-1.5 py-0.5 rounded text-purple-300 text-sm"
                {...props}
              >
                {children}
              </code>
            );
          },
          // 自定义标题样式
          h2({ children }) {
            return (
              <motion.h2
                initial={{ opacity: 0, y: -10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="text-2xl md:text-3xl font-bold text-white mt-12 mb-6 pb-3 border-b border-white/10"
              >
                {children}
              </motion.h2>
            );
          },
          h3({ children }) {
            return (
              <motion.h3
                initial={{ opacity: 0, y: -10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="text-xl md:text-2xl font-semibold text-white mt-8 mb-4"
              >
                {children}
              </motion.h3>
            );
          },
          // 自定义段落样式
          p({ children }) {
            return (
              <motion.p
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                className="text-white/80 leading-relaxed mb-6"
              >
                {children}
              </motion.p>
            );
          },
          // 自定义列表样式
          ul({ children }) {
            return (
              <motion.ul
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                className="list-disc list-inside mb-6 space-y-2 text-white/80"
              >
                {children}
              </motion.ul>
            );
          },
          li({ children }) {
            return <li className="pl-2">{children}</li>;
          },
          // 自定义块引用样式
          blockquote({ children }) {
            return (
              <motion.blockquote
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                className="border-l-4 border-purple-500 pl-6 py-2 my-6 bg-purple-500/10 rounded-r-lg"
              >
                {children}
              </motion.blockquote>
            );
          },
          // 自定义链接样式
          a({ children, href }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-400 hover:text-cyan-300 underline underline-offset-4 hover:underline-offset-2 transition-all"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </motion.article>
  );
}
