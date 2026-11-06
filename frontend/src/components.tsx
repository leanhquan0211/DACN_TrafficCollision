import { useState, type ReactNode } from 'react'
import { Dialog } from 'radix-ui'
import { AlertCircle, ArrowUpRight, ChevronDown, Download, Info, X } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { History, Run } from './types'
import { count, download, percent } from './api'

export function Panel({ title, subtitle, action, children, className = '' }: { title?: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-heading"><div>{title && <h2>{title}</h2>}{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>
}
export function Empty({ title = 'Chưa có dữ liệu', children }: { title?: string; children?: ReactNode }) {
  return <div className="empty"><Info size={24}/><h3>{title}</h3><p>{children || 'Artifact chưa được phục hồi trên máy này. Dashboard sẽ hiển thị khi có file thật.'}</p></div>
}
export function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return <div className="error-state" role="alert"><AlertCircle/><div><h2>Chưa đọc được dữ liệu</h2><p>{message}</p><p>Kiểm tra API local đang chạy ở cổng 8765.</p><button className="button" onClick={retry}>Thử lại</button></div></div>
}
export function Loading() { return <div className="loading" role="status"><span className="spinner"/>Đang đọc kết quả thật…</div> }
export function Status({ value }: { value: string }) {
  const label: Record<string, string> = { completed: 'Đã hoàn tất', evidence_present: 'Có bằng chứng chẩn đoán', COMPLETE: 'Kaggle đã kết thúc · chờ kiểm file', RUNNING: 'Kaggle đang chạy', QUEUED: 'Kaggle đang chờ', ERROR: 'Kaggle báo lỗi', submitted: 'Đã gửi Kaggle · chưa có file local', withdrawn: 'Đã thu hồi', unknown: 'Chưa xác minh trạng thái' }
  return <span className={`status ${value}`}><span/>{label[value] || value}</span>
}
export const metricDefinitions: Record<string, string> = {
  mAP50: 'Diện tích dưới đường precision–recall tại IoU 0,50, lấy trung bình các lớp. B0 có một lớp accident. Không phải accuracy video.',
  'mAP50–95': 'Trung bình AP ở 10 ngưỡng IoU 0,50 đến 0,95, bước 0,05. Hộp phải khớp chặt hơn; Ultralytics bản này dùng chỉ số này chọn best.',
  Precision: 'TP / (TP + FP): tỷ lệ hộp dự đoán đúng. Theo dõi để hạn chế báo nhầm. Phải đọc cùng confidence và recall.',
  Recall: 'TP / (TP + FN): tỷ lệ vùng thật tìm được. Theo dõi để hạn chế bỏ sót. Hiện là recall bbox, chưa phải sự kiện.',
  F1: '2PR / (P + R): trung bình điều hòa precision và recall tại cùng operating point; không trộn P/R từ hai ngưỡng khác nhau.',
  IoU: 'Diện tích giao chia diện tích hợp của hai hộp. IoU 0,60 đạt yêu cầu 0,50 nhưng chưa đạt 0,75. Ngưỡng càng cao, đòi hộp càng sát.'
}
export function InfoTip({ label }: { label: string }) {
  return <span className="info-tip"><button type="button" aria-label={`Giải thích ${label}`}><Info size={14}/></button><span role="tooltip">{metricDefinitions[label] || label}</span></span>
}
export function Metric({ label, value, note, tone = '' }: { label: string; value: string; note?: string; tone?: string }) {
  return <div className={`metric ${tone}`}><div className="metric-label">{label}<InfoTip label={label}/></div><strong>{value}</strong>{note && <span className="metric-note">{note}</span>}</div>
}
export function Modal({ title, trigger, children, wide = false }: { title: string; trigger: ReactNode; children: ReactNode; wide?: boolean }) {
  return <Dialog.Root><Dialog.Trigger asChild>{trigger}</Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className={`modal-content ${wide ? 'wide' : ''}`}><div className="modal-head"><Dialog.Title>{title}</Dialog.Title><Dialog.Close className="icon-button" aria-label="Đóng"><X/></Dialog.Close></div><Dialog.Description className="sr-only">Chi tiết dữ liệu nguồn đã lưu của đồ án.</Dialog.Description>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>
}
export function ImageGallery({ run }: { run: Run }) {
  return <div className="curve-grid">{run.charts?.map(chart => <Modal key={chart.name} title={chart.name} wide trigger={<button className="curve-tile"><img src={chart.url} alt={`Biểu đồ gốc ${chart.name}`} loading="lazy"/><span>{chart.name}<ArrowUpRight size={15}/></span></button>}><img className="full-image" src={chart.url} alt={chart.name}/><p className="caption">Ảnh gốc · {run.id}/{chart.source}</p></Modal>)}</div>
}
const lineMetrics = [ ['map50', 'mAP50', 'var(--chart-map50)'], ['map95', 'mAP50–95', 'var(--chart-map95)'], ['precision', 'Precision', 'var(--chart-precision)'], ['recall', 'Recall', 'var(--chart-recall)'] ]
export function EpochChart({ history, best }: { history: History[]; best: number | null }) {
  const [active, setActive] = useState(['map50', 'map95'])
  const [end, setEnd] = useState(0)
  const [smooth, setSmooth] = useState(false)
  const [table, setTable] = useState(false)
  if (!history.length) return <Empty/>
  const visible = history.filter(r => !end || r.epoch <= end)
  const data = visible.map((r, index) => {
    const out: Record<string, number | null> = { ...r }
    if (smooth) for (const [key] of lineMetrics) out[key] = visible.slice(Math.max(0, index - 2), index + 1).reduce((sum, row) => sum + (row[key] ?? 0), 0) / Math.min(index + 1, 3)
    return out
  })
  const exportCsv = () => download('epochs.csv', ['epoch,map50,map95,precision,recall', ...visible.map(r => [r.epoch, r.map50, r.map95, r.precision, r.recall].join(','))].join('\n'))
  return <><div className="chart-toolbar"><div className="checks">{lineMetrics.map(([key, label, color]) => <label key={key}><input type="checkbox" checked={active.includes(key)} onChange={() => setActive(prev => prev.includes(key) ? prev.filter(v => v !== key) : [...prev, key])}/><span className="legend-dot" style={{ background: color }}/>{label}</label>)}</div><button className="text-button" onClick={exportCsv}><Download size={15}/>CSV</button></div>
    <div className="chart-canvas"><ResponsiveContainer width="100%" height="100%" minWidth={0}><LineChart data={data} margin={{ top: 20, right: 20, left: -10, bottom: 8 }}><CartesianGrid vertical={false} stroke="var(--color-rule)"/><XAxis dataKey="epoch" type="number" domain={['dataMin', 'dataMax']} tickCount={6} tickLine={false} axisLine={false} tick={{ fill: 'var(--color-muted)', fontSize: 12 }} label={{ value: 'Epoch', position: 'insideBottomRight', offset: -4, fill: 'var(--color-muted)' }}/><YAxis domain={[0, 1]} tickFormatter={v => `${Math.round(v * 100)}%`} axisLine={false} tickLine={false} tick={{ fill: 'var(--color-muted)', fontSize: 12 }}/><Tooltip contentStyle={{ background: 'var(--color-panel)', border: '1px solid var(--color-rule)', color: 'var(--color-ink)' }} formatter={(v, name) => [percent(Number(v)), name]} labelFormatter={v => `Epoch ${v}${smooth ? ' · TB trượt 3 điểm' : ''}`}/>{best && <ReferenceLine x={best} stroke="var(--color-muted)" strokeDasharray="4 4" label={{ value: `Best ${best}`, position: 'insideTopRight', fill: 'var(--color-muted)', fontSize: 11 }}/>} {lineMetrics.filter(([key]) => active.includes(key)).map(([key, name, color]) => <Line key={key} dataKey={key} name={name} stroke={color} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} type="linear" isAnimationActive={false}/>)}</LineChart></ResponsiveContainer></div>
    <div className="chart-bottom"><label>Đến epoch <b>{end || history.at(-1)?.epoch}</b><input aria-label="Chọn epoch cuối hiển thị" type="range" min={1} max={history.at(-1)?.epoch || 1} value={end || history.at(-1)?.epoch} onChange={e => setEnd(Number(e.target.value))}/></label><label className="check"><input type="checkbox" checked={smooth} onChange={e => setSmooth(e.target.checked)}/>TB trượt 3 điểm</label><button className="text-button" onClick={() => setTable(!table)} aria-expanded={table}>Bảng số <ChevronDown size={14}/></button></div>
    {smooth && <p className="notice">Đang xem trung bình trượt; tắt để đọc dữ liệu raw. Best vẫn lấy từ metric raw, không tính lại.</p>}
    {table && <div className="table-scroll"><table><thead><tr><th>Epoch</th><th>mAP50</th><th>mAP50–95</th><th>P (log)</th><th>R (log)</th></tr></thead><tbody>{visible.map(r => <tr key={r.epoch}><td>{r.epoch}</td><td>{percent(r.map50)}</td><td>{percent(r.map95)}</td><td>{percent(r.precision)}</td><td>{percent(r.recall)}</td></tr>)}</tbody></table></div>}
  </>
}
export function Counts({ run }: { run: Run }) { return <div className="count-strip"><span><i className="dot tp"/>TP <b>{count(run.fixed.tp)}</b></span><span><i className="dot fp"/>FP <b>{count(run.fixed.fp)}</b></span><span><i className="dot fn"/>FN <b>{count(run.fixed.fn)}</b></span></div> }
export function RoadArtwork() {
  return <svg className="road-art" viewBox="0 0 440 280" fill="none" aria-hidden="true"><defs><linearGradient id="road-surface" x2="1" y2="1"><stop stopColor="var(--color-art-light)"/><stop offset="1" stopColor="var(--color-art-dark)"/></linearGradient></defs><path d="M42 231 285 88 400 154 156 295" fill="url(#road-surface)"/><path d="m101 3 246 143-121 71L-19 74" fill="var(--color-art-cross)"/><path d="m76 253 280-165M55 47l236 138" stroke="var(--color-art-mark)" strokeWidth="2" strokeDasharray="12 12"/><path className="trajectory" d="m62 233 144-84q25-14 43-2l56 33" stroke="var(--color-accent)" strokeWidth="2" strokeDasharray="5 6"/><g transform="translate(163 128)"><path d="m0 13 33-19 29 17-33 20Z" fill="var(--color-art-car)"/><path d="m0 13v12l29 17V31m0 0 33-20v12L29 42" fill="var(--color-art-dark)"/><path d="m8 13 25-14 19 11-25 14Z" fill="var(--color-panel)"/></g><path d="m148 133 48-28 43 25v39l-48 28-43-25Z" stroke="var(--color-accent)" strokeWidth="1.5"/><circle cx="239" cy="130" r="3" fill="var(--color-accent)"/><path d="M297 34v80m0-80 39-23 49 28-39 23Z" stroke="var(--color-art-dark)" strokeWidth="3"/><path d="m297 34 49 28v28l-49-28Z" fill="var(--color-art-car)"/><path d="m346 62 39-23v28l-39 23Z" fill="var(--color-art-dark)"/><circle cx="362" cy="65" r="8" fill="var(--color-accent)"/><path d="m359 68 24 13" stroke="var(--color-art-mark)"/><path d="M297 114v19m-17 10 17-10 17 10" stroke="var(--color-art-dark)" strokeWidth="3"/></svg>
}
