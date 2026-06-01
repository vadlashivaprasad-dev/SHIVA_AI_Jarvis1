// apps/web/src/components/ui/Button.tsx
/**
 * Button Component
 * Flexible button component with multiple variants and sizes
 */

import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  // Base styles
  'inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neural-500',
  {
    variants: {
      variant: {
        primary: 'bg-neural-600 text-white hover:bg-neural-700 active:bg-neural-800 shadow-base hover:shadow-lg',
        secondary: 'border-2 border-neural-500 text-neural-600 hover:bg-neural-50 active:bg-neural-100',
        ghost: 'text-neural-600 hover:bg-neural-50 active:bg-neural-100',
        danger: 'bg-error text-white hover:bg-red-700 active:bg-red-800',
        success: 'bg-success text-white hover:opacity-90',
        icon: 'p-2 hover:bg-neural-50 active:bg-neural-100',
      },
      size: {
        sm: 'h-8 px-3 text-sm gap-2',
        md: 'h-10 px-4 text-base gap-2',
        lg: 'h-12 px-6 text-lg gap-3',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  children: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, disabled, children, ...props }, ref) => (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={isLoading || disabled}
      ref={ref}
      {...props}
    >
      {isLoading ? (
        <>
          <Spinner size="sm" />
          <span className="opacity-50">Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  )
);

Button.displayName = 'Button';


// apps/web/src/components/ui/Input.tsx
/**
 * Input Component
 * Text input with validation states and icons
 */

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  status?: 'default' | 'error' | 'success' | 'warning';
  icon?: React.ReactNode;
  label?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, status = 'default', icon, label, helperText, ...props }, ref) => {
    const statusClasses = {
      default: 'border-gray-300 focus:border-neural-500 focus:ring-neural-500',
      error: 'border-error focus:border-error focus:ring-error',
      success: 'border-success focus:border-success focus:ring-success',
      warning: 'border-warning focus:border-warning focus:ring-warning',
    };

    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-text-primary mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">{icon}</div>}
          <input
            ref={ref}
            className={cn(
              'w-full px-4 py-2 border-2 rounded-lg text-base transition-colors',
              'placeholder:text-text-tertiary',
              'focus:outline-none focus:ring-2 focus:ring-offset-0',
              'disabled:bg-gray-100 disabled:cursor-not-allowed',
              icon && 'pl-10',
              statusClasses[status],
              className
            )}
            {...props}
          />
        </div>
        {helperText && (
          <p className={cn(
            'text-sm mt-1',
            status === 'error' ? 'text-error' : status === 'success' ? 'text-success' : 'text-text-secondary'
          )}>
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';


// apps/web/src/components/ui/Card.tsx
/**
 * Card Component
 * Flexible card container with sections
 */

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'base' | 'elevated' | 'outlined';
  padding?: 'sm' | 'md' | 'lg';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'base', padding = 'md', ...props }, ref) => {
    const variants = {
      base: 'bg-white border border-gray-200 rounded-lg',
      elevated: 'bg-white rounded-lg shadow-lg',
      outlined: 'bg-transparent border-2 border-neural-300 rounded-lg',
    };

    const paddings = {
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
    };

    return (
      <div
        ref={ref}
        className={cn(
          variants[variant],
          paddings[padding],
          'transition-shadow duration-200',
          className
        )}
        {...props}
      />
    );
  }
);

Card.displayName = 'Card';

interface CardSectionProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
}

const CardHeader = ({ className, ...props }: CardSectionProps) => (
  <div className={cn('border-b border-gray-200 pb-4 mb-4', className)} {...props} />
);

const CardBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('', className)} {...props} />
);

const CardFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('border-t border-gray-200 pt-4 mt-4 flex gap-2', className)} {...props} />
);

Card.Header = CardHeader;
Card.Body = CardBody;
Card.Footer = CardFooter;


