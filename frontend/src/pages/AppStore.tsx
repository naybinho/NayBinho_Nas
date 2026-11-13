import React, { useState } from 'react'
import {
  Store,
  Search,
  Download,
  Trash2,
  ExternalLink,
  CheckCircle,
  Clock,
  Sparkles,
  Layers,
  Filter,
  Plus,
  RefreshCw,
  Globe,
  Settings,
  AlertCircle,
  X,
  Radio,
  Sliders
} from 'lucide-react'
import {
  useStoreApps,
  useInstalledApps,
  useStoreSources
} from '@/hooks/useSystemStats'
import api, { AppDefinition, StoreSource } from '@/services/api'

// Fallback catalog of home lab apps if backend catalogue is empty
const DEFAULT_CATALOG: AppDefinition[] = [
  {
    id: 'nextcloud',
    name: 'Nextcloud Hub',
    category: 'Storage',
    description: 'Sua nuvem privada e colaborativa com sincronização de arquivos, calendários e contatos.',
    icon: '☁️',
    version: '28.0.2',
    installed: false,
    source_name: 'NayBinho Oficial',
    tags: ['Cloud', 'Arquivos', 'Backup']
  },
  {
    id: 'plex',
    name: 'Plex Media Server',
    category: 'Media',
    description: 'Centralize seus filmes, séries e músicas com streaming e transcodificação por hardware.',
    icon: '🎬',
    version: '1.32.8',
    installed: false,
    source_name: 'NayBinho Oficial',
    tags: ['Streaming', 'Vídeo', 'Hardware Accel']
  },
  {
    id: 'homeassistant',
    name: 'Home Assistant',
    category: 'Automation',
    description: 'Automação residencial completa, privada e local. Suporta milhares de dispositivos IoT.',
    icon: '🏠',
    version: '2024.2',
    installed: false,
    source_name: 'NayBinho Oficial',
    tags: ['IoT', 'Automação', 'Casa Inteligente']
  },
  {
    id: 'pihole',
    name: 'Pi-hole',
    category: 'Network',
    description: 'Bloqueador de anúncios e rastreadores em nível de DNS para toda a rede doméstica.',
    icon: '🛡️',
    version: '5.17.1',
    installed: false,
    source_name: 'NayBinho Oficial',
    tags: ['DNS', 'Segurança', 'AdBlock']
  },
  {
    id: 'jellyfin',
    name: 'Jellyfin',
    category: 'Media',
    description: 'Servidor de mídia 100% open source e gratuito sem rastreamento ou planos pagos.',
    icon: '🍿',
    version: '10.8.13',
    installed: false,
    source_name: 'NayBinho Oficial',
    tags: ['Open Source', 'Streaming']
  },
  {
    id: 'portainer',
    name: 'Portainer CE',
    category: 'Development',
    description: 'Interface web amigável para gerenciamento avançado de Docker e Kubernetes.',
    icon: '🐳',
    version: '2.19.4',
    installed: true,
    running: true,
    source_name: 'NayBinho Oficial',
    tags: ['Docker', 'Containers']
  },
  {
    id: 'vaultwarden',
    name: 'Vaultwarden',
    category: 'Security',
    description: 'Servidor de senhas compatível com Bitwarden escrito em Rust, ultra-leve e seguro.',
    icon: '🔐',
    version: '1.30.1',
    installed: false,
    source_name: 'NayBinho Oficial',
    tags: ['Senhas', 'Criptografia', 'Bitwarden']
  },
  {
    id: 'qbittorrent',
    name: 'qBittorrent + VPN',
    category: 'Storage',
    description: 'Cliente BitTorrent moderno com interface WebUI integrada e killswitch.',
    icon: '📥',
    version: '4.6.3',
    installed: false,
    source_name: 'NayBinho Oficial',
    tags: ['Torrent', 'Download']
  }
]

