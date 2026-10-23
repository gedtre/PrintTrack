import type { ComponentProps } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "primary bg-blue-700 text-white hover:bg-blue-800",
        outline:
          "border border-slate-300 bg-white text-slate-800 hover:bg-slate-100",
      },
      size: { default: "h-10 px-4 py-2", sm: "h-8 px-3" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);
/** shadcn/ui-style composable button: Radix Slot, CVA variants and merged Tailwind classes. */
export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}
