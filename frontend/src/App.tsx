import { useEffect, useState } from 'react'
import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router'
import { Dialog, Popover } from 'radix-ui'
import { Activity, ArrowUpRight, BookOpen, Camera, ChartNoAxesCombined, ChevronDown, Compass, Database, GitCompareArrows, LayoutDashboard, Menu, Moon, RefreshCw, Settings2, Sun, X } from 'lucide-react'
import { useApi } from './api'
import type { Inventory } from './types'
import { applyAppearance, defaults, fonts, readAppearance, type Appearance, type FontChoice } from './appearance'
import { ErrorState, Loading } from './components'
import { CasesPage, Compare, DataPage, Library, Overview, Training } from './pages'
import { ExplorePage } from './ExplorePage'

const navigation = [ ['/', 'Tổng quan', LayoutDashboard], ['/explore', 'Khám phá đồ án', Compass], ['/training', 'Huấn luyện', Activity], ['/compare', 'So sánh', GitCompareArrows], ['/data', 'Dữ liệu', Database], ['/cases', 'Ảnh & video', Camera], ['/library', 'Tra cứu', BookOpen] ] as const

function AppearanceControls() {
  const [value, setValue] = useState(readAppearance)
  const update = (next: Appearance) => { setValue(next); applyAppearance(next) }
  return <div className="appearance-controls"><button className="icon-button" aria-label={value.dark ? 'Chuyển giao diện sáng' : 'Chuyển giao diện tối'} onClick={() => update({ ...value, dark: !value.dark })}>{value.dark ? <Sun size={19}/> : <Moon size={19}/>}</button><Popover.Root><Popover.Trigger asChild><button className="icon-button" aria-label="Tùy chỉnh giao diện"><Settings2 size={19}/></button></Popover.Trigger><Popover.Portal><Popover.Content className="appearance-popover" align="end" sideOffset={12}><div className="popover-title"><h2>Giao diện của bạn</h2><Popover.Close className="icon-button" aria-label="Đóng tùy chỉnh"><X size={17}/></Popover.Close></div><p>Chỉ thay cách hiển thị, không đổi dữ liệu.</p><label className="font-picker">Kiểu chữ<select aria-label="Kiểu chữ" value={value.font} onChange={e => update({ ...value, font: e.target.value as FontChoice })}>{fonts.map(font => <option key={font.value} value={font.value}>{font.label}</option>)}</select></label><p className="font-sample" aria-live="polite">Quan sát hành trình · Đọc rõ từng kết quả ă â đ ê ô ơ ư</p><label className="check"><input type="checkbox" checked={value.gradient} onChange={e => update({ ...value, gradient: e.target.checked })}/>Nền chuyển sắc hồng phấn</label>{([['transparency', 'Trong suốt'], ['neon', 'Điểm sáng'], ['motion', 'Chuyển động'], ['roundness', 'Bo góc']] as const).map(([key, label]) => <label className="appearance-range" key={key}><span>{label}<b>{value[key]}%</b></span><input type="range" min={0} max={100} value={value[key]} onChange={e => update({ ...value, [key]: Number(e.target.value) })}/></label>)}<button className="button secondary full" onClick={() => update({ ...defaults })}>Khôi phục mặc định</button></Popover.Content></Popover.Portal></Popover.Root></div>
}

