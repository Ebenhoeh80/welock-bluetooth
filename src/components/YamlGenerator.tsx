import React, { useState } from 'react';
import { Copy, Check, Code2, LayoutDashboard, Bell, Tag } from 'lucide-react';
import { Language } from '../types';
import { TRANSLATIONS } from '../i18n/translations';

interface YamlGeneratorProps {
  currentLang: Language;
}

export const YamlGenerator: React.FC<YamlGeneratorProps> = ({ currentLang }) => {
  const t = TRANSLATIONS[currentLang];
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (key: string, code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const getSnippets = () => {
    switch (currentLang) {
      case 'de':
        return [
          {
            id: 'lovelace_tile',
            icon: <LayoutDashboard className="w-4 h-4 text-cyan-400" />,
            title: t.yaml.lovelaceTileTitle,
            desc: t.yaml.lovelaceTileDesc,
            yaml: `type: tile
entity: lock.welock_haustur
name: Haustür Schloss
icon: mdi:lock-smart
features:
  - type: lock-commands
vertical: false
card_mod:
  style: |
    ha-card {
      border-radius: 16px;
    }`,
          },
          {
            id: 'battery_grid',
            icon: <LayoutDashboard className="w-4 h-4 text-emerald-400" />,
            title: t.yaml.batteryCardTitle,
            desc: t.yaml.batteryCardDesc,
            yaml: `type: grid
columns: 3
square: false
cards:
  - type: tile
    entity: sensor.welock_haustur_battery
    name: Batterie
    color: green
  - type: tile
    entity: binary_sensor.welock_haustur_lock_status
    name: Schloss-Verbindung
    color: blue
  - type: tile
    entity: binary_sensor.welock_gateway_wifibox_online
    name: WiFiBox Gateway
    color: cyan`,
          },
          {
            id: 'automation_battery',
            icon: <Bell className="w-4 h-4 text-amber-400" />,
            title: t.yaml.automationBatteryTitle,
            desc: t.yaml.automationBatteryDesc,
            yaml: `alias: "WeLock: Warnung bei schwacher Schloss-Batterie"
description: "Sendet eine Benachrichtigung, wenn die Batterien unter 20% fallen"
trigger:
  - platform: numeric_state
    entity_id: sensor.welock_haustur_battery
    below: 20
action:
  - action: notify.notify
    data:
      title: "⚠️ WeLock Batterie fast leer"
      message: "Die Batterie des Haustürschlosses beträgt nur noch {{ states('sensor.welock_haustur_battery') }}%. Bitte 3x AAA-Batterien wechseln."
mode: single`,
          },
          {
            id: 'automation_nfc',
            icon: <Tag className="w-4 h-4 text-indigo-400" />,
            title: t.yaml.automationNfcTitle,
            desc: t.yaml.automationNfcDesc,
            yaml: `alias: "WeLock: Haustür mit NFC-Tag entriegeln"
description: "Entriegelt das WeLock-Schloss beim Scannen eines authorisierten NFC-Chips"
trigger:
  - platform: tag
    tag_id: 84a7-9f20-haustuer-nfc
action:
  - action: lock.unlock
    target:
      entity_id: lock.welock_haustur
  - action: notify.notify
    data:
      message: "Haustür wurde via NFC-Tag autorisiert und entriegelt."
mode: restart`,
          },
        ];

      case 'es':
        return [
          {
            id: 'lovelace_tile',
            icon: <LayoutDashboard className="w-4 h-4 text-cyan-400" />,
            title: t.yaml.lovelaceTileTitle,
            desc: t.yaml.lovelaceTileDesc,
            yaml: `type: tile
entity: lock.welock_puerta_principal
name: Cerradura Principal
icon: mdi:lock-smart
features:
  - type: lock-commands
vertical: false`,
          },
          {
            id: 'battery_grid',
            icon: <LayoutDashboard className="w-4 h-4 text-emerald-400" />,
            title: t.yaml.batteryCardTitle,
            desc: t.yaml.batteryCardDesc,
            yaml: `type: grid
columns: 3
square: false
cards:
  - type: tile
    entity: sensor.welock_puerta_principal_bateria
    name: Batería
    color: green
  - type: tile
    entity: binary_sensor.welock_puerta_principal_estado
    name: Estado Cerradura
    color: blue
  - type: tile
    entity: binary_sensor.welock_gateway_wifibox_online
    name: Pasarela WiFiBox
    color: cyan`,
          },
          {
            id: 'automation_battery',
            icon: <Bell className="w-4 h-4 text-amber-400" />,
            title: t.yaml.automationBatteryTitle,
            desc: t.yaml.automationBatteryDesc,
            yaml: `alias: "WeLock: Alerta de batería baja"
description: "Notifica cuando la batería de la cerradura baja del 20%"
trigger:
  - platform: numeric_state
    entity_id: sensor.welock_puerta_principal_bateria
    below: 20
action:
  - action: notify.notify
    data:
      title: "⚠️ Batería WeLock Baja"
      message: "La batería de la cerradura principal está al {{ states('sensor.welock_puerta_principal_bateria') }}%. Cambie las pilas AAA pronto."
mode: single`,
          },
          {
            id: 'automation_nfc',
            icon: <Tag className="w-4 h-4 text-indigo-400" />,
            title: t.yaml.automationNfcTitle,
            desc: t.yaml.automationNfcDesc,
            yaml: `alias: "WeLock: Desbloqueo con etiqueta NFC"
description: "Desbloquea la cerradura al escanear la tarjeta o etiqueta NFC autorizada"
trigger:
  - platform: tag
    tag_id: id-etiqueta-nfc-puerta
action:
  - action: lock.unlock
    target:
      entity_id: lock.welock_puerta_principal
mode: restart`,
          },
        ];

      case 'fr':
        return [
          {
            id: 'lovelace_tile',
            icon: <LayoutDashboard className="w-4 h-4 text-cyan-400" />,
            title: t.yaml.lovelaceTileTitle,
            desc: t.yaml.lovelaceTileDesc,
            yaml: `type: tile
entity: lock.welock_porte_principale
name: Serrure Porte Principale
icon: mdi:lock-smart
features:
  - type: lock-commands
vertical: false`,
          },
          {
            id: 'battery_grid',
            icon: <LayoutDashboard className="w-4 h-4 text-emerald-400" />,
            title: t.yaml.batteryCardTitle,
            desc: t.yaml.batteryCardDesc,
            yaml: `type: grid
columns: 3
square: false
cards:
  - type: tile
    entity: sensor.welock_porte_principale_batterie
    name: Batterie
    color: green
  - type: tile
    entity: binary_sensor.welock_porte_principale_etat
    name: État Serrure
    color: blue
  - type: tile
    entity: binary_sensor.welock_gateway_wifibox_online
    name: Passerelle WiFiBox
    color: cyan`,
          },
          {
            id: 'automation_battery',
            icon: <Bell className="w-4 h-4 text-amber-400" />,
            title: t.yaml.automationBatteryTitle,
            desc: t.yaml.automationBatteryDesc,
            yaml: `alias: "WeLock: Alerte batterie faible"
description: "Envoie une alerte lorsque la batterie passe sous les 20%"
trigger:
  - platform: numeric_state
    entity_id: sensor.welock_porte_principale_batterie
    below: 20
action:
  - action: notify.notify
    data:
      title: "⚠️ Batterie WeLock faible"
      message: "Le niveau de batterie de la serrure est à {{ states('sensor.welock_porte_principale_batterie') }}%. Veuillez remplacer les piles AAA."
mode: single`,
          },
          {
            id: 'automation_nfc',
            icon: <Tag className="w-4 h-4 text-indigo-400" />,
            title: t.yaml.automationNfcTitle,
            desc: t.yaml.automationNfcDesc,
            yaml: `alias: "WeLock: Déverrouillage par badge NFC"
description: "Déverrouille la serrure lors du scan d'un badge NFC autorisé"
trigger:
  - platform: tag
    tag_id: badge-nfc-porte-entree
action:
  - action: lock.unlock
    target:
      entity_id: lock.welock_porte_principale
mode: restart`,
          },
        ];

      default: // en
        return [
          {
            id: 'lovelace_tile',
            icon: <LayoutDashboard className="w-4 h-4 text-cyan-400" />,
            title: t.yaml.lovelaceTileTitle,
            desc: t.yaml.lovelaceTileDesc,
            yaml: `type: tile
entity: lock.welock_front_door
name: Front Door Lock
icon: mdi:lock-smart
features:
  - type: lock-commands
vertical: false`,
          },
          {
            id: 'battery_grid',
            icon: <LayoutDashboard className="w-4 h-4 text-emerald-400" />,
            title: t.yaml.batteryCardTitle,
            desc: t.yaml.batteryCardDesc,
            yaml: `type: grid
columns: 3
square: false
cards:
  - type: tile
    entity: sensor.welock_front_door_battery
    name: Battery
    color: green
  - type: tile
    entity: binary_sensor.welock_front_door_lock_status
    name: Lock Status
    color: blue
  - type: tile
    entity: binary_sensor.welock_gateway_wifibox_online
    name: WiFiBox Gateway
    color: cyan`,
          },
          {
            id: 'automation_battery',
            icon: <Bell className="w-4 h-4 text-amber-400" />,
            title: t.yaml.automationBatteryTitle,
            desc: t.yaml.automationBatteryDesc,
            yaml: `alias: "WeLock: Low Battery Alert"
description: "Send push notification when cylinder battery drops below 20%"
trigger:
  - platform: numeric_state
    entity_id: sensor.welock_front_door_battery
    below: 20
action:
  - action: notify.notify
    data:
      title: "⚠️ WeLock Battery Low"
      message: "Front door lock battery is down to {{ states('sensor.welock_front_door_battery') }}%. Please replace the 3x AAA batteries soon."
mode: single`,
          },
          {
            id: 'automation_nfc',
            icon: <Tag className="w-4 h-4 text-indigo-400" />,
            title: t.yaml.automationNfcTitle,
            desc: t.yaml.automationNfcDesc,
            yaml: `alias: "WeLock: Unlock Front Door with NFC Tag"
description: "Unlocks the smart lock when an authorized NFC tag is scanned"
trigger:
  - platform: tag
    tag_id: your-nfc-tag-id-here
action:
  - action: lock.unlock
    target:
      entity_id: lock.welock_front_door
mode: restart`,
          },
        ];
    }
  };

  const snippets = getSnippets();

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5">
        <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
          <Code2 className="w-5 h-5 text-cyan-400" />
          <span>{t.yaml.title}</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          {t.yaml.subtitle}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {snippets.map((snip) => (
          <div
            key={snip.id}
            className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col shadow-md"
          >
            {/* Header */}
            <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {snip.icon}
                <h3 className="font-semibold text-xs sm:text-sm text-white">
                  {snip.title}
                </h3>
              </div>
              <button
                onClick={() => handleCopy(snip.id, snip.yaml)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 transition cursor-pointer"
              >
                {copiedKey === snip.id ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">{t.yaml.copiedYaml}</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>{t.yaml.copyYaml}</span>
                  </>
                )}
              </button>
            </div>

            {/* Description */}
            <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800/80 text-xs text-slate-400">
              {snip.desc}
            </div>

            {/* Code */}
            <div className="p-4 bg-slate-950 flex-1 overflow-x-auto font-mono text-xs text-cyan-300 leading-relaxed select-text">
              <pre>{snip.yaml}</pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
