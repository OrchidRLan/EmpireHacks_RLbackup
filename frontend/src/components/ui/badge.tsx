import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full text-xs font-semibold px-2.5 py-0.5 transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-[#6A5CFF]/10 text-[#6A5CFF] dark:bg-yellow-400/10 dark:text-yellow-400',
        secondary: 'bg-[#EBEBEC] text-[#4A4A4A] dark:bg-[#242424] dark:text-yellow-400/70',
        success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
        warning: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
        destructive: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400',
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