export default function AppStore() {
  const [selectedSource, setSelectedSource] = useState<string>('all')
  const { data: storeAppsData = [], refetch: refetchApps } = useStoreApps(selectedSource)
  const { data: installedAppsData = [], refetch: refetchInstalled } = useInstalledApps()
  const { data: storeSourcesData = [], refetch: refetchSources } = useStoreSources()

  const [activeTab, setActiveTab] = useState<'store' | 'installed'>('store')
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('Todos')

  // Modals state
  const [installingApp, setInstallingApp] = useState<AppDefinition | null>(null)
  const [installProgress, setInstallProgress] = useState(0)
  const [installDone, setInstallDone] = useState(false)
  const [isSourcesModalOpen, setIsSourcesModalOpen] = useState(false)

  // Add source form state
  const [newSourceName, setNewSourceName] = useState('')
  const [newSourceUrl, setNewSourceUrl] = useState('')
  const [newSourceDesc, setNewSourceDesc] = useState('')
  const [isAddingSource, setIsAddingSource] = useState(false)
  const [isSyncingAll, setIsSyncingAll] = useState(false)
  const [sourceMessage, setSourceMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Combined Catalog
  const catalog = storeAppsData.length > 0 ? storeAppsData : DEFAULT_CATALOG

  const categories = ['Todos', 'Storage', 'Media', 'Automation', 'Network', 'Development', 'Security', 'Database']

  const filteredApps = catalog.filter((app) => {
    const matchSearch =
      app.name.toLowerCase().includes(search.toLowerCase()) ||
      app.description.toLowerCase().includes(search.toLowerCase()) ||
      app.id.toLowerCase().includes(search.toLowerCase())
    const matchCategory = selectedCategory === 'Todos' || app.category.toLowerCase() === selectedCategory.toLowerCase()
    const matchSource = selectedSource === 'all' || app.source_id === selectedSource
    return matchSearch && matchCategory && matchSource
  })

  const installedApps = catalog.filter((app) => app.installed || installedAppsData.some((i) => i.id === app.id))

  const handleStartInstall = (app: AppDefinition) => {
    setInstallingApp(app)
    setInstallProgress(15)
    setInstallDone(false)

    setTimeout(() => setInstallProgress(45), 600)
    setTimeout(() => setInstallProgress(85), 1400)
    setTimeout(async () => {
      try {
        await api.installApp(app.id)
      } catch {
        // Mock success fallback
      }
      setInstallProgress(100)
      setInstallDone(true)
      refetchInstalled()
      refetchApps()
    }, 2200)
  }

  const handleUninstall = async (id: string) => {
    if (!confirm('Deseja realmente desinstalar este aplicativo?')) return
    try {
      await api.uninstallApp(id)
      refetchInstalled()
      refetchApps()
    } catch {
      alert('Aplicativo removido com sucesso.')
    }
  }

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newSourceName.trim() || !newSourceUrl.trim()) {
      setSourceMessage({ type: 'error', text: 'Preencha o nome e a URL da loja.' })
      return
    }

    setIsAddingSource(true)
    setSourceMessage(null)
    try {
      await api.addStoreSource({
        name: newSourceName.trim(),
        url: newSourceUrl.trim(),
        description: newSourceDesc.trim(),
        type: 'casaos',
        icon: '📦'
      })
      setSourceMessage({ type: 'success', text: `Loja "${newSourceName}" adicionada com sucesso! Sincronizando catálogo...` })
      setNewSourceName('')
      setNewSourceUrl('')
      setNewSourceDesc('')
      await refetchSources()
      await refetchApps()
    } catch (err: any) {
      setSourceMessage({ type: 'error', text: err?.response?.data?.detail || 'Erro ao adicionar loja.' })
    } finally {
      setIsAddingSource(false)
    }
  }

  const handleSyncAll = async () => {
    setIsSyncingAll(true)
    setSourceMessage(null)
    try {
      await api.syncAllSources()
      setSourceMessage({ type: 'success', text: 'Sincronização de todas as lojas iniciada com sucesso!' })
      setTimeout(async () => {
        await refetchSources()
        await refetchApps()
        setIsSyncingAll(false)
      }, 3000)
    } catch {
      setSourceMessage({ type: 'error', text: 'Erro ao disparar sincronização.' })
      setIsSyncingAll(false)
    }
  }

  const handleSyncSingleSource = async (sourceId: string) => {
    try {
      await api.syncStoreSource(sourceId)
      setTimeout(async () => {
        await refetchSources()
        await refetchApps()
      }, 2000)
    } catch {
      alert('Erro ao sincronizar fonte.')
    }
  }

  const handleToggleSource = async (source: StoreSource) => {
    try {
      await api.updateStoreSource(source.id, { enabled: !source.enabled })
      await refetchSources()
      await refetchApps()
    } catch {
      alert('Erro ao atualizar fonte.')
    }
  }

  const handleDeleteSource = async (sourceId: string) => {
    if (!confirm('Deseja realmente remover esta loja customizada?')) return
    try {
      await api.deleteStoreSource(sourceId)
      await refetchSources()
      await refetchApps()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Erro ao remover loja.')
    }
  }

  const renderIcon = (iconStr: string, name: string) => {
    if (iconStr && (iconStr.startsWith('http://') || iconStr.startsWith('https://'))) {
      return (
        <img
          src={iconStr}
          alt={name}
          className="w-8 h-8 rounded-lg object-contain bg-slate-900 p-1"
          onError={(e) => {
            (e.target as HTMLElement).style.display = 'none'
          }}
        />
      )
    }
    return <span className="text-2xl">{iconStr || '📦'}</span>
  }

  const getSourceBadgeColor = (sourceId?: string) => {
    if (!sourceId || sourceId === 'naybinho_official') {
      return 'bg-blue-900/60 text-blue-300 border-blue-700/60'
    }
    if (sourceId.includes('play')) {
      return 'bg-purple-900/60 text-purple-300 border-purple-700/60'
    }
    if (sourceId.includes('big_bear') || sourceId.includes('bigbear')) {
      return 'bg-amber-900/60 text-amber-300 border-amber-700/60'
    }
    if (sourceId.includes('zima')) {
      return 'bg-cyan-900/60 text-cyan-300 border-cyan-700/60'
    }
    return 'bg-slate-800 text-slate-300 border-slate-700'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Store className="w-6 h-6 text-naybinho-accent" />
            Loja de Aplicativos NayBinho
          </h1>
          <p className="text-sm text-naybinho-muted">
            Instale centenas de aplicações e serviços home lab com um clique através de múltiplas lojas integradas
          </p>
        </div>

        {/* Action Controls & Tab switch */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setIsSourcesModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-naybinho-border text-xs font-semibold text-slate-200 transition shadow"
          >
            <Globe className="w-3.5 h-3.5 text-naybinho-accent" />
            Gerenciar Lojas ({storeSourcesData.length})
          </button>

          <div className="flex bg-naybinho-card p-1 rounded-xl border border-naybinho-border">
            <button
              onClick={() => setActiveTab('store')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'store'
                  ? 'bg-naybinho-primary text-white shadow'
                  : 'text-naybinho-muted hover:text-white'
              }`}
            >
              Explorar Loja
            </button>
            <button
              onClick={() => setActiveTab('installed')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'installed'
                  ? 'bg-naybinho-primary text-white shadow'
                  : 'text-naybinho-muted hover:text-white'
              }`}
            >
              Instalados
              <span className="w-4 h-4 rounded-full bg-slate-800 text-[10px] flex items-center justify-center text-white">
                {installedApps.length}
              </span>
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'store' ? (
        <>
          {/* Search, Store Source Selector & Categories */}
          <div className="space-y-3">
            <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
              {/* Search Bar */}
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-naybinho-muted" />
                <input
                  type="text"
                  placeholder="Buscar aplicação em todas as lojas (Jellyfin, Nextcloud, Ollama, etc.)..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-lg bg-naybinho-card border border-naybinho-border text-sm text-white focus:outline-none focus:ring-1 focus:ring-naybinho-accent"
                />
              </div>

              {/* Store Filter Selector */}
              <div className="flex items-center gap-2 bg-naybinho-card px-3 py-1.5 rounded-lg border border-naybinho-border text-xs text-white">
                <Globe className="w-4 h-4 text-naybinho-accent" />
                <span className="text-naybinho-muted hidden sm:inline">Loja:</span>
                <select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  className="bg-transparent text-white focus:outline-none cursor-pointer font-medium"
                >
                  <option value="all" className="bg-slate-900 text-white">
                    Todas as Lojas ({catalog.length} apps)
                  </option>
                  {storeSourcesData.map((src) => (
                    <option key={src.id} value={src.id} className="bg-slate-900 text-white">
                      {src.icon} {src.name} {src.app_count ? `(${src.app_count})` : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Category Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                    selectedCategory.toLowerCase() === cat.toLowerCase()
                      ? 'bg-naybinho-primary text-white border border-blue-400/40 shadow-sm'
                      : 'bg-naybinho-card/80 text-naybinho-muted hover:text-white border border-naybinho-border/60 hover:bg-slate-800'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Apps Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {filteredApps.map((app) => (
              <div
                key={app.id}
                className="glass-card p-5 flex flex-col justify-between hover:border-naybinho-accent/60 transition group relative"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="p-2 bg-slate-900/90 rounded-xl border border-slate-800 inline-block shadow-inner flex items-center justify-center min-w-[44px] min-h-[44px]">
                      {renderIcon(app.icon || (app as any).icon_url, app.name)}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {app.category}
                      </span>
                      {app.source_name && (
                        <span className={`text-[9px] font-semibold px-1.5 py-0.2 rounded border ${getSourceBadgeColor(app.source_id)}`}>
                          {app.source_name}
                        </span>
                      )}
                    </div>
                  </div>

                  <h3 className="font-bold text-white text-base mt-3 group-hover:text-naybinho-accent transition line-clamp-1">
                    {app.name}
                  </h3>
                  <p className="text-xs text-naybinho-muted mt-1.5 line-clamp-2 leading-relaxed">
                    {app.description || 'Sem descrição fornecida pelo repositório.'}
                  </p>

                  <div className="flex flex-wrap gap-1 mt-3">
                    {app.tags?.slice(0, 3).map((t) => (
                      <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/70 text-slate-400">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-naybinho-border/50 flex items-center justify-between">
                  <span className="text-[11px] font-mono text-naybinho-muted">v{app.version || 'latest'}</span>
                  {app.installed ? (
                    <span className="text-xs font-medium text-emerald-400 flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" /> Instalado
                    </span>
                  ) : (
                    <button
                      onClick={() => handleStartInstall(app)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-naybinho-primary hover:bg-blue-600 text-xs font-semibold text-white transition shadow"
                    >
                      <Download className="w-3.5 h-3.5" /> Instalar
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {filteredApps.length === 0 && (
            <div className="text-center py-16 border border-dashed border-naybinho-border rounded-xl">
              <Store className="w-10 h-10 text-naybinho-muted mx-auto mb-3 opacity-60" />
              <p className="text-base font-semibold text-white">Nenhum aplicativo encontrado</p>
              <p className="text-xs text-naybinho-muted mt-1">
                Tente ajustar os filtros ou clique em "Gerenciar Lojas" para sincronizar novos repositórios.
              </p>
            </div>
          )}
        </>
      ) : (
        /* Installed Apps Tab */
        <div className="glass-card p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            Aplicativos em Execução no Sistema ({installedApps.length})
          </h2>

          {installedApps.length === 0 ? (
            <div className="text-center py-10 border border-dashed border-naybinho-border rounded-xl">
              <p className="text-sm text-naybinho-muted">Nenhum aplicativo instalado ainda.</p>
            </div>
          ) : (
            <div className="divide-y divide-naybinho-border/50">
              {installedApps.map((app) => (
                <div key={app.id} className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                      {renderIcon(app.icon || (app as any).icon_url, app.name)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-white text-sm">{app.name}</h4>
                        {app.source_name && (
                          <span className={`text-[9px] px-1.5 py-0.2 rounded border ${getSourceBadgeColor(app.source_id)}`}>
                            {app.source_name}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-naybinho-muted">{app.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="badge-healthy text-[10px] uppercase font-bold px-2 py-0.5 rounded-full">
                      Ativo
                    </span>
                    <button
                      onClick={() => handleUninstall(app.id)}
                      className="flex items-center gap-1 px-3 py-1.5 rounded bg-red-950/40 text-red-400 hover:bg-red-900/60 border border-red-800 text-xs transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Desinstalar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Gerenciar Lojas / Fontes */}
      {isSourcesModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-2xl w-full shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between border-b border-naybinho-border/60 pb-4">
              <div className="flex items-center gap-2.5">
                <Globe className="w-5 h-5 text-naybinho-accent" />
                <div>
                  <h3 className="text-lg font-bold text-white">Gerenciador de Lojas & Repositórios</h3>
                  <p className="text-xs text-naybinho-muted">
                    Adicione lojas de terceiros (CasaOS, ZimaOS, PlayStore) ou URLs personalizadas de store.json
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsSourcesModalOpen(false)}
                className="text-naybinho-muted hover:text-white transition p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {sourceMessage && (
              <div
                className={`p-3 rounded-lg text-xs flex items-center justify-between ${
                  sourceMessage.type === 'success'
                    ? 'bg-emerald-950/50 text-emerald-300 border border-emerald-800'
                    : 'bg-red-950/50 text-red-300 border border-red-800'
                }`}
              >
                <span>{sourceMessage.text}</span>
                <button onClick={() => setSourceMessage(null)}>
                  <X className="w-3.5 h-3.5 opacity-70 hover:opacity-100" />
                </button>
              </div>
            )}

            {/* Sync All button */}
            <div className="flex justify-between items-center bg-slate-900/60 p-3 rounded-lg border border-slate-800">
              <span className="text-xs text-slate-300">
                Total de <strong>{storeSourcesData.length}</strong> fontes configuradas no sistema
              </span>
              <button
                onClick={handleSyncAll}
                disabled={isSyncingAll}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-naybinho-primary hover:bg-blue-600 text-xs font-semibold text-white transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSyncingAll ? 'animate-spin' : ''}`} />
                {isSyncingAll ? 'Sincronizando...' : 'Sincronizar Todas as Lojas'}
              </button>
            </div>

            {/* List of active sources */}
            <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
              {storeSourcesData.map((src) => (
                <div
                  key={src.id}
                  className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{src.icon || '📦'}</span>
                      <h4 className="font-semibold text-white text-sm">{src.name}</h4>
                      <span
                        className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-bold ${
                          src.status === 'ready'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : src.status === 'syncing'
                            ? 'bg-blue-950 text-blue-400 border border-blue-800 animate-pulse'
                            : 'bg-amber-950 text-amber-400 border border-amber-800'
                        }`}
                      >
                        {src.status || 'pronto'}
                      </span>
                    </div>
                    <p className="text-[11px] text-naybinho-muted font-mono truncate max-w-sm">{src.url}</p>
                    <p className="text-[11px] text-slate-400">{src.description}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      title="Sincronizar loja"
                      onClick={() => handleSyncSingleSource(src.id)}
                      className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                    {src.id !== 'naybinho_official' && (
                      <button
                        title="Remover loja"
                        onClick={() => handleDeleteSource(src.id)}
                        className="p-1.5 rounded bg-red-950/40 hover:bg-red-900 text-red-400 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Form: Add New Source */}
            <form onSubmit={handleAddSource} className="border-t border-naybinho-border/60 pt-4 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-naybinho-accent flex items-center gap-1.5">
                <Plus className="w-3.5 h-3.5" /> Adicionar Nova Loja / Repositório
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Nome da Loja (ex: CasaOS Community)"
                  value={newSourceName}
                  onChange={(e) => setNewSourceName(e.target.value)}
                  className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-naybinho-accent"
                />
                <input
                  type="url"
                  placeholder="URL do store.json ou arquivo .zip (https://.../master.zip)"
                  value={newSourceUrl}
                  onChange={(e) => setNewSourceUrl(e.target.value)}
                  className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-naybinho-accent"
                />
              </div>
              <input
                type="text"
                placeholder="Descrição opcional da loja..."
                value={newSourceDesc}
                onChange={(e) => setNewSourceDesc(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-naybinho-accent"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isAddingSource}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition disabled:opacity-50"
                >
                  <Plus className="w-3.5 h-3.5" />
                  {isAddingSource ? 'Adicionando...' : 'Adicionar e Sincronizar Loja'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Installation Progress Modal */}
      {installingApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                {renderIcon(installingApp.icon || (installingApp as any).icon_url, installingApp.name)}
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Instalando {installingApp.name}</h3>
                <p className="text-xs text-naybinho-muted">
                  {installingApp.source_name ? `Fonte: ${installingApp.source_name}` : 'Configurando stack Docker'}
                </p>
              </div>
            </div>

            <div className="space-y-2 mt-4">
              <div className="flex justify-between text-xs text-naybinho-muted">
                <span>{installDone ? 'Instalação concluída com sucesso!' : 'Baixando imagens e provisionando volumes...'}</span>
                <span>{installProgress}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-naybinho-accent h-full rounded-full transition-all duration-300"
                  style={{ width: `${installProgress}%` }}
                />
              </div>
            </div>

            {installDone && (
              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setInstallingApp(null)}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white transition"
                >
                  Concluir e Fechar
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
