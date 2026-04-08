/**
 * 类型定义统一导出
 */

export * from './components.types';

// 通用类型
export type Optional<T> = Partial<T>;

export type Nullable<T> = T | null;

export type PromiseResult<T> = Promise<{ data: T; error: null } | { data: null; error: Error }>;
