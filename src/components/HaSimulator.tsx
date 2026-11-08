import React, { useState, useEffect } from 'react';
import { 
  Lock, 
  Unlock, 
  Battery, 
  BatteryMedium, 
  BatteryWarning, 
  Wifi, 
  KeyRound, 
  Radio, 
  Server, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  RotateCcw,
  Sparkles,
  Layers
} from 'lucide-react';
import { Language, SimulatedLock, SimulatedGateway } from '../types';
import { TRANSLATIONS } from '../i18n/translations';

interface HaSimulatorProps {
  currentLang: Language;
}

export const HaSimulator: React.FC<HaSimulatorProps> = ({ currentLang }) => {
  const t = TRANSLATIONS[currentLang];

  // Config flow states
  const [clientId, setClientId] = useState('WLK_DEMO_CLIENT_9721');
  const [clientSecret, setClientSecret] = useState('sec_wl_88390b24e4d5881');
  const [isConnected, setIsConnected] = useState(true);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Simulated locks
  const [locks, setLocks] = useState<SimulatedLock[]>([
    {
      id: 'lock_01',
      sn: 'WLK-4109-8821',
      name: currentLang === 'de' ? 'WeLock Touch41 Haustür' : currentLang === 'es' ? 'WeLock Touch41 Puerta Principal' : currentLang === 'fr' ? 'WeLock Touch41 Porte Principale' : 'WeLock Touch41 Front Door',
      model: 'Touch41 (Fingerprint & RFID)',
      battery: 88,
      isLocked: true,
      isUnlocking: false,
      lastUnlockMethod: 'Fingerprint',
      lastUnlockTimestamp: '10:42',
      rssi: -64,
      online: true,
      wifiBoxId: 'WFBX-003-771',
    },
    {
      id: 'lock_02',
      sn: 'WLK-3210-4491',
      name: currentLang === 'de' ? 'WeLock PCB41 Gartenhaus' : currentLang === 'es' ? 'WeLock PCB41 Caseta Jardín' : currentLang === 'fr' ? 'WeLock PCB41 Abri de Jardin' : 'WeLock PCB41 Garden Shed',
      model: 'PCB41 (Passcode & RFID)',
      battery: 62,
      isLocked: true,
      isUnlocking: false,
      lastUnlockMethod: 'Passcode',
      lastUnlockTimestamp: 'Yesterday 17:15',
      rssi: -78,
      online: true,
      wifiBoxId: 'WFBX-003-771',
    },
  ]);

  const [gateway] = useState<SimulatedGateway>({
    id: 'WFBX-003-771',
    name: 'WeLock WiFiBox 3',
    model: 'WiFiBox 3 Gateway (BLE 5.0 + Wi-Fi)',
    online: true,
    connectedLocks: 2,
    ip: '192.168.1.145',
  });

  // Simulated logs
  const [logs, setLogs] = useState<Array<{ id: string; time: string; text: string; type: 'info' | 'success' | 'warn' }>>([
    {
      id: '1',
      time: '04:52:10',
      text: 'WeLock API: Initialized coordinator. Polling interval: 30s.',
      type: 'info',
    },
    {
      id: '2',
      time: '04:52:11',
      text: 'Discovered 2 WeLock locks and 1 WiFiBox gateway via api.welockglobal.com',
      type: 'success',
    },
  ]);

  const addLog = (text: string, type: 'info' | 'success' | 'warn' = 'info') => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [{ id: Math.random().toString(), time, text, type }, ...prev.slice(0, 15)]);
  };

  const handleConnect = () => {
    if (!clientId.trim() || !clientSecret.trim()) {
      setErrorMessage(t.simulator.clientIdLabel + ' & ' + t.simulator.clientSecretLabel + ' required.');
      return;
    }
    setErrorMessage(null);
    setIsAuthenticating(true);

    setTimeout(() => {
      setIsAuthenticating(false);
      setIsConnected(true);
      addLog(`Authenticated successfully with WeLock Cloud (${clientId.slice(0, 8)}...)`, 'success');
    }, 900);
  };

  const handleUnlock = (lockId: string) => {
    setLocks((prev) =>
      prev.map((l) => (l.id === lockId ? { ...l, isUnlocking: true } : l))
    );

    addLog(`POST api.welockglobal.com/app/v1/open/lock/unlock -> Lock ${lockId}`, 'info');

    setTimeout(() => {
      setLocks((prev) =>
        prev.map((l) =>
          l.id === lockId
            ? {
                ...l,
                isUnlocking: false,
                isLocked: false,
                lastUnlockMethod: 'Gateway',
                lastUnlockTimestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              }
            : l
        )
      );
      addLog(`Lock ${lockId} UNLOCKED. Cylinder authorized to turn for 7s.`, 'success');

      // Auto-relock mechanically after 7s (standard WeLock behaviour)
      setTimeout(() => {
        setLocks((prev) =>
          prev.map((l) => (l.id === lockId ? { ...l, isLocked: true } : l))
        );
        addLog(`Lock ${lockId} auto-relocked mechanically. Outer knob disengaged.`, 'info');
      }, 7000);
    }, 600);
  };

  const handleManualLock = (lockId: string) => {
    setLocks((prev) =>
      prev.map((l) => (l.id === lockId ? { ...l, isLocked: true, isUnlocking: false } : l))
    );
    addLog(`Lock ${lockId} locked manually in Home Assistant.`, 'info');
  };

  const getBatteryIcon = (pct: number) => {
    if (pct > 70) return <Battery className="w-4 h-4 text-emerald-400" />;
    if (pct > 25) return <BatteryMedium className="w-4 h-4 text-amber-400" />;
    return <BatteryWarning className="w-4 h-4 text-red-400 animate-pulse" />;
  };

  return (
    <div className="space-y-6">
      {/* Overview Notice */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            <h2 className="text-lg sm:text-xl font-bold text-white">
              {t.simulator.title}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {t.simulator.subtitle}
          </p>
        </div>

        <div className="text-xs text-slate-300 font-mono bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center gap-2">
          <Server className="w-3.5 h-3.5 text-cyan-400" />
          <span>https://api.welockglobal.com</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Home Assistant Config Flow Box (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            {/* HA Card Header */}
            <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs">
                  HA
                </div>
                <h3 className="font-semibold text-xs sm:text-sm text-white">
                  {t.simulator.haFlowTitle}
                </h3>
              </div>
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                isConnected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
              }`}>
                {isConnected ? t.simulator.connectedBadge : 'ConfigFlow'}
              </span>
            </div>

            <div className="p-4 sm:p-5 space-y-4">
              <p className="text-xs text-slate-400 leading-relaxed">
                {t.simulator.haFlowSub}
              </p>

              {errorMessage && (
                <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <div className="space-y-3">
                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">
                    {t.simulator.clientIdLabel}
                  </label>
                  <input
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    placeholder="WLK_..."
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">
                    {t.simulator.clientSecretLabel}
                  </label>
                  <input
                    type="password"
                    value={clientSecret}
                    onChange={(e) => setClientSecret(e.target.value)}
                    placeholder="sec_..."
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <button
                  onClick={handleConnect}
                  disabled={isAuthenticating}
                  className="flex-1 py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs transition cursor-pointer flex items-center justify-center gap-1.5 shadow"
                >
                  {isAuthenticating ? (
                    <>
                      <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                      <span>{t.simulator.connecting}</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{t.simulator.connectBtn}</span>
                    </>
                  )}
                </button>

                <button
                  onClick={() => {
                    setClientId('WLK_DEMO_' + Math.floor(1000 + Math.random() * 9000));
                    setClientSecret('sec_demo_' + Math.random().toString(36).substring(2, 12));
                  }}
                  className="px-2.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition cursor-pointer"
                  title={t.simulator.loadDemo}
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                </button>
              </div>

              {/* Gateway summary card */}
              <div className="pt-2 border-t border-slate-800/80">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-cyan-400" />
                    <span>{t.simulator.gatewayStatusLabel}:</span>
                  </span>
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    Online ({gateway.name})
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Live HA Event Log */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>{t.simulator.logsTitle}</span>
              </span>
              <button
                onClick={() => setLogs([])}
                className="text-[10px] text-slate-500 hover:text-slate-300 transition"
              >
                {t.simulator.clearLogs}
              </button>
            </div>
            <div className="h-40 overflow-y-auto font-mono text-[11px] space-y-1 pr-1 scrollbar-thin">
              {logs.map((log) => (
                <div key={log.id} className="text-slate-400 leading-tight">
                  <span className="text-slate-600">[{log.time}]</span>{' '}
                  <span
                    className={
                      log.type === 'success'
                        ? 'text-emerald-400'
                        : log.type === 'warn'
                        ? 'text-amber-400'
                        : 'text-slate-300'
                    }
                  >
                    {log.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Discovered Locks & Interactive Lovelace Entities (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>{t.simulator.devicesFound} ({locks.length})</span>
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Auto-Relock: 7s
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {locks.map((lock) => {
              const isLocked = lock.isLocked;
              return (
                <div
                  key={lock.id}
                  className={`bg-slate-900 border rounded-xl p-4 sm:p-5 transition shadow-md ${
                    !isLocked
                      ? 'border-emerald-500/50 bg-gradient-to-br from-slate-900 to-emerald-950/20'
                      : 'border-slate-800'
                  }`}
                >
                  {/* Top Row: Name, SN, Online status */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="text-base font-bold text-white flex items-center gap-2">
                        <span>{lock.name}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {lock.model}
                        </span>
                      </h4>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {t.simulator.lockSnLabel}: {lock.sn}
                      </p>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 font-medium">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span>Online</span>
                    </div>
                  </div>

                  {/* Lock Status Card Body */}
                  <div className="mt-4 pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    {/* Big Lock Status Indicator */}
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-12 h-12 rounded-xl flex items-center justify-center transition-transform ${
                          !isLocked
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-lg shadow-emerald-500/10'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {!isLocked ? (
                          <Unlock className="w-6 h-6 animate-pulse" />
                        ) : (
                          <Lock className="w-6 h-6" />
                        )}
                      </div>

                      <div>
                        <div className="text-sm font-bold text-white flex items-center gap-2">
                          <span>
                            {!isLocked
                              ? currentLang === 'de' ? 'Entriegelt' : currentLang === 'es' ? 'Desbloqueada' : currentLang === 'fr' ? 'Déverrouillée' : 'Unlocked'
                              : currentLang === 'de' ? 'Verriegelt' : currentLang === 'es' ? 'Bloqueada' : currentLang === 'fr' ? 'Verrouillée' : 'Locked'}
                          </span>
                          {!isLocked && (
                            <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded animate-pulse font-mono">
                              7s Auto-Relock
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          {!isLocked ? t.simulator.unlockedSuccess : 'lock.' + lock.sn.toLowerCase().replace(/[^a-z0-9]/g, '_')}
                        </p>
                      </div>
                    </div>

                    {/* Action Button */}
                    <div className="flex items-center gap-2">
                      {isLocked ? (
                        <button
                          onClick={() => handleUnlock(lock.id)}
                          disabled={lock.isUnlocking}
                          className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs sm:text-sm flex items-center gap-2 transition shadow-md shadow-emerald-600/20 cursor-pointer active:scale-95"
                        >
                          <Unlock className="w-4 h-4" />
                          <span>{t.simulator.unlockBtn}</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => handleManualLock(lock.id)}
                          className="px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs sm:text-sm flex items-center gap-2 transition border border-slate-700 cursor-pointer"
                        >
                          <Lock className="w-4 h-4 text-slate-400" />
                          <span>{t.simulator.lockBtn}</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Attributes Grid (Battery, RSSI, Last Unlock) */}
                  <div className="mt-4 pt-3 border-t border-slate-800/60 grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5 flex items-center justify-center gap-1">
                        {getBatteryIcon(lock.battery)}
                        <span>{t.simulator.batteryLabel}</span>
                      </div>
                      <span className="font-mono font-bold text-slate-200">
                        {lock.battery}%
                      </span>
                    </div>

                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5 flex items-center justify-center gap-1">
                        <Wifi className="w-3.5 h-3.5 text-cyan-400" />
                        <span>{t.simulator.signalLabel}</span>
                      </div>
                      <span className="font-mono font-bold text-slate-200">
                        {lock.rssi} dBm
                      </span>
                    </div>

                    <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5 flex items-center justify-center gap-1">
                        <KeyRound className="w-3.5 h-3.5 text-indigo-400" />
                        <span>{t.simulator.lastUnlockLabel}</span>
                      </div>
                      <span className="font-semibold text-slate-200 truncate block">
                        {lock.lastUnlockMethod} ({lock.lastUnlockTimestamp})
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
