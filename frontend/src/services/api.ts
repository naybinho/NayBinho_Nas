// NayBinho NAS — API Service
// Centralizes all HTTP calls to the FastAPI backend

import axios, { AxiosInstance, AxiosResponse } from 'axios'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface SystemInfo {
  hostname: string
  os: string
  kernel: string
  uptime: number          // seconds
  cpu_percent: number
  cpu_cores: number
  ram_total: number       // bytes
  ram_used: number
  ram_percent: number
  temperature: number     // celsius
  version: string
}

export interface SystemStats {
  timestamp: number
  cpu_percent: number
  ram_percent: number
  temperature: number
  net_rx: number          // bytes/s
  net_tx: number
  disk_read: number
  disk_write: number
}

export interface Disk {
  device: string          // e.g. /dev/sda
  name: string
  model: string
  size: number            // bytes
  temperature: number
  smart_status: 'PASSED' | 'FAILED' | 'UNKNOWN'
  smart_enabled: boolean
  serial: string
  type: 'HDD' | 'SSD' | 'NVMe'
  partitions: Partition[]
}

export interface Partition {
  device: string
  mountpoint: string
  fstype: string
  size: number
  used: number
  percent: number
}

export interface SmartReport {
  device: string
  model: string
  serial: string
  firmware: string
  capacity: number
  status: string
  temperature: number
  power_on_hours: number
  attributes: SmartAttribute[]
}

export interface SmartAttribute {
  id: number
  name: string
  value: number
  worst: number
  threshold: number
  raw: string
  status: 'OK' | 'WARNING' | 'FAILED'
}

export interface RaidArray {
  name: string
  level: 0 | 1 | 5 | 6 | 10
  state: 'active' | 'degraded' | 'inactive' | 'failed' | 'recovering'
  size: number
  devices: string[]
  active_devices: number
  failed_devices: number
  spare_devices: number
  rebuild_progress?: number   // 0–100 when recovering
  fault_tolerance: string     // e.g. "Suporta perda de 2 discos"
}

export interface DockerContainer {
  id: string
  name: string
  image: string
  status: 'running' | 'stopped' | 'paused' | 'restarting' | 'dead'
  ports: string[]
  cpu_percent: number
  mem_usage: number
  mem_limit: number
  created: string
  uptime?: string
}

export interface DockerImage {
  id: string
  tags: string[]
  size: number
  created: string
}

export interface NetworkInterface {
  name: string
  ip: string
  mac: string
  speed: number           // Mbps
  mtu: number
  is_up: boolean
  rx_bytes: number
  tx_bytes: number
  rx_packets: number
  tx_packets: number
}

export interface AppDefinition {
  id: string
  name: string
  category: string
  description: string
  icon: string            // emoji or URL
  version: string
  compose_url?: string
  installed: boolean
  is_installed?: boolean
  running?: boolean
  container_id?: string
  tags: string[]
  source_id?: string
  source_name?: string
  homepage?: string
}

export interface StoreSource {
  id: string
  name: string
  url: string
  description?: string
  enabled: boolean
  type?: string
  icon?: string
  last_sync?: string | null
  app_count?: number
  status?: 'ready' | 'syncing' | 'error' | 'pending_sync'
  error_message?: string
}

export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'user' | 'readonly'
  created_at: string
  last_login?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Volume {
  name: string
  mountpoint: string
  fstype: string
  size: number
  used: number
  available: number
  percent: number
  device: string
}

export interface SystemReleaseInfo {
  current_version: string
  latest_version: string
  has_update: boolean
  release_title?: string
  release_notes?: string
  published_at?: string
  iso_asset?: {
    name: string
    download_url: string
    size_bytes: number
    size_mb: number
  } | null
  update_asset?: {
    name: string
    download_url: string
    size_bytes: number
    size_mb: number
  } | null
  system_packages_count?: number
  system_packages?: Array<{ name: string; version: string }>
  last_checked?: string
}