function Dashboard() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = useApi<Inventory>('/api/runs', 15)
  const [runId, setRunId] = useState('')
  const [mobile, setMobile] = useState(false)
  useEffect(() => {
    if (state.data?.runs.length && !state.data.runs.some(r => r.id === runId)) setRunId(state.data.runs[0].id)
  }, [state.data, runId])
  useEffect(() => {
    const requested = location.pathname === '/training' ? new URLSearchParams(location.search).get('run') : null
    if (requested && state.data?.runs.some(r => r.id === requested)) setRunId(requested)
  }, [location.pathname, location.search, state.data])
  const effectiveRunId = state.data?.runs.some(r => r.id === runId) ? runId : state.data?.runs[0]?.id || ''
  const selectedRun = state.data?.runs.find(r => r.id === effectiveRunId)
  const nav = () => navigation.map(([path, title, Icon]) => <NavLink key={path} to={path} end={path === '/'} onClick={() => setMobile(false)} className={({ isActive }) => isActive ? 'active' : ''}><Icon size={17}/><span>{title}</span></NavLink>)
  const props = state.data && { runId: effectiveRunId, inventory: state.data }
  return <div className="app"><a className="skip-link" href="#main">Đến nội dung chính</a><header className="app-header"><div className="header-inner"><Link className="brand" to="/" aria-label="Traffic Observatory, trang tổng quan"><span className="brand-icon"><ChartNoAxesCombined size={21}/></span><span>Traffic<span className="brand-light"> / Observatory</span></span></Link><nav className="desktop-nav" aria-label="Điều hướng chính">{nav()}</nav><div className="header-actions"><AppearanceControls/><Dialog.Root open={mobile} onOpenChange={setMobile}><Dialog.Trigger asChild><button className="icon-button mobile-menu" aria-label="Mở menu"><Menu size={21}/></button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className="mobile-drawer"><div className="modal-head"><Dialog.Title>Traffic Observatory</Dialog.Title><Dialog.Close className="icon-button" aria-label="Đóng menu"><X/></Dialog.Close></div><Dialog.Description className="sr-only">Điều hướng sáu khu vực của dashboard.</Dialog.Description><nav>{nav()}</nav></Dialog.Content></Dialog.Portal></Dialog.Root></div></div></header>
    <div className="workspace-bar"><div className="workspace-label"><span className="workspace-marker"/><span>DACN_TrafficCollision</span><span className="workspace-tag">Run local + Kaggle · chỉ đọc</span></div><div className="run-picker"><label htmlFor="run-picker">Thí nghiệm</label><div><select id="run-picker" value={effectiveRunId} onChange={e => { setRunId(e.target.value); if (location.pathname === '/training' && location.search) navigate('/training', {replace: true}) }} disabled={!state.data?.runs.length}>{!state.data?.runs.length && <option value="">Chưa có run</option>}{state.data?.runs.map(r => <option value={r.id} key={r.id}>{r.title}{r.status === 'withdrawn' ? ' · thu hồi' : ''}{!r.local_available ? ' · chỉ có cloud' : ''}</option>)}</select><ChevronDown size={14}/></div><button className="icon-button" aria-label="Cập nhật danh sách run" onClick={state.refresh}><RefreshCw size={16}/></button></div></div>
    <main id="main" className="main-content">{state.loading ? <Loading/> : state.error ? <ErrorState message={state.error} retry={state.refresh}/> : !state.data?.runs.length && !['/explore', '/library'].includes(location.pathname) ? <div className="empty"><h1>Chưa có run trên máy này</h1><p>Phục hồi artifact vào outputs/training theo GETTING_STARTED. Clone Git chỉ có code và metadata.</p><Link className="text-button" to="/explore">Khám phá cấu trúc đồ án <ArrowUpRight size={15}/></Link></div> : props && <Routes><Route path="/" element={selectedRun?.local_available === false ? <Navigate to="/training" replace/> : <Overview {...props}/>}/><Route path="/explore" element={<ExplorePage/>}/><Route path="/training" element={<Training key={effectiveRunId} {...props}/>}/><Route path="/compare" element={<Compare {...props}/>}/><Route path="/data" element={selectedRun?.local_available === false ? <Navigate to="/training" replace/> : <DataPage {...props}/>}/><Route path="/cases" element={selectedRun?.local_available === false ? <Navigate to="/training" replace/> : <CasesPage {...props}/>}/><Route path="/library" element={<Library/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes>}</main>
    <footer className="app-footer"><span><Camera size={16}/>DACN · quan sát bằng dữ liệu thật</span><span>Bbox ảnh ≠ sự kiện đã xác minh</span><Link to="/library">Căn cứ & giới hạn<ArrowUpRight size={14}/></Link></footer>
  </div>
}
export default function App() { return <BrowserRouter><Dashboard/></BrowserRouter> }
