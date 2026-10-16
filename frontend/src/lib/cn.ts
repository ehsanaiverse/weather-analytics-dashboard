/**
 * Join class names, dropping falsy values.
 *
 * A tiny stand-in for `clsx` so the project keeps its dependency list to the
 * stack the dashboard needs. It is not a Tailwind merge utility: conflicting
 * classes are resolved by CSS order, so components should not rely on override
 * semantics.
 */
export function cn(...classes: ReadonlyArray<string | false | null | undefined>): string {
  return classes.filter((value): value is string => Boolean(value && value.trim())).join(' ')
}