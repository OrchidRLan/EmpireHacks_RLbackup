import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none',
  {
    variants: {
      variant: {
        default:
          'bg-[#010205] text-white hover:bg-[#1A1A1F] active:bg-[#2A2A2F] shadow-sm dark:bg-yellow-400 dark:text-black dark:hover:bg-yellow-300',
        secondary:
          'bg-[#EBEBEC] text-[#010205] hover:bg-[#E2E2E3] dark:bg-[#1A1A1A] dark:text-white dark:hover:bg-[#242424]',
        outline:
          'border border-[rgba(1,2,5,0.15)] bg-white text-[#010205] hover:bg-[#F0F0F1] dark:border-[rgba(255,215,0,0.20)] dark:bg-transparent dark:text-yellow-400 dark:hover:bg-yellow-400/10',
        ghost:
          'text-[#6B6B6B] hover:bg-[#F0F0F1] hover:text-[#010205] dark:text-yellow-400/60 dark:hover:bg-[#1A1A1A] dark:hover:text-yellow-400',
        destructive:
          'bg-red-500 text-white hover:bg-red-600 shadow-sm',
        success:
          'bg-emerald-500 text-white hover:bg-emerald-600 shadow-sm',
        link:
          'text-[#6A5CFF] underline-offset-4 hover:underline dark:text-yellow-400',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        default: 'h-10 px-4 py-2',
        lg: 'h-12 px-6 text-base',
        icon: 'h-9 w-9',
        'icon-sm': 'h-7 w-7',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props}
    />
  )
)
Button.displayName = 'Button'

export { Button, buttonVariants }
