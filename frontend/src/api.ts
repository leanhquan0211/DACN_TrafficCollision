import { useCallback, useEffect, useState } from 'react'

export async function get<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `Không đọc được dữ liệu (${response.status}).`)
  }
  return response.json() as Promise<T>
}

export function useApi<T>(url: string, refreshSeconds = 0, enabled = true) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [version, setVersion] = useState(0)
  const [readAt, setReadAt] = useState<number | null>(null)
  const refresh = useCallback(() => setVersion(v => v + 1), [])
  useEffect(() => {
    if (!enabled) { setData(null); setError(''); setLoading(false); return }
    const controller = new AbortController()
    setLoading(true); setData(null); setError('')
    let pending = false
    const load = async () => {
      if (pending) return
      pending = true
      try {
        const result = await get<T>(url, controller.signal)
        if (!controller.signal.aborted) { setData(result); setError(''); setReadAt(Date.now()) }
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Chưa kết nối được API.')
      } finally {
        pending = false
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    const timer = refreshSeconds ? window.setInterval(() => void load(), refreshSeconds * 1000) : undefined
    return () => { controller.abort(); if (timer) clearInterval(timer) }
  }, [url, version, refreshSeconds, enabled])
  return { data, error, loading, refresh, readAt }
}

export const percent = (value: number | null | undefined) => value == null ? '—' : new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(value * 100) + '%'
export const count = (value: number | undefined | null) => value == null ? '—' : new Intl.NumberFormat('vi-VN').format(value)
export const date = (value: number | null) => value ? new Date(value * 1000).toLocaleString('vi-VN') : 'Chưa có mốc thời gian'

export function download(name: string, content: string, type = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob(['\ufeff', content], { type }))
  const a = document.createElement('a'); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url)
}
