// NayBinho NAS — Header

import React, { useState, useEffect } from 'react'
import { Bell, LogOut, User, ChevronDown, Wifi, WifiOff, Sun, Sparkles } from 'lucide-react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useSystemInfo, useNotifications } from '@/hooks/useSystemStats'
import api, { SystemReleaseInfo } from '@/services/api'

export default function Header() {
  const navigate = useNavigate()
  const { logout, user } = useAuthStore()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [notifOpen, setNotifOpen]       = useState(false)
  const [newRelease, setNewRelease]     = useState<SystemReleaseInfo | null>(null)

  const { data: sysInfo, isError } = useSystemInfo()
  const { data: notifications = [] } = useNotifications()

  useEffect(() => {
    // Check if new version or ISO was released on GitHub
    api.checkUpdates().then(info => {
      if (info && info.has_update) {
        setNewRelease(info)
      }
    }).catch(() => {})
  }, [])

  const unreadCount = notifications.filter((n) => !n.read).length
  const isOnline = !isError

  const handleLogout = async () => {
    try { await api.logout() } catch {}
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-naybinho-card border-b border-naybinho-border flex items-center justify-between px-6 flex-shrink-0">
      {/* ── Left: hostname + status ── */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          {isOnline ? (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
          ) : (
            <span className="h-2 w-2 rounded-full bg-red-500" />
          )}
          <span className="text-sm font-semibold text-naybinho-text">
            {sysInfo?.hostname ?? 'naybinho-nas'}
          </span>
        </div>
        <span className="text-naybinho-border">|</span>
        <span className={`text-xs font-medium flex items-center gap-1 ${isOnline ? 'text-emerald-400' : 'text-red-400'}`}>
          {isOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          {isOnline ? 'Online' : 'Offline'}
        </span>
        {sysInfo && (
          <>
            <span className="text-naybinho-border">|</span>
            <span className="text-xs text-naybinho-muted">
              Uptime: {formatUptime(sysInfo.uptime)}
            </span>
          </>
        )}
      </div>

      {/* ── Right: notifications + user ── */}
      <div className="flex items-center gap-2">
        {/* Update Badge if new ISO/version is out */}
        {newRelease?.has_update && (
          <Link
            to="/system"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gradient-to-r from-blue-600/30 to-indigo-600/30 border border-blue-400/50 text-blue-300 text-xs font-semibold hover:border-blue-400 transition animate-pulse"
            title={`Nova versão ${newRelease.latest_version} disponível! Clique para atualizar.`}
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span className="hidden sm:inline">Update</span> v{newRelease.latest_version}
          </Link>
        )}

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => { setNotifOpen(!notifOpen); setUserMenuOpen(false) }}
            className="relative p-2 rounded-lg text-naybinho-muted hover:text-white hover:bg-white/5 transition-colors"
            aria-label="Notificações"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-naybinho-card border border-naybinho-border rounded-xl shadow-2xl shadow-black/50 z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-naybinho-border flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Notificações</h3>
                {unreadCount > 0 && (
                  <span className="text-xs text-naybinho-accent">{unreadCount} não lidas</span>
                )}
              </div>
              <div className="max-h-72 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="text-center text-naybinho-muted text-sm py-6">Sem notificações</p>
                ) : (
                  notifications.slice(0, 8).map((n) => (
                    <div
                      key={n.id}
                      className={`px-4 py-3 border-b border-naybinho-border/50 hover:bg-white/5 ${!n.read ? 'bg-blue-900/10' : ''}`}
                    >
                      <div className="flex items-start gap-2">
                        <LevelDot level={n.level} />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-white truncate">{n.title}</p>
                          <p className="text-xs text-naybinho-muted mt-0.5 line-clamp-2">{n.message}</p>
                          <p className="text-[10px] text-naybinho-muted/60 mt-1">{n.timestamp}</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => { setUserMenuOpen(!userMenuOpen); setNotifOpen(false) }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-naybinho-primary to-naybinho-accent flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm text-naybinho-text">{user?.username ?? 'admin'}</span>
            <ChevronDown className="w-4 h-4 text-naybinho-muted" />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 bg-naybinho-card border border-naybinho-border rounded-xl shadow-2xl shadow-black/50 z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-naybinho-border">
                <p className="text-sm font-medium text-white">{user?.username}</p>
                <p className="text-xs text-naybinho-muted">{user?.role}</p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-400 hover:bg-red-900/20 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sair
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function LevelDot({ level }: { level: string }) {
  const colors: Record<string, string> = {
    info:    'bg-blue-400',
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    error:   'bg-red-400',
  }
  return <span className={`mt-1 flex-shrink-0 w-2 h-2 rounded-full ${colors[level] ?? 'bg-slate-400'}`} />
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}
