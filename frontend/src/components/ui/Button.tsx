import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '../../lib/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'
type ButtonSize = 'sm' | 'md'

/** Props for {@link Button}. */
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: ButtonVariant
  readonly size?: ButtonSize
  readonly children: ReactNode
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-r from-sky-400 to-cyan-400 hover:from-sky-300 hover:to-cyan-300 text-slate-950 font-semibold shadow-lg shadow-cyan-500/20 active:scale-[0.98]',
  secondary:
    'border border-slate-200/80 bg-white/70 text-slate-800 hover:bg-slate-100 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-100 dark:hover:bg-white/10 dark:hover:border-white/20 active:scale-[0.98] backdrop-blur-md',
  ghost:
    'text-slate-500 hover:bg-slate-200/60 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-white',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs rounded-xl',
  md: 'h-10 px-4 text-sm rounded-xl',
}

/** Glassmorphic button supporting primary, secondary and ghost variants. */
export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  type = 'button',
  children,
  ...rest
}: ButtonProps): ReactNode {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150',
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  )
}