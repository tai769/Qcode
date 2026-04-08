export interface Post {
  slug: string;
  id: string; // 兼容代码中使用的 id 属性
  title: string;
  excerpt: string;
  content: string;
  date: string;
  tags: string[];
  category: string;
  cover?: string;
  author?: string;
  readingTime?: number;
  featured?: boolean;
}

export interface Category {
  slug: string;
  name: string;
  count: number;
}

export interface Tag {
  name: string;
  count: number;
}
