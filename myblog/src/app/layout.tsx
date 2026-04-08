import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import FluidBackground from '@/components/background/FluidBackground';
import Navbar from '@/components/layout/Navbar';
import { ScrollProgress } from '@/components/animation/ScrollProgress';
import { reportWebVitalsHandler } from '@/lib/analytics';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'MyBlog - 个人博客',
  description: '使用Next.js 14和React Three Fiber构建的现代化个人博客',
};

export { reportWebVitalsHandler as reportWebVitals };

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <ScrollProgress />
        <FluidBackground />
        <Navbar />
        <main className="pt-24">
          {children}
        </main>
      </body>
    </html>
  );
}
