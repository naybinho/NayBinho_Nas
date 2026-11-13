// NayBinho NAS — System Stats Hooks (React Query)
// Polling hooks for real-time dashboard data

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import api, { SystemStats, SystemInfo } from '@/services/api'

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const queryKeys = {
  systemInfo:    ['system', 'info']       as const,
  systemStats:   ['system', 'stats']      as const,
  disks:         ['storage', 'disks']     as const,
  volumes:       ['storage', 'volumes']   as const,
  raid:          ['storage', 'raid']      as const,
  containers:    ['docker', 'containers'] as const,
  images:        ['docker', 'images']     as const,
  interfaces:    ['network', 'interfaces']as const,
  storeApps:     ['store', 'apps']        as const,
  installedApps: ['store', 'installed']   as const,
  notifications: ['system', 'notifications'] as const,
}

// ─── System Info (slow refresh — 30s) ─────────────────────────────────────────

export function useSystemInfo() {
  return useQuery({
    queryKey: queryKeys.systemInfo,
    queryFn: api.getSystemInfo.bind(api),
    refetchInterval: 30_000,
    staleTime: 20_000,
  })
}

// ─── Live System Stats (fast polling — 2s) ────────────────────────────────────

export function useSystemStats() {
  return useQuery({
    queryKey: queryKeys.systemStats,
    queryFn: api.getSystemStats.bind(api),
    refetchInterval: 2_000,
    staleTime: 1_000,
  })
}

// ─── CPU History (last 60 data points, 2s cadence → 2 min window) ─────────────

export function useCpuHistory(maxPoints = 60) {
  const [history, setHistory] = useState<{ time: string; cpu: number; ram: number }[]>([])
  const { data: stats } = useSystemStats()

  useEffect(() => {
    if (!stats) return
    setHistory((prev) => {
      const point = {
        time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        cpu: Math.round(stats.cpu_percent),
        ram: Math.round(stats.ram_percent),
      }
      const updated = [...prev, point]
      return updated.length > maxPoints ? updated.slice(-maxPoints) : updated
    })
  }, [stats, maxPoints])

  return history
}

// ─── Network Traffic History ──────────────────────────────────────────────────

export function useNetworkHistory(maxPoints = 60) {
  const [history, setHistory] = useState<{ time: string; rx: number; tx: number }[]>([])
  const prevRef = useRef<{ rx: number; tx: number } | null>(null)
  const { data: stats } = useSystemStats()

  useEffect(() => {
    if (!stats) return
    const rxMbps = prevRef.current
      ? Math.max(0, ((stats.net_rx - prevRef.current.rx) * 8) / 1_000_000 / 2)
      : 0
    const txMbps = prevRef.current
      ? Math.max(0, ((stats.net_tx - prevRef.current.tx) * 8) / 1_000_000 / 2)
      : 0
    prevRef.current = { rx: stats.net_rx, tx: stats.net_tx }

    setHistory((prev) => {
      const point = {
        time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        rx: parseFloat(rxMbps.toFixed(2)),
        tx: parseFloat(txMbps.toFixed(2)),
      }
      const updated = [...prev, point]
      return updated.length > maxPoints ? updated.slice(-maxPoints) : updated
    })
  }, [stats, maxPoints])

  return history
}

// ─── RAID Arrays ──────────────────────────────────────────────────────────────

export function useRaidArrays() {
  return useQuery({
    queryKey: queryKeys.raid,
    queryFn: api.getRaidArrays.bind(api),
    refetchInterval: 10_000,
    staleTime: 8_000,
  })
}

// ─── Disks ────────────────────────────────────────────────────────────────────

export function useDisks() {
  return useQuery({
    queryKey: queryKeys.disks,
    queryFn: api.getDisks.bind(api),
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}

// ─── Volumes ──────────────────────────────────────────────────────────────────

export function useVolumes() {
  return useQuery({
    queryKey: queryKeys.volumes,
    queryFn: api.getVolumes.bind(api),
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}

// ─── Docker Containers ────────────────────────────────────────────────────────

export function useContainers() {
  return useQuery({
    queryKey: queryKeys.containers,
    queryFn: api.getContainers.bind(api),
    refetchInterval: 5_000,
    staleTime: 3_000,
  })
}

// ─── Docker Images ────────────────────────────────────────────────────────────

export function useImages() {
  return useQuery({
    queryKey: queryKeys.images,
    queryFn: api.getImages.bind(api),
    refetchInterval: 30_000,
  })
}

// ─── Network Interfaces ───────────────────────────────────────────────────────

export function useNetworkInterfaces() {
  return useQuery({
    queryKey: queryKeys.interfaces,
    queryFn: api.getInterfaces.bind(api),
    refetchInterval: 10_000,
    staleTime: 8_000,
  })
}

// ─── App Store ────────────────────────────────────────────────────────────────

export function useStoreApps(sourceId?: string) {
  return useQuery({
    queryKey: ['storeApps', sourceId || 'all'],
    queryFn: () => api.getStoreApps(sourceId && sourceId !== 'all' ? { source_id: sourceId } : undefined),
    staleTime: 60_000,
  })
}

export function useStoreSources() {
  return useQuery({
    queryKey: ['storeSources'],
    queryFn: () => api.getStoreSources(),
    staleTime: 15_000,
  })
}

export function useInstalledApps() {
  return useQuery({
    queryKey: queryKeys.installedApps,
    queryFn: api.getInstalledApps.bind(api),
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}

// ─── Notifications ────────────────────────────────────────────────────────────

export function useNotifications() {
  return useQuery({
    queryKey: queryKeys.notifications,
    queryFn: api.getNotifications.bind(api),
    refetchInterval: 10_000,
    staleTime: 8_000,
  })
}

// ─── Utility: format bytes ────────────────────────────────────────────────────

export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

// ─── Utility: format uptime ───────────────────────────────────────────────────

export function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}
