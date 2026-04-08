import { ReactNode, ButtonHTMLAttributes, AnchorHTMLAttributes } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface ButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
  href?: string;
  target?: string;
}

const variants = {
  primary: 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white',
  secondary: 'bg-white/10 backdrop-blur-sm border border-white/20 text-white hover:bg-white/20',
  ghost: 'text-white hover:bg-white/10',
};

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  className,
  onClick,
  href,
  target,
}: ButtonProps) {
  const MotionComponent = motion.button;
  const baseClasses = cn(
    'rounded-lg font-medium transition-all duration-300',
    variants[variant],
    sizes[size],
    className
  );

  const motionProps = {
    whileHover: { scale: 1.05, boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)' },
    whileTap: { scale: 0.95 },
  };

  if (href) {
    return (
      <Link href={href} passHref legacyBehavior>
        <motion.a
          className={baseClasses}
          {...motionProps}
          target={target}
        >
          {children}
        </motion.a>
      </Link>
    );
  }

  return (
    <MotionComponent
      className={baseClasses}
      onClick={onClick}
      {...motionProps}
    >
      {children}
    </MotionComponent>
  );
}
