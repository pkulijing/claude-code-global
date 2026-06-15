import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** 合并 className：clsx 条件拼接 + tailwind-merge 消解冲突类。shadcn 组件标配。 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
