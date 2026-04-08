/**
 * 性能监控和 Analytics
 * 
 * 用途：监控 Core Web Vitals 和用户行为
 */

export type Metric = {
  name: string;
  value: number;
  id: string;
  delta?: number;
  labels?: string;
};

/**
 * 报告 Web Vitals 指标到控制台或分析服务
 */
export function reportWebVitalsHandler(metric: Metric) {
  // 开发环境打印到控制台
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Web Vitals] ${metric.name}:`, metric.value, metric);
  }

  // 生产环境可以发送到分析服务
  if (process.env.NODE_ENV === 'production') {
    // 示例：发送到 Google Analytics
    // if (typeof window !== 'undefined' && (window as any).gtag) {
    //   (window as any).gtag('event', metric.name, {
    //     value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
    //     event_label: metric.id,
    //     non_interaction: true,
    //   });
    // }
    
    // 或发送到自定义分析服务
    // sendToAnalyticsService(metric);
  }
}

/**
 * Web Vitals 阈值配置
 */
export const WEB_VITALS_THRESHOLDS = {
  FCP: 3000, // FCP
  LCP: 2500, // LCP
  FID: 100, // FID
  TTFB: 800, // TTFB
  CLS: 0.1, // CLS
  INP: 200, // INP (Interaction to Next Paint)
} as const;

/**
 * 检查指标是否超过阈值
 */
export function isMetricPoor(metric: Metric): boolean {
  const threshold = (WEB_VITALS_THRESHOLDS as any)[metric.name];
  if (!threshold) return false;
  
  return metric.value > threshold;
}

/**
 * 格式化指标值
 */
export function formatMetricValue(metric: Metric): string {
  const value = metric.value;
  
  switch (metric.name) {
    case 'CLS':
      return value.toFixed(3);
    case 'FCP':
    case 'LCP':
    case 'FID':
    case 'TTFB':
    case 'INP':
      return `${Math.round(value)}ms`;
    default:
      return value.toString();
  }
}

/**
 * 性能评分
 */
export function getPerformanceScore(metrics: Metric[]): {
  score: number; // 0-100
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  issues: string[];
} {
  let score = 100;
  const issues: string[] = [];
  
  metrics.forEach(metric => {
    if (isMetricPoor(metric)) {
      score -= 15;
      issues.push(`${metric.name} exceeds threshold: ${formatMetricValue(metric)}`);
    }
  });
  
  score = Math.max(0, Math.min(100, score));
  
  let grade: 'A' | 'B' | 'C' | 'D' | 'F';
  if (score >= 90) grade = 'A';
  else if (score >= 75) grade = 'B';
  else if (score >= 60) grade = 'C';
  else if (score >= 40) grade = 'D';
  else grade = 'F';
  
  return { score, grade, issues };
}
