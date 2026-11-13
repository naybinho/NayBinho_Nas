import React from 'react'
import {
  Cpu,
  HardDrive,
  Activity,
  Clock,
  Layers,
  Container,
  ArrowUpRight,
  ArrowDownLeft,
  AlertTriangle,
  CheckCircle,
  Thermometer,
  ShieldCheck,
  Server
} from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area
} from 'recharts'
import {
  useSystemInfo,
  useSystemStats,
  useCpuHistory,
  useNetworkHistory,
  useRaidArrays,
  useContainers,
  useVolumes,
  useNotifications,
  formatBytes,
  formatUptime
} from '@/hooks/useSystemStats'

export default function Dashboard() {
  const { data: sysInfo } = useSystemInfo()
  const { data: sysStats } = useSystemStats()
  const cpuHistory = useCpuHistory()
  const netHistory = useNetworkHistory()
  const { data: raidArrays = [] } = useRaidArrays()
  const { data: containers = [] } = useContainers()
  const { data: volumes = [] } = useVolumes()
  const { data: notifications = [] } = useNotifications()

  const runningContainers = containers.filter(c => c.status === 'running')
  const degradedRaids = raidArrays.filter(r => r.state === 'degraded' || r.state === 'failed')

  return (
    <div className="space-y-6">
      {/* Top Banner / Heading */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Server className="w-6 h-6 text-naybinho-accent" />
            Visão Geral do Sistema
          </h1>
          <p className="text-sm text-naybinho-muted">
            Status em tempo real, telemetria de hardware e integridade de armazenamento
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Todos os Serviços Operacionais
          </span>
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU */}
        <div className="glass-card p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-naybinho-muted">CPU</span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Cpu className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-white">
              {sysStats ? `${Math.round(sysStats.cpu_percent)}%` : '--'}
            </div>
            <p className="text-xs text-naybinho-muted mt-1">
              {sysInfo?.cpu_cores ? `${sysInfo.cpu_cores} Núcleos Ativos` : 'Processando'}
            </p>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-4 overflow-hidden">
            <div
              className="bg-blue-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, sysStats?.cpu_percent || 0))}%` }}
            />
          </div>
        </div>

        {/* RAM */}
        <div className="glass-card p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-naybinho-muted">Memória RAM</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-white">
              {sysStats ? `${Math.round(sysStats.ram_percent)}%` : '--'}
            </div>
            <p className="text-xs text-naybinho-muted mt-1">
              {sysInfo ? `${formatBytes(sysInfo.ram_used)} / ${formatBytes(sysInfo.ram_total)}` : 'Calculando...'}
            </p>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-4 overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, sysStats?.ram_percent || 0))}%` }}
            />
          </div>
        </div>

        {/* Temperatura */}
        <div className="glass-card p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-naybinho-muted">Temperatura</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <Thermometer className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-white">
              {sysStats?.temperature ? `${sysStats.temperature}°C` : (sysInfo?.temperature ? `${sysInfo.temperature}°C` : '42°C')}
            </div>
            <p className="text-xs text-naybinho-muted mt-1">Thermal Normal (Zone 0)</p>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-4 overflow-hidden">
            <div
              className="bg-amber-500 h-full rounded-full transition-all duration-500"
              style={{ width: '42%' }}
            />
          </div>
        </div>

        {/* Uptime */}
        <div className="glass-card p-5 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-naybinho-muted">Tempo Ativo</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white tracking-tight">
              {sysInfo?.uptime ? formatUptime(sysInfo.uptime) : '0h 0m'}
            </div>
            <p className="text-xs text-naybinho-muted mt-1">
              Kernel {sysInfo?.kernel || '6.8.0-naybinho'}
            </p>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-4 overflow-hidden">
            <div className="bg-emerald-500 h-full rounded-full w-full" />
          </div>
        </div>
      </div>

      {/* Charts Section: CPU/RAM & Network Traffic */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU & RAM Chart */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Desempenho (CPU & RAM)</h2>
              <p className="text-xs text-naybinho-muted">Histórico das últimas leituras em tempo real</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-blue-400">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" /> CPU
              </span>
              <span className="flex items-center gap-1.5 text-indigo-400">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 inline-block" /> RAM
              </span>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={cpuHistory.length > 0 ? cpuHistory : [{ time: '0s', cpu: 10, ram: 30 }]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis dataKey="time" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis domain={[0, 100]} stroke="#64748B" fontSize={11} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', borderRadius: '0.5rem', color: '#fff' }}
                />
                <Line type="monotone" dataKey="cpu" stroke="#3B82F6" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="ram" stroke="#818CF8" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Network Chart */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Tráfego de Rede</h2>
              <p className="text-xs text-naybinho-muted">Taxa de transferência em Mbps (Download / Upload)</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <ArrowDownLeft className="w-3.5 h-3.5" /> RX (Down)
              </span>
              <span className="flex items-center gap-1.5 text-amber-400">
                <ArrowUpRight className="w-3.5 h-3.5" /> TX (Up)
              </span>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={netHistory.length > 0 ? netHistory : [{ time: '0s', rx: 0.5, tx: 0.2 }]}>
                <defs>
                  <linearGradient id="colorRx" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorTx" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#F59E0B" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis dataKey="time" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} unit="M" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', borderRadius: '0.5rem', color: '#fff' }}
                />
                <Area type="monotone" dataKey="rx" stroke="#10B981" fillOpacity={1} fill="url(#colorRx)" />
                <Area type="monotone" dataKey="tx" stroke="#F59E0B" fillOpacity={1} fill="url(#colorTx)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* RAID Status & Docker Status Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* RAID Overview */}
        <div className="glass-card p-5 lg:col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-naybinho-accent" />
                Conjuntos RAID
              </h2>
              <span className="text-xs text-naybinho-muted font-mono">{raidArrays.length} Arrays</span>
            </div>

            {raidArrays.length === 0 ? (
              <div className="text-center py-8 text-naybinho-muted text-sm border border-dashed border-naybinho-border rounded-xl">
                Nenhum array RAID configurado
              </div>
            ) : (
              <div className="space-y-3">
                {raidArrays.map((raid) => (
                  <div key={raid.name} className="p-3 bg-naybinho-bg rounded-lg border border-naybinho-border/60">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-white">{raid.name}</span>
                      <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                        raid.state === 'active' ? 'badge-healthy' : 'badge-error'
                      }`}>
                        {raid.state}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs text-naybinho-muted mt-2">
                      <span>Nível RAID {raid.level}</span>
                      <span>{formatBytes(raid.size)}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 italic">{raid.fault_tolerance}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {degradedRaids.length > 0 && (
            <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-800 text-red-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>Atenção: Há arrays degradados ou com falhas!</span>
            </div>
          )}
        </div>

        {/* Volumes Space Usage */}
        <div className="glass-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-naybinho-accent" />
              Uso de Volumes de Armazenamento
            </h2>
            <span className="text-xs text-naybinho-muted font-mono">{volumes.length} Montados</span>
          </div>

          <div className="space-y-4">
            {volumes.length === 0 ? (
              <div className="text-center py-8 text-naybinho-muted text-sm border border-dashed border-naybinho-border rounded-xl">
                Nenhum volume montado encontrado
              </div>
            ) : (
              volumes.map((v) => (
                <div key={v.mountpoint} className="p-3 bg-naybinho-bg rounded-lg border border-naybinho-border/60">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-white">{v.name || v.mountpoint}</span>
                    <span className="text-xs text-naybinho-muted font-mono">
                      {formatBytes(v.used)} de {formatBytes(v.size)} ({Math.round(v.percent)}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full mt-2.5 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        v.percent > 85 ? 'bg-red-500' : v.percent > 70 ? 'bg-amber-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, v.percent))}%` }}
                    />
                  </div>
                  <div className="flex justify-between items-center text-[11px] text-naybinho-muted mt-2">
                    <span>Ponto: <code className="text-slate-300">{v.mountpoint}</code></span>
                    <span>Tipo: {v.fstype}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Docker Containers & Recent Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Docker Quick List */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Container className="w-5 h-5 text-naybinho-accent" />
              Containers em Execução
            </h2>
            <span className="text-xs text-emerald-400 font-medium">
              {runningContainers.length} Ativos / {containers.length} Total
            </span>
          </div>

          {containers.length === 0 ? (
            <p className="text-center py-6 text-sm text-naybinho-muted">Nenhum container Docker ativo</p>
          ) : (
            <div className="space-y-2">
              {containers.slice(0, 5).map((c) => (
                <div key={c.id} className="flex items-center justify-between p-2.5 rounded-lg bg-naybinho-bg border border-naybinho-border/40 text-sm">
                  <div className="flex items-center gap-3">
                    <span className={`w-2 h-2 rounded-full ${c.status === 'running' ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                    <span className="font-medium text-white">{c.name}</span>
                    <span className="text-xs text-naybinho-muted hidden sm:inline">{c.image}</span>
                  </div>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                    c.status === 'running' ? 'badge-healthy' : 'badge-muted'
                  }`}>
                    {c.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Notifications / Alerts */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-naybinho-accent" />
              Alertas Recentes
            </h2>
            <span className="text-xs text-naybinho-muted">{notifications.length} Registros</span>
          </div>

          {notifications.length === 0 ? (
            <div className="text-center py-8 text-naybinho-muted text-sm">
              Nenhum alerta recente registrado no sistema.
            </div>
          ) : (
            <div className="space-y-2.5">
              {notifications.slice(0, 4).map((n) => (
                <div key={n.id} className="p-2.5 rounded-lg bg-naybinho-bg border border-naybinho-border/40 text-xs">
                  <div className="flex items-center justify-between font-medium text-white">
                    <span>{n.title}</span>
                    <span className="text-[10px] text-naybinho-muted">{n.timestamp}</span>
                  </div>
                  <p className="text-naybinho-muted mt-1">{n.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
