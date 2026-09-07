import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary";

export function Button({
  variant = "primary",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={cn(
        "inline-flex h-[34px] items-center justify-between rounded-md px-2.5 py-2 text-[13px] transition-colors",
        variant === "primary"
          ? "bg-primary text-inverse hover:bg-accent"
          : "border border-border bg-surface text-on-surface hover:border-tertiary",
        className,
      )}
      {...props}
    />
  );
}