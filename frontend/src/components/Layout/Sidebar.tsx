// NayBinho NAS — Sidebar navigation

import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  HardDrive,
  Layers,
  Container,
  Store,
  Network,
  Users,
  Settings,
  RefreshCw,
  FileText,
  ChevronLeft,
  ChevronRight,
  Server,
} from 'lucide-react'

// ─── Nav items ────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/storage',   icon: HardDrive,       label: 'Storage' },
  { to: '/raid',      icon: Layers,          label: 'RAID' },
  { to: '/docker',    icon: Container,       label: 'Docker' },
  { to: '/apps',      icon: Store,           label: 'App Store' },
  { to: '/network',   icon: Network,         label: 'Network' },
  { to: '/system',    icon: Settings,        label: 'Sistema' },
]

// ─── Component ────────────────────────────────────────────────────────────────

interface SidebarProps {
  version?: string
}

export default function Sidebar({ version = 'v1.0.0-alpha' }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <aside
      className={`
        relative flex flex-col h-screen
        bg-naybinho-card border-r border-naybinho-border
        transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-64'}
      `}
    >
      {/* ── Logo ── */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-naybinho-border">
        <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-naybinho-primary to-naybinho-accent rounded-lg flex items-center justify-center shadow-lg shadow-blue-900/50">
          <Server className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <p className="text-white font-bold text-sm leading-tight truncate">NayBinho NAS</p>
            <p className="text-naybinho-muted text-xs truncate">Home Lab OS</p>
          </div>
        )}
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
          const isActive = location.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              title={collapsed ? label : undefined}
              className={`
                group flex items-center gap-3 px-3 py-2.5 rounded-lg
                text-sm font-medium transition-all duration-150
                ${isActive
                  ? 'bg-naybinho-primary/20 text-naybinho-accent border border-naybinho-primary/30'
                  : 'text-naybinho-muted hover:text-naybinho-text hover:bg-white/5'
                }
              `}
            >
              <Icon
                className={`flex-shrink-0 w-5 h-5 transition-colors ${
                  isActive ? 'text-naybinho-accent' : 'text-naybinho-muted group-hover:text-naybinho-text'
                }`}
              />
              {!collapsed && <span className="truncate">{label}</span>}
              {/* Active indicator bar */}
              {isActive && !collapsed && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-naybinho-accent" />
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* ── Version ── */}
      {!collapsed && (
        <div className="px-4 py-3 border-t border-naybinho-border">
          <p className="text-naybinho-muted text-xs">NayBinho NAS</p>
          <p className="text-naybinho-muted/60 text-xs font-mono">{version}</p>
        </div>
      )}

      {/* ── Collapse toggle ── */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="
          absolute -right-3 top-1/2 -translate-y-1/2
          w-6 h-6 rounded-full
          bg-naybinho-card border border-naybinho-border
          flex items-center justify-center
          text-naybinho-muted hover:text-white
          transition-colors shadow-md
          z-10
        "
        aria-label={collapsed ? 'Expandir sidebar' : 'Recolher sidebar'}
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </aside>
  )
}
