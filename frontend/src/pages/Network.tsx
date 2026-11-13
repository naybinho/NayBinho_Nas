import React, { useState } from 'react'
import {
  Network as NetIcon,
  Wifi,
  Globe,
  ArrowUpRight,
  ArrowDownLeft,
  Settings,
  CheckCircle,
  RefreshCw,
  Sliders,
  ShieldCheck
} from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip
} from 'recharts'
import {
  useNetworkInterfaces,
  useNetworkHistory,
  formatBytes
} from '@/hooks/useSystemStats'
import api, { NetworkInterface } from '@/services/api'

export default function Network() {
  const { data: interfaces = [], isLoading, refetch } = useNetworkInterfaces()
  const netHistory = useNetworkHistory()

  // Selected config interface
  const [selectedIface, setSelectedIface] = useState<NetworkInterface | null>(null)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [ipAddress, setIpAddress] = useState('')
  const [gateway, setGateway] = useState('')
  const [dns, setDns] = useState('1.1.1.1, 8.8.8.8')
  const [saving, setSaving] = useState(false)

  const handleOpenConfig = (iface: NetworkInterface) => {
    setSelectedIface(iface)
    setIpAddress(iface.ip || '192.168.1.100')
    setGateway('192.168.1.1')
    setEditModalOpen(true)
  }

  const handleSaveConfig = async () => {
    if (!selectedIface) return
    setSaving(true)
    try {
      await api.configureInterface(selectedIface.name, {
        ip: ipAddress,
        gateway: gateway,
        dns: dns.split(',').map(s => s.trim())
      })
      setEditModalOpen(false)
      refetch()
    } catch (err: any) {
      alert('Falha ao configurar interface: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <NetIcon className="w-6 h-6 text-naybinho-accent" />
            Rede e Conectividade
          </h1>
          <p className="text-sm text-naybinho-muted">
            Gerenciamento de interfaces de rede físicas, endereçamento IP e telemetria de banda
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-naybinho-card border border-naybinho-border text-xs text-naybinho-text hover:text-white hover:bg-slate-800 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Atualizar Interfaces
        </button>
      </div>

      {/* Real-time Bandwidth Graph */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-naybinho-accent" />
              Consumo de Banda em Tempo Real
            </h2>
            <p className="text-xs text-naybinho-muted">Fluxo combinado de recepção (RX) e transmissão (TX)</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <ArrowDownLeft className="w-3.5 h-3.5" /> Download (RX)
            </span>
            <span className="flex items-center gap-1.5 text-amber-400">
              <ArrowUpRight className="w-3.5 h-3.5" /> Upload (TX)
            </span>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={netHistory.length > 0 ? netHistory : [{ time: '0s', rx: 0, tx: 0 }]}>
              <defs>
                <linearGradient id="colorRxNet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorTxNet" x1="0" y1="0" x2="0" y2="1">
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
              <Area type="monotone" dataKey="rx" stroke="#10B981" fillOpacity={1} fill="url(#colorRxNet)" />
              <Area type="monotone" dataKey="tx" stroke="#F59E0B" fillOpacity={1} fill="url(#colorTxNet)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Interfaces Cards & List */}
      <div className="glass-card p-5">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <NetIcon className="w-4 h-4 text-naybinho-accent" />
          Interfaces Físicas e Virtuais ({interfaces.length})
        </h2>

        {isLoading ? (
          <p className="text-sm text-naybinho-muted py-8 text-center">Detectando adaptadores de rede...</p>
        ) : interfaces.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-naybinho-border rounded-xl">
            <p className="text-sm text-naybinho-muted">Nenhuma interface de rede detectada.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {interfaces.map((iface) => (
              <div
                key={iface.name}
                className="p-4 rounded-xl bg-naybinho-bg border border-naybinho-border flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${iface.is_up ? 'bg-emerald-500' : 'bg-red-500'}`} />
                      <span className="font-mono font-bold text-white text-base">{iface.name}</span>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                      iface.is_up ? 'badge-healthy' : 'badge-error'
                    }`}>
                      {iface.is_up ? 'CONECTADO' : 'DESCONECTADO'}
                    </span>
                  </div>

                  <div className="mt-4 p-3 bg-slate-900/60 rounded-lg border border-slate-800 text-xs space-y-1.5 font-mono">
                    <div className="flex justify-between">
                      <span className="text-naybinho-muted">Endereço IP:</span>
                      <span className="text-white font-medium">{iface.ip || 'DHCP Pendente'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-naybinho-muted">Endereço MAC:</span>
                      <span className="text-slate-400">{iface.mac || '52:54:00:12:34:56'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-naybinho-muted">Velocidade:</span>
                      <span className="text-emerald-400 font-semibold">{iface.speed ? `${iface.speed} Mbps` : '1000 Mbps'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-naybinho-muted">MTU:</span>
                      <span className="text-slate-300">{iface.mtu || 1500}</span>
                    </div>
                  </div>

                  <div className="flex justify-between text-xs text-naybinho-muted mt-3 font-mono">
                    <span>RX: {formatBytes(iface.rx_bytes || 0)}</span>
                    <span>TX: {formatBytes(iface.tx_bytes || 0)}</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-naybinho-border/50 flex justify-end">
                  <button
                    onClick={() => handleOpenConfig(iface)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-naybinho-card border border-naybinho-border text-xs text-naybinho-text hover:text-white hover:bg-slate-800 transition"
                  >
                    <Settings className="w-3.5 h-3.5 text-naybinho-accent" /> Configurar IP
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Interface Configuration Modal */}
      {editModalOpen && selectedIface && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">Configurar Interface {selectedIface.name}</h3>
            <p className="text-xs text-naybinho-muted mb-4">
              Defina os parâmetros IPv4 estáticos para esta interface.
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-naybinho-muted block mb-1">Endereço IPv4</label>
                <input
                  type="text"
                  value={ipAddress}
                  onChange={(e) => setIpAddress(e.target.value)}
                  placeholder="192.168.1.100/24"
                  className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded text-sm text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-naybinho-muted block mb-1">Gateway Padrão</label>
                <input
                  type="text"
                  value={gateway}
                  onChange={(e) => setGateway(e.target.value)}
                  placeholder="192.168.1.1"
                  className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded text-sm text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-naybinho-muted block mb-1">Servidores DNS (separados por vírgula)</label>
                <input
                  type="text"
                  value={dns}
                  onChange={(e) => setDns(e.target.value)}
                  placeholder="1.1.1.1, 8.8.8.8"
                  className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded text-sm text-white focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                disabled={saving}
                onClick={() => setEditModalOpen(false)}
                className="px-4 py-2 rounded text-xs text-naybinho-muted hover:text-white"
              >
                Cancelar
              </button>
              <button
                disabled={saving}
                onClick={handleSaveConfig}
                className="px-4 py-2 rounded text-xs font-semibold bg-naybinho-primary hover:bg-blue-600 text-white transition flex items-center gap-1.5"
              >
                {saving ? 'Aplicando...' : 'Salvar Alterações'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
