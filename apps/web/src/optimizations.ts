/**
 * Frontend optimization utilities for React/TypeScript.
 * Includes hooks, components, and utilities for performance.
 */

import React, { useCallback, useRef, useEffect, useMemo } from 'react'

// ====================
// HOOKS
// ====================

/**
 * Debounce hook for expensive operations
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}

/**
 * Throttle hook for frequent updates
 */
export function useThrottle<T>(value: T, interval: number): T {
  const [throttledValue, setThrottledValue] = React.useState<T>(value)
  const lastUpdated = useRef<number>(Date.now())

  useEffect(() => {
    const now = Date.now()
    if (now >= lastUpdated.current + interval) {
      lastUpdated.current = now
      setThrottledValue(value)
    } else {
      const handler = setTimeout(() => {
        lastUpdated.current = Date.now()
        setThrottledValue(value)
      }, interval - (now - lastUpdated.current))

      return () => clearTimeout(handler)
    }
  }, [value, interval])

  return throttledValue
}

/**
 * Lazy loading image hook
 */
export function useLazyImage(src: string) {
  const [imageSrc, setImageSrc] = React.useState<string>('')
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    if (!src) return

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setImageSrc(src)
            observer.unobserve(entry.target)
          }
        })
      },
      { rootMargin: '50px' }
    )

    if (imgRef.current) {
      observer.observe(imgRef.current)
    }

    return () => observer.disconnect()
  }, [src])

  return { imageSrc, imgRef }
}

/**
 * Intersection Observer hook for visibility detection
 */
export function useIntersection(
  ref: React.RefObject<Element>,
  options?: IntersectionObserverInit
) {
  const [isVisible, setIsVisible] = React.useState(false)

  useEffect(() => {
    if (!ref.current) return

    const observer = new IntersectionObserver(([entry]) => {
      setIsVisible(entry.isIntersecting)
    }, options)

    observer.observe(ref.current)

    return () => observer.disconnect()
  }, [ref, options])

  return isVisible
}

// ====================
// UTILITIES
// ====================

/**
 * Debounce function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

/**
 * Throttle function
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean
  return function (...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

/**
 * Measure web vitals
 */
export interface PerformanceMetrics {
  fcp: number // First Contentful Paint
  lcp: number // Largest Contentful Paint
  cls: number // Cumulative Layout Shift
  tti: number // Time to Interactive
  fid: number // First Input Delay
}

export function measureWebVitals(): Promise<Partial<PerformanceMetrics>> {
  return new Promise((resolve) => {
    const metrics: Partial<PerformanceMetrics> = {}

    // Use PerformanceObserver if available
    if ('PerformanceObserver' in window) {
      // Measure LCP
      try {
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const lastEntry = entries[entries.length - 1]
          metrics.lcp = lastEntry.startTime
        })
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })
      } catch (e) {
        // Silently fail if not supported
      }

      // Measure CLS
      try {
        const clsObserver = new PerformanceObserver((list) => {
          let cls = 0
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) {
              cls += (entry as any).value
            }
          }
          metrics.cls = cls
        })
        clsObserver.observe({ entryTypes: ['layout-shift'] })
      } catch (e) {
        // Silently fail if not supported
      }
    }

    // Measure navigation timing
    if ('performance' in window) {
      const perfData = window.performance.timing
      const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart
      
      if (pageLoadTime > 0) {
        metrics.tti = pageLoadTime
      }
    }

    // Report after a short delay
    setTimeout(() => {
      resolve(metrics)
    }, 5000)
  })
}

/**
 * Optimized API client with retry logic and timeout
 */
export class OptimizedApiClient {
  private requestCache = new Map<string, { data: any; timestamp: number }>()
  private cacheTimeout = 5 * 60 * 1000 // 5 minutes
  private readonly defaultTimeout = 30000
  private readonly maxRetries = 3

  private getHeaders(): HeadersInit {
    const token = typeof window !== 'undefined' 
      ? localStorage.getItem('shivaai_token')
      : null
    
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit & { timeout?: number; retries?: number } = {}
  ): Promise<T> {
    const { timeout = this.defaultTimeout, retries = this.maxRetries, ...fetchOptions } = options

    const response = await this.retryWithBackoff(
      () => this.fetchWithTimeout(endpoint, fetchOptions, timeout),
      retries
    )

    if (!response.ok) {
      let message = `Request failed (${response.status})`
      try {
        const payload = await response.json()
        message = payload.user_message || payload.message || payload.detail || message
      } catch {
        // Keep the status-based message when the body is not JSON.
      }
      throw new Error(message)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  }

  private async fetchWithTimeout(
    endpoint: string,
    options: RequestInit,
    timeout: number
  ): Promise<Response> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const apiUrl = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
      const response = await fetch(`${apiUrl}${endpoint}`, {
        ...options,
        headers: this.getHeaders(),
        signal: controller.signal,
      })
      return response
    } finally {
      clearTimeout(timeoutId)
    }
  }

  private async retryWithBackoff<T>(
    fn: () => Promise<T>,
    maxAttempts: number
  ): Promise<T> {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await fn()
      } catch (error) {
        if (attempt === maxAttempts) throw error

        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 10000)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
    throw new Error('Retry failed')
  }

  async get<T>(endpoint: string): Promise<T> {
    // Check cache
    const cached = this.requestCache.get(endpoint)
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data
    }

    const response = await this.request<T>(endpoint, { method: 'GET' })
    this.requestCache.set(endpoint, { data: response, timestamp: Date.now() })
    return response
  }

  async post<T>(endpoint: string, body?: Record<string, any>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  }

  clearCache(): void {
    this.requestCache.clear()
  }
}

export const optimizedApiClient = new OptimizedApiClient()
