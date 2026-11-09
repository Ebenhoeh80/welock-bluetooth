export type Language = 'de' | 'en' | 'es' | 'fr';

export interface RepoFile {
  path: string;
  name: string;
  category: 'python' | 'json' | 'markdown' | 'license' | 'shell';
  description: Record<Language, string>;
  content: string;
}

export interface ValidationRule {
  id: string;
  category: 'hacs' | 'homeassistant' | 'localization' | 'architecture';
  title: Record<Language, string>;
  description: Record<Language, string>;
  passed: boolean;
  status: 'success' | 'warning' | 'info';
  details?: Record<Language, string>;
}

export interface SimulatedLock {
  id: string;
  sn: string;
  name: string;
  model: string;
  battery: number;
  isLocked: boolean;
  isUnlocking: boolean;
  lastUnlockMethod: 'Fingerprint' | 'RFID Card' | 'Passcode' | 'App' | 'Gateway';
  lastUnlockTimestamp: string;
  rssi: number;
  online: boolean;
  wifiBoxId: string;
}

export interface SimulatedGateway {
  id: string;
  name: string;
  model: string;
  online: boolean;
  connectedLocks: number;
  ip: string;
}