// apps/web/src/components/ui/Badge.tsx
/**
 * Badge Component
 * Compact indicator for status or category
 */

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md' | 'lg';
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    const variants = {
      primary: 'bg-neural-100 text-neural-700',
      secondary: 'bg-blue-100 text-blue-700',
      success: 'bg-green-100 text-success',
      warning: 'bg-amber-100 text-warning',
      error: 'bg-red-100 text-error',
      info: 'bg-blue-50 text-blue-600',
    };

    const sizes = {
      sm: 'px-2 py-1 text-xs font-medium',
      md: 'px-3 py-1.5 text-sm font-medium',
      lg: 'px-4 py-2 text-base font-medium',
    };

    return (
      <span
        ref={ref}
        className={cn(
          'inline-block rounded-full',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    );
  }
);

Badge.displayName = 'Badge';


// apps/web/src/components/ui/Spinner.tsx
/**
 * Spinner Component
 * Loading indicator with multiple variants
 */

import { motion } from 'framer-motion';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'dots' | 'bars';
  color?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  variant = 'default',
  color = '#7C51DC',
}) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  if (variant === 'dots') {
    return (
      <div className={cn(sizes[size], 'flex items-center justify-center gap-1')}>
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: color }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, delay: i * 0.2, repeat: Infinity }}
          />
        ))}
      </div>
    );
  }

  if (variant === 'bars') {
    return (
      <div className={cn(sizes[size], 'flex items-center justify-center gap-1')}>
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1 flex-1"
            style={{ backgroundColor: color }}
            animate={{ scaleY: [0.4, 1, 0.4] }}
            transition={{ duration: 1, delay: i * 0.15, repeat: Infinity }}
          />
        ))}
      </div>
    );
  }

  // Default spinner
  return (
    <motion.div
      className={cn(sizes[size], 'border-2 border-gray-200 rounded-full')}
      style={{
        borderTopColor: color,
      }}
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
    />
  );
};


// apps/web/src/components/ui/Modal.tsx
/**
 * Modal Dialog Component
 */

import { motion, AnimatePresence } from 'framer-motion';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, children }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/50 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          
          {/* Modal */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            <div className="bg-white rounded-xl shadow-2xl max-w-md w-full">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

interface ModalSectionProps extends React.HTMLAttributes<HTMLDivElement> {}

const ModalHeader = ({ className, ...props }: ModalSectionProps) => (
  <div className={cn('px-6 py-4 border-b border-gray-200', className)} {...props} />
);

const ModalBody = ({ className, ...props }: ModalSectionProps) => (
  <div className={cn('px-6 py-4', className)} {...props} />
);

const ModalFooter = ({ className, ...props }: ModalSectionProps) => (
  <div className={cn('px-6 py-4 border-t border-gray-200 flex gap-3 justify-end', className)} {...props} />
);

Modal.Header = ModalHeader;
Modal.Body = ModalBody;
Modal.Footer = ModalFooter;


// apps/web/src/components/ui/Toast.tsx
/**
 * Toast Notification Component
 */

interface ToastProps {
  variant?: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
  onClose?: () => void;
}

export const Toast: React.FC<ToastProps> = ({
  variant = 'info',
  message,
  duration = 3000,
  onClose,
}) => {
  const [isOpen, setIsOpen] = React.useState(true);

  React.useEffect(() => {
    if (duration) {
      const timer = setTimeout(() => {
        setIsOpen(false);
        onClose?.();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const variants = {
    success: 'bg-green-50 text-success border-green-200',
    error: 'bg-red-50 text-error border-red-200',
    warning: 'bg-amber-50 text-warning border-amber-200',
    info: 'bg-blue-50 text-blue-600 border-blue-200',
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className={cn(
            'fixed bottom-4 right-4 px-4 py-3 rounded-lg border',
            variants[variant]
          )}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
        >
          {message}
        </motion.div>
      )}
    </AnimatePresence>
  );
};


// apps/web/src/lib/utils.ts
/**
 * Utility functions
 */

import clsx, { type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