export interface UpdateProgressStatus {
  in_progress: boolean
  progress: {
    stage: string
    percent: number
    message: string
    started_at?: string
    completed_at?: string
    error?: string
  }
  latest_release: SystemReleaseInfo
}

export interface Notification {
  id: string
  level: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
  timestamp: string
  read: boolean
}

// ─── API Client ───────────────────────────────────────────────────────────────

class ApiService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: '/api',
      timeout: 15000,
      headers: { 'Content-Type': 'application/json' },
    })

    // Request interceptor: attach JWT token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('naybinho_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // Response interceptor: handle 401 globally
    this.client.interceptors.response.use(
      (res) => res,
      (err) => {
        if (err.response?.status === 401) {
          localStorage.removeItem('naybinho_token')
          window.location.href = '/login'
        }
        return Promise.reject(err)
      },
    )
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  async login(username: string, password: string): Promise<LoginResponse> {
    const params = new URLSearchParams({ username, password })
    const res = await this.client.post<LoginResponse>('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return res.data
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout')
  }

  async getMe(): Promise<User> {
    const res = await this.client.get<User>('/auth/me')
    return res.data
  }

  // ── System ────────────────────────────────────────────────────────────────

  async getSystemInfo(): Promise<SystemInfo> {
    const res = await this.client.get<SystemInfo>('/system/info')
    return res.data
  }

  async getSystemStats(): Promise<SystemStats> {
    const res = await this.client.get<SystemStats>('/system/stats')
    return res.data
  }

  async reboot(): Promise<void> {
    await this.client.post('/system/reboot')
  }

  async shutdown(): Promise<void> {
    await this.client.post('/system/shutdown')
  }

  async checkUpdates(): Promise<SystemReleaseInfo> {
    const res = await this.client.get<SystemReleaseInfo>('/system/update/check')
    return res.data
  }

  async getUpdateStatus(): Promise<UpdateProgressStatus> {
    const res = await this.client.get<UpdateProgressStatus>('/system/update/status')
    return res.data
  }

  async applyUpdates(): Promise<{ status: string; message: string }> {
    const res = await this.client.post('/system/update/apply', { apply: true })
    return res.data
  }

  async getHostname(): Promise<string> {
    const res = await this.client.get<{ hostname: string }>('/system/hostname')
    return res.data.hostname
  }

  async setHostname(hostname: string): Promise<void> {
    await this.client.post('/system/hostname', { hostname })
  }

  async getNotifications(): Promise<Notification[]> {
    const res = await this.client.get<Notification[]>('/system/notifications')
    return res.data
  }

  async markNotificationRead(id: string): Promise<void> {
    await this.client.patch(`/system/notifications/${id}/read`)
  }

  // ── Storage ───────────────────────────────────────────────────────────────

  async getDisks(): Promise<Disk[]> {
    const res = await this.client.get<Disk[]>('/storage/disks')
    return res.data
  }

  async getSmartReport(device: string): Promise<SmartReport> {
    const encoded = encodeURIComponent(device)
    const res = await this.client.get<SmartReport>(`/storage/smart/${encoded}`)
    return res.data
  }

  async getVolumes(): Promise<Volume[]> {
    const res = await this.client.get<Volume[]>('/storage/volumes')
    return res.data
  }

  async formatDisk(device: string, fstype: string, label?: string): Promise<void> {
    await this.client.post('/storage/volumes/format', { device, fstype, label })
  }

  async mountVolume(device: string, mountpoint: string): Promise<void> {
    await this.client.post('/storage/volumes/mount', { device, mountpoint })
  }

  async unmountVolume(mountpoint: string): Promise<void> {
    await this.client.post('/storage/volumes/unmount', { mountpoint })
  }

  // ── RAID ──────────────────────────────────────────────────────────────────

  async getRaidArrays(): Promise<RaidArray[]> {
    const res = await this.client.get<RaidArray[]>('/storage/raid')
    return res.data
  }

  async createRaid(params: {
    name: string
    level: number
    devices: string[]
  }): Promise<RaidArray> {
    const res = await this.client.post<RaidArray>('/storage/raid/create', params)
    return res.data
  }

  async deleteRaid(name: string): Promise<void> {
    await this.client.delete(`/storage/raid/${name}`)
  }

  // ── Docker ────────────────────────────────────────────────────────────────

  async getContainers(): Promise<DockerContainer[]> {
    const res = await this.client.get<DockerContainer[]>('/docker/containers')
    return res.data
  }

  async containerAction(
    id: string,
    action: 'start' | 'stop' | 'restart' | 'remove',
  ): Promise<void> {
    await this.client.post(`/docker/containers/${action}/${id}`)
  }

  async getContainerLogs(id: string, lines = 100): Promise<string> {
    const res = await this.client.get<{ logs: string }>(
      `/docker/containers/${id}/logs?lines=${lines}`,
    )
    return res.data.logs
  }

  async getContainerStats(id: string): Promise<{ cpu: number; mem: number }> {
    const res = await this.client.get(`/docker/stats/${id}`)
    return res.data
  }

  async getImages(): Promise<DockerImage[]> {
    const res = await this.client.get<DockerImage[]>('/docker/images')
    return res.data
  }

  async pullImage(image: string): Promise<void> {
    await this.client.post('/docker/pull', { image })
  }

  // ── App Store ─────────────────────────────────────────────────────────────

  async getStoreApps(params?: { category?: string; search?: string; source_id?: string }): Promise<AppDefinition[]> {
    const res = await this.client.get<AppDefinition[]>('/store/apps', { params })
    return res.data
  }

  async getStoreSources(): Promise<StoreSource[]> {
    const res = await this.client.get<StoreSource[]>('/store/sources')
    return res.data
  }

  async addStoreSource(data: { name: string; url: string; description?: string; type?: string; icon?: string }): Promise<{ message: string; source: StoreSource }> {
    const res = await this.client.post('/store/sources', data)
    return res.data
  }

  async updateStoreSource(sourceId: string, data: { enabled?: boolean; name?: string }): Promise<void> {
    await this.client.put(`/store/sources/${sourceId}`, data)
  }

  async deleteStoreSource(sourceId: string): Promise<void> {
    await this.client.delete(`/store/sources/${sourceId}`)
  }

  async syncAllSources(): Promise<void> {
    await this.client.post('/store/sources/sync')
  }

  async syncStoreSource(sourceId: string): Promise<void> {
    await this.client.post(`/store/sources/${sourceId}/sync`)
  }

  async getInstalledApps(): Promise<AppDefinition[]> {
    const res = await this.client.get<AppDefinition[]>('/store/apps/installed')
    return res.data
  }

  async installApp(id: string): Promise<void> {
    await this.client.post(`/store/apps/${id}/install`)
  }

  async uninstallApp(id: string): Promise<void> {
    await this.client.delete(`/store/apps/${id}/uninstall`)
  }

  async getStoreCategories(): Promise<string[]> {
    const res = await this.client.get<string[]>('/store/categories')
    return res.data
  }

  // ── Network ───────────────────────────────────────────────────────────────

  async getInterfaces(): Promise<NetworkInterface[]> {
    const res = await this.client.get<NetworkInterface[]>('/network/interfaces')
    return res.data
  }

  async configureInterface(
    name: string,
    config: { ip: string; gateway: string; dns: string[] },
  ): Promise<void> {
    await this.client.post(`/network/interfaces/${name}`, config)
  }

  // ── Users ─────────────────────────────────────────────────────────────────

  async getUsers(): Promise<User[]> {
    const res = await this.client.get<User[]>('/users')
    return res.data
  }

  async createUser(data: {
    username: string
    email: string
    password: string
    role: string
  }): Promise<User> {
    const res = await this.client.post<User>('/users', data)
    return res.data
  }

  async deleteUser(id: number): Promise<void> {
    await this.client.delete(`/users/${id}`)
  }

  async changePassword(currentPw: string, newPw: string): Promise<void> {
    await this.client.post('/auth/change-password', {
      current_password: currentPw,
      new_password: newPw,
    })
  }
}

// Singleton export
export const api = new ApiService()
export default api
