export const fonts = [
  { value: 'current', label: 'Mặc định · Be Vietnam Pro + Geist' },
  { value: 'be-vietnam', label: 'Be Vietnam Pro · đồng nhất' },
  { value: 'inter', label: 'Inter · hiện đại' },
  { value: 'lora', label: 'Lora + Inter · kiểu biên tập' }
] as const
export type FontChoice = typeof fonts[number]['value']
export type Appearance = { transparency: number; neon: number; motion: number; roundness: number; gradient: boolean; dark: boolean; font: FontChoice }
const KEY = 'dacn-traffic:appearance:v1'
export const defaults: Appearance = { transparency: 35, neon: 15, motion: 30, roundness: 10, gradient: true, dark: false, font: 'current' }
export function readAppearance(): Appearance {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '{}')
    const numbers = (['transparency', 'neon', 'motion', 'roundness'] as const)
    const result = { ...defaults }
    for (const key of numbers) if (typeof saved[key] === 'number' && Number.isFinite(saved[key])) result[key] = Math.max(0, Math.min(100, saved[key]))
    if (typeof saved.gradient === 'boolean') result.gradient = saved.gradient
    if (typeof saved.dark === 'boolean') result.dark = saved.dark
    if (fonts.some(option => option.value === saved.font)) result.font = saved.font
    return result
  } catch { return { ...defaults } }
}
export function applyAppearance(value: Appearance) {
  const element = document.documentElement
  element.dataset.theme = value.dark ? 'dark' : 'light'
  element.dataset.font = value.font
  element.dataset.gradient = String(value.gradient)
  element.dataset.motion = value.motion === 0 ? 'off' : 'on'
  element.style.setProperty('--glass-opacity', String(1 - value.transparency / 100))
  element.style.setProperty('--neon', String(value.neon / 100))
  element.style.setProperty('--motion-duration', String(14 - value.motion * 0.08) + 's')
  element.style.setProperty('--roundness', String(value.roundness / 10))
  try { localStorage.setItem(KEY, JSON.stringify(value)) } catch { /* Giao diện vẫn chạy khi storage bị chặn. */ }
}
