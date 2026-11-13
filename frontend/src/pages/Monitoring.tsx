import React, { useState, useEffect, useMemo } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSSE } from '../hooks/useSSE';

// --- Interfaces ---
interface MetricPoint {
  timestamp: string;
  cpu_pct?: number;
  ram_pct?: number;
  net_sent?: number;
  net_recv?: number;
  cpu?: { percent: number; load_avg_1m: number };
  ram?: { percent: number; used_gb: number; total_gb: number };
  temperatures?: Array<{ sensor: string; label: string; current: number }>;
  disks?: Array<{ mountpoint: string; percent: number; used_gb: number; total_gb: number }>;
}

interface AlertItem {
  id: number;
  type: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  value?: number;
  threshold?: number;
  created_at: string;
  dismissed: boolean | number;
}

interface LogEntry {
  source: string;
  timestamp: string;
  level: string;
  unit: string;
  message: string;
}

export const Monitoring: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'metrics' | 'alerts' | 'logs' | 'settings'>('metrics');
  const [period, setPeriod] = useState<'1h' | '6h' | '24h' | '7d'>('1h');
  
  // Real-time state via WS
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws/stats`;
  const { lastData: wsData, isConnected: wsConnected } = useWebSocket(wsUrl, { autoReconnect: true });

  // Fallback or Event alert stream via SSE
  const { data: sseData } = useSSE('/events/stream');

  // Metrics history
  const [metricsHistory, setMetricsHistory] = useState<MetricPoint[]>([]);
  const [loadingMetrics, setLoadingMetrics] = useState(false);

  // Alerts
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertFilter, setAlertFilter] = useState<'all' | 'active'>('active');

  // Logs
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logSearch, setLogSearch] = useState('');
  const [logLevel, setLogLevel] = useState('all');
  const [logService, setLogService] = useState('all');
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Settings
  const [settings, setSettings] = useState({
    thresholds: {
      cpu_percent: 90,
      ram_percent: 90,
      disk_percent: 85,
      temperature_celsius: 70,
      collect_interval_seconds: 10,
    },
    notifications: {
      email_enabled: false,
      email_to: '',
      webhook_enabled: false,
      webhook_url: '',
      telegram_enabled: false,
      telegram_bot_token: '',
      telegram_chat_id: '',
    },
  });

  // Current real-time snapshot
  const liveStats = useMemo(() => {
    if (wsData && wsData.event === 'metrics' && wsData.data) {
      return wsData.data;
    }
    return null;
  }, [wsData]);

  // Fetch metrics history
  const fetchMetricsHistory = async () => {
    setLoadingMetrics(true);
    try {
      const res = await fetch(`/api/monitoring/metrics?period=${period}`);
      const json = await res.json();
      if (json.metrics) setMetricsHistory(json.metrics);
    } catch (err) {
      console.error('Falha ao carregar métricas:', err);
    } finally {
      setLoadingMetrics(false);
    }
  };

  // Fetch alerts
  const fetchAlerts = async () => {
    try {
      const res = await fetch(`/api/monitoring/alerts?active_only=${alertFilter === 'active'}`);
      const json = await res.json();
      if (json.alerts) setAlerts(json.alerts);
    } catch (err) {
      console.error('Falha ao buscar alertas:', err);
    }
  };

  // Dismiss alert
  const handleDismissAlert = async (id: number) => {
    try {
      const res = await fetch(`/api/monitoring/alerts/${id}/dismiss`, { method: 'POST' });
      if (res.ok) {
        setAlerts((prev) => prev.filter((a) => a.id !== id));
      }
    } catch (err) {
      console.error('Erro ao descartar alerta:', err);
    }
  };

  // Fetch logs
  const fetchLogs = async () => {
    setLoadingLogs(true);
    try {
      let url = `/api/monitoring/logs?service=${encodeURIComponent(logService)}&level=${logLevel}&limit=150`;
      if (logSearch) url += `&search=${encodeURIComponent(logSearch)}`;
      const res = await fetch(url);
      const json = await res.json();
      if (json.logs) setLogs(json.logs);
    } catch (err) {
      console.error('Erro ao buscar logs:', err);
    } finally {
      setLoadingLogs(false);
    }
  };

  // Load Settings
  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/monitoring/settings');
      const json = await res.json();
      if (json.thresholds || json.notifications) {
        setSettings({
          thresholds: { ...settings.thresholds, ...json.thresholds },
          notifications: { ...settings.notifications, ...json.notifications },
        });
      }
    } catch (err) {
      console.error('Erro ao carregar configurações:', err);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/monitoring/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        alert('Configurações de monitoramento salvas com sucesso!');
      }
    } catch (err) {
      alert('Falha ao salvar configurações.');
    }
  };

  useEffect(() => {
    fetchMetricsHistory();
  }, [period]);

  useEffect(() => {
    fetchAlerts();
  }, [alertFilter]);

  useEffect(() => {
    if (activeTab === 'logs') fetchLogs();
    if (activeTab === 'settings') fetchSettings();
  }, [activeTab]);

  return (
    <div style={{ padding: '24px', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #1e293b', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>Monitoramento & Alertas</h1>
          <p style={{ color: '#94a3b8', margin: '4px 0 0 0', fontSize: '14px' }}>
            NayBinho NAS — Telemetria de hardware em tempo real, gestão de alertas e análise de eventos.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: wsConnected ? '#22c55e' : '#ef4444',
            }}
          />
          <span style={{ fontSize: '13px', color: '#cbd5e1' }}>
            {wsConnected ? 'WebSocket Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        {(['metrics', 'alerts', 'logs', 'settings'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              backgroundColor: activeTab === tab ? '#3b82f6' : '#1e293b',
              color: '#ffffff',
              transition: 'background-color 0.2s',
            }}
          >
            {tab === 'metrics' && '📊 Métricas & Hardware'}
            {tab === 'alerts' && `🚨 Alertas (${alerts.filter(a => !a.dismissed).length})`}
            {tab === 'logs' && '📜 Visualizador de Logs'}
            {tab === 'settings' && '⚙️ Configurações & Notificações'}
          </button>
        ))}
      </div>

      {/* Real-time Cards */}
      {liveStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div style={{ backgroundColor: '#1e293b', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #3b82f6' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>CPU USAGE</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', marginTop: '4px' }}>{liveStats.cpu?.percent}%</div>
            <div style={{ fontSize: '12px', color: '#64748b' }}>Load: {liveStats.cpu?.load_avg_1m?.toFixed(2)}</div>
          </div>
          <div style={{ backgroundColor: '#1e293b', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #10b981' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>RAM USAGE</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', marginTop: '4px' }}>{liveStats.ram?.percent}%</div>
            <div style={{ fontSize: '12px', color: '#64748b' }}>{liveStats.ram?.used_gb} GB / {liveStats.ram?.total_gb} GB</div>
          </div>
          <div style={{ backgroundColor: '#1e293b', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>TEMPERATURA MAX</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', marginTop: '4px' }}>
              {liveStats.temperatures?.length ? `${Math.max(...liveStats.temperatures.map((t: any) => t.current))}°C` : 'N/A'}
            </div>
            <div style={{ fontSize: '12px', color: '#64748b' }}>Sensores Ativos: {liveStats.temperatures?.length || 0}</div>
          </div>
          <div style={{ backgroundColor: '#1e293b', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>REDE TRAFFIC</div>
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '8px' }}>
              ↑ {((liveStats.network?.bytes_sent || 0) / 1024 / 1024).toFixed(1)} MB
            </div>
            <div style={{ fontSize: '12px', color: '#64748b' }}>
              ↓ {((liveStats.network?.bytes_recv || 0) / 1024 / 1024).toFixed(1)} MB
            </div>
          </div>
        </div>
      )}

      {/* Tab 1: Metrics */}
      {activeTab === 'metrics' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
            <div style={{ display: 'flex', gap: '4px', backgroundColor: '#1e293b', padding: '4px', borderRadius: '6px' }}>
              {(['1h', '6h', '24h', '7d'] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  style={{
                    backgroundColor: period === p ? '#3b82f6' : 'transparent',
                    color: '#f8fafc',
                    border: 'none',
                    padding: '4px 12px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px' }}>Histórico de Uso de Recursos</h3>
            {loadingMetrics ? (
              <p style={{ color: '#94a3b8' }}>Carregando métricas...</p>
            ) : metricsHistory.length === 0 ? (
              <p style={{ color: '#94a3b8' }}>Nenhum histórico registrado no período selecionado.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <p style={{ fontSize: '13px', color: '#94a3b8' }}>
                  Amostras coletadas: <strong>{metricsHistory.length}</strong> pontos.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                  <div style={{ backgroundColor: '#0f172a', padding: '12px', borderRadius: '6px' }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#38bdf8' }}>CPU (%) Últimas Amostras</h4>
                    {metricsHistory.slice(-5).map((m, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                        <span>{new Date(m.timestamp).toLocaleTimeString()}</span>
                        <span>{m.cpu_pct !== undefined ? `${m.cpu_pct.toFixed(1)}%` : `${m.cpu?.percent}%`}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ backgroundColor: '#0f172a', padding: '12px', borderRadius: '6px' }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#4ade80' }}>RAM (%) Últimas Amostras</h4>
                    {metricsHistory.slice(-5).map((m, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                        <span>{new Date(m.timestamp).toLocaleTimeString()}</span>
                        <span>{m.ram_pct !== undefined ? `${m.ram_pct.toFixed(1)}%` : `${m.ram?.percent}%`}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Alerts */}
      {activeTab === 'alerts' && (
        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '16px' }}>Alertas do Sistema</h3>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setAlertFilter('active')}
                style={{
                  backgroundColor: alertFilter === 'active' ? '#3b82f6' : '#334155',
                  color: 'white',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '12px',
                }}
              >
                Apenas Ativos
              </button>
              <button
                onClick={() => setAlertFilter('all')}
                style={{
                  backgroundColor: alertFilter === 'all' ? '#3b82f6' : '#334155',
                  color: 'white',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '12px',
                }}
              >
                Todos
              </button>
            </div>
          </div>

          {alerts.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '32px' }}>Nenhum alerta encontrado 🎉</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {alerts.map((alert) => {
                const isCrit = alert.severity === 'critical';
                const isWarn = alert.severity === 'warning';
                return (
                  <div
                    key={alert.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 16px',
                      backgroundColor: '#0f172a',
                      borderRadius: '6px',
                      borderLeft: `4px solid ${isCrit ? '#ef4444' : isWarn ? '#f59e0b' : '#3b82f6'}`,
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 'bold',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            backgroundColor: isCrit ? '#ef4444' : isWarn ? '#f59e0b' : '#3b82f6',
                            color: '#ffffff',
                            textTransform: 'uppercase',
                          }}
                        >
                          {alert.severity}
                        </span>
                        <strong style={{ fontSize: '14px' }}>{alert.message}</strong>
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                        Detectado em: {new Date(alert.created_at).toLocaleString()} | Tipo: {alert.type}
                      </div>
                    </div>
                    {!alert.dismissed && (
                      <button
                        onClick={() => handleDismissAlert(alert.id)}
                        style={{
                          backgroundColor: '#334155',
                          color: '#e2e8f0',
                          border: 'none',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '12px',
                        }}
                      >
                        Reconhecer
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Logs */}
      {activeTab === 'logs' && (
        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Buscar logs por palavra-chave..."
              value={logSearch}
              onChange={(e) => setLogSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchLogs()}
              style={{
                flex: 1,
                minWidth: '240px',
                padding: '8px 12px',
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '4px',
                color: '#ffffff',
                fontSize: '13px',
              }}
            />
            <select
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value)}
              style={{
                padding: '8px 12px',
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '4px',
                color: '#ffffff',
                fontSize: '13px',
              }}
            >
              <option value="all">Todos os Níveis</option>
              <option value="error">Error / Crítico</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
              <option value="debug">Debug</option>
            </select>
            <button
              onClick={fetchLogs}
              style={{
                backgroundColor: '#3b82f6',
                color: '#ffffff',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '13px',
              }}
            >
              Filtrar
            </button>
            <a
              href={`/api/monitoring/logs/export?service=${logService}&level=${logLevel}&fmt=json`}
              download
              style={{
                backgroundColor: '#334155',
                color: '#ffffff',
                textDecoration: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                fontSize: '13px',
                display: 'inline-flex',
                alignItems: 'center',
              }}
            >
              Exportar JSON
            </a>
          </div>

          <div
            style={{
              backgroundColor: '#0a0f1d',
              padding: '12px',
              borderRadius: '6px',
              maxHeight: '500px',
              overflowY: 'auto',
              fontFamily: 'monospace',
              fontSize: '12px',
            }}
          >
            {loadingLogs ? (
              <p style={{ color: '#94a3b8' }}>Carregando eventos de log...</p>
            ) : logs.length === 0 ? (
              <p style={{ color: '#94a3b8' }}>Nenhum log encontrado para os critérios selecionados.</p>
            ) : (
              logs.map((log, index) => (
                <div
                  key={index}
                  style={{
                    padding: '4px 0',
                    borderBottom: '1px solid #1e293b',
                    color: log.level === 'error' || log.level === 'critical' ? '#ef4444' : log.level === 'warning' ? '#f59e0b' : '#94a3b8',
                  }}
                >
                  <span style={{ color: '#64748b', marginRight: '8px' }}>[{log.timestamp || 'system'}]</span>
                  <span style={{ fontWeight: 'bold', marginRight: '8px' }}>[{log.level.toUpperCase()}]</span>
                  <span style={{ color: '#38bdf8', marginRight: '8px' }}>{log.unit || log.source}:</span>
                  <span style={{ color: '#e2e8f0' }}>{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Settings */}
      {activeTab === 'settings' && (
        <form onSubmit={handleSaveSettings} style={{ backgroundColor: '#1e293b', padding: '24px', borderRadius: '8px', maxWidth: '720px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px' }}>Limites de Alertas (Thresholds)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>Limite CPU (%)</label>
              <input
                type="number"
                value={settings.thresholds.cpu_percent}
                onChange={(e) => setSettings({ ...settings, thresholds: { ...settings.thresholds, cpu_percent: parseFloat(e.target.value) } })}
                style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>Limite RAM (%)</label>
              <input
                type="number"
                value={settings.thresholds.ram_percent}
                onChange={(e) => setSettings({ ...settings, thresholds: { ...settings.thresholds, ram_percent: parseFloat(e.target.value) } })}
                style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>Limite Disco (%)</label>
              <input
                type="number"
                value={settings.thresholds.disk_percent}
                onChange={(e) => setSettings({ ...settings, thresholds: { ...settings.thresholds, disk_percent: parseFloat(e.target.value) } })}
                style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>Temperatura Máx (°C)</label>
              <input
                type="number"
                value={settings.thresholds.temperature_celsius}
                onChange={(e) => setSettings({ ...settings, thresholds: { ...settings.thresholds, temperature_celsius: parseFloat(e.target.value) } })}
                style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
              />
            </div>
          </div>

          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', borderTop: '1px solid #334155', paddingTop: '16px' }}>Canais de Notificação</h3>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={settings.notifications.telegram_enabled}
                onChange={(e) => setSettings({ ...settings, notifications: { ...settings.notifications, telegram_enabled: e.target.checked } })}
              />
              Ativar Notificações via Telegram Bot
            </label>
            {settings.notifications.telegram_enabled && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '8px' }}>
                <input
                  type="text"
                  placeholder="Bot Token"
                  value={settings.notifications.telegram_bot_token}
                  onChange={(e) => setSettings({ ...settings, notifications: { ...settings.notifications, telegram_bot_token: e.target.value } })}
                  style={{ padding: '8px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
                />
                <input
                  type="text"
                  placeholder="Chat ID"
                  value={settings.notifications.telegram_chat_id}
                  onChange={(e) => setSettings({ ...settings, notifications: { ...settings.notifications, telegram_chat_id: e.target.value } })}
                  style={{ padding: '8px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
                />
              </div>
            )}
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={settings.notifications.webhook_enabled}
                onChange={(e) => setSettings({ ...settings, notifications: { ...settings.notifications, webhook_enabled: e.target.checked } })}
              />
              Ativar Webhook HTTP POST
            </label>
            {settings.notifications.webhook_enabled && (
              <div style={{ marginTop: '8px' }}>
                <input
                  type="url"
                  placeholder="https://seu-servidor.com/webhook/naybinho"
                  value={settings.notifications.webhook_url}
                  onChange={(e) => setSettings({ ...settings, notifications: { ...settings.notifications, webhook_url: e.target.value } })}
                  style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
                />
              </div>
            )}
          </div>

          <button
            type="submit"
            style={{
              backgroundColor: '#3b82f6',
              color: '#ffffff',
              border: 'none',
              padding: '10px 24px',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Salvar Configurações
          </button>
        </form>
      )}
    </div>
  );
};

export default Monitoring;
