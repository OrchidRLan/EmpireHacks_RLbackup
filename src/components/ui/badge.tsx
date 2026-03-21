import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full text-xs font-semibold px-2.5 py-0.5 transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
        secondary: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
        success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300',
        warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
        destructive: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
        outline: 'border border-current bg-transparent',
        score: 'bg-emerald-500 text-white font-bold',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
