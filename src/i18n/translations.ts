import { Language } from '../types';

export interface TranslationDict {
  appTitle: string;
  appSubtitle: string;
  repoBadge: string;
  forkOf: string;
  hacsCertified: string;
  fourLanguagesReady: string;

  // Navigation tabs
  tabs: {
    explorer: string;
    simulator: string;
    yaml: string;
    validator: string;
    guide: string;
  };

  // Quick action buttons
  downloadZip: string;
  downloadZipSub: string;
  copyRepoUrl: string;
  copied: string;
  openGithub: string;

  // Language selector
  selectLanguage: string;
  languages: {
    de: string;
    en: string;
    es: string;
    fr: string;
  };

  // Explorer tab
  explorer: {
    title: string;
    subtitle: string;
    fileTree: string;
    copyFile: string;
    copiedFile: string;
    allFilesValid: string;
    translationComparisonTitle: string;
    translationComparisonSub: string;
    keyLabel: string;
    filterPlaceholder: string;
  };

  // Simulator tab
  simulator: {
    title: string;
    subtitle: string;
    simulationNotice: string;
    haFlowTitle: string;
    haFlowSub: string;
    clientIdLabel: string;
    clientSecretLabel: string;
    loadDemo: string;
    clear: string;
    connectBtn: string;
    connecting: string;
    connectedBadge: string;
    devicesFound: string;
    unlockedSuccess: string;
    lockingAuto: string;
    unlockBtn: string;
    lockBtn: string;
    batteryLabel: string;
    signalLabel: string;
    lastUnlockLabel: string;
    gatewayStatusLabel: string;
    lockSnLabel: string;
    logsTitle: string;
    clearLogs: string;
  };

  // YAML Tab
  yaml: {
    title: string;
    subtitle: string;
    lovelaceTileTitle: string;
    lovelaceTileDesc: string;
    batteryCardTitle: string;
    batteryCardDesc: string;
    automationBatteryTitle: string;
    automationBatteryDesc: string;
    automationNfcTitle: string;
    automationNfcDesc: string;
    copyYaml: string;
    copiedYaml: string;
  };

  // Validator Tab
  validator: {
    title: string;
    subtitle: string;
    scoreLabel: string;
    passAll: string;
    checkManifest: string;
    checkManifestDesc: string;
    checkHacsJson: string;
    checkHacsJsonDesc: string;
    checkConfigFlow: string;
    checkConfigFlowDesc: string;
    checkTranslations: string;
    checkTranslationsDesc: string;
    checkCoordinator: string;
    checkCoordinatorDesc: string;
    checkSecurity: string;
    checkSecurityDesc: string;
    rulePassed: string;
  };

  // Guide Tab
  guide: {
    title: string;
    subtitle: string;
    step1Title: string;
    step1Desc: string;
    step2Title: string;
    step2Desc: string;
    step3Title: string;
    step3Desc: string;
    step4Title: string;
    step4Desc: string;
    importantTipTitle: string;
    importantTipText: string;
  };
}

export const TRANSLATIONS: Record<Language, TranslationDict> = {
  de: {
    appTitle: 'WeLock — Home Assistant HACS Integration',
    appSubtitle: 'Offizielle HACS / Marketplace Suite für WeLock Smart Locks mit vollständiger 4-Sprachen-Lokalisierung.',
    repoBadge: 'Ebenhoeh80/welock-aistudio',
    forkOf: 'Suite: Ebenhoeh80/welock-aistudio',
    hacsCertified: 'HACS / Marketplace 2024–2026 Konform',
    fourLanguagesReady: '4 Sprachen: Deutsch • English • Español • Français',

    tabs: {
      explorer: 'Dateien & Code',
      simulator: 'Home Assistant Simulator',
      yaml: 'Dashboard & Automationen (YAML)',
      validator: 'HACS Konformitätsprüfung',
      guide: 'Installationsanleitung',
    },

    downloadZip: 'Integration als ZIP herunterladen',
    downloadZipSub: 'Direkt in config/custom_components/welock entpacken',
    copyRepoUrl: 'Repository-URL kopieren',
    copied: 'Kopiert!',
    openGithub: 'GitHub Repository',

    selectLanguage: 'Sprache wählen',
    languages: {
      de: 'Deutsch',
      en: 'English',
      es: 'Español',
      fr: 'Français',
    },

    explorer: {
      title: 'Integrations-Dateistruktur',
      subtitle: 'Alle Python-, JSON- und Markdown-Komponenten für custom_components/welock',
      fileTree: 'Dateibaum',
      copyFile: 'Code kopieren',
      copiedFile: 'Code in Zwischenablage kopiert!',
      allFilesValid: '11 von 11 Dateien vollständig generiert',
      translationComparisonTitle: 'Viersprachiger Lokalisierungs-Vergleich',
      translationComparisonSub: 'Gegenüberstellung der Zeichenketten in Deutsch, Englisch, Spanisch und Französisch',
      keyLabel: 'Schlüssel (Translation Key)',
      filterPlaceholder: 'Dateien durchsuchen...',
    },

    simulator: {
      title: 'Interaktiver Home Assistant Simulator',
      subtitle: 'Testen Sie den Konfigurationsassistenten und die Schlosssteuerung live im Browser.',
      simulationNotice: 'Live-Simulation der WeLock Cloud API (api.welockglobal.com) mit automatischer Entriegelung und mechanischem Auto-Relock.',
      haFlowTitle: 'WeLock Smart Lock Einrichtung',
      haFlowSub: 'Geben Sie Ihre WeLock API-Zugangsdaten ein, die Sie in der WeLock Mobile-App finden (Seitenmenü -> Home Assistant).',
      clientIdLabel: 'Client-ID',
      clientSecretLabel: 'Client-Secret',
      loadDemo: 'Demo-Zugangsdaten laden',
      clear: 'Zurücksetzen',
      connectBtn: 'Verbindung herstellen',
      connecting: 'Authentifiziere mit WeLock Cloud...',
      connectedBadge: 'Verbunden mit WeLock Cloud',
      devicesFound: 'Erkannte Geräte',
      unlockedSuccess: 'Schloss entriegelt! Knauf kann gedreht werden.',
      lockingAuto: 'Mechanische Rückstellung (Auto-Relock) in 7s...',
      unlockBtn: 'Tür entriegeln',
      lockBtn: 'Verriegelt',
      batteryLabel: 'Batteriestand',
      signalLabel: 'Signalstärke (RSSI)',
      lastUnlockLabel: 'Letzte Entriegelung',
      gatewayStatusLabel: 'WiFiBox Gateway',
      lockSnLabel: 'Seriennummer (SN)',
      logsTitle: 'Home Assistant Live-Ereignisprotokoll',
      clearLogs: 'Protokoll leeren',
    },

    yaml: {
      title: 'Home Assistant Dashboards & Automationen',
      subtitle: 'Fertige YAML-Konfigurationen für Lovelace-Karten und Benachrichtigungen.',
      lovelaceTileTitle: 'Lovelace Schloss-Kachelkarte (Tile Card)',
      lovelaceTileDesc: 'Moderne Kachelkarte mit Schnell-Entriegelungsbutton und Batteriestatus.',
      batteryCardTitle: 'Lovelace Batterie- und Status-Raster',
      batteryCardDesc: 'Übersichtskarte für Batteriestand, Gateway-Verbindung und RSSI.',
      automationBatteryTitle: 'Automation: Warnung bei schwacher Batterie (< 20%)',
      automationBatteryDesc: 'Sendet eine Push-Benachrichtigung an Ihr Smartphone, wenn die Batterien gewechselt werden müssen.',
      automationNfcTitle: 'Automation: Tür öffnen mit NFC-Tag oder RFID-Chip',
      automationNfcDesc: 'Entriegelt das WeLock-Schloss sofort beim Scannen eines autorisierten Tags.',
      copyYaml: 'YAML kopieren',
      copiedYaml: 'YAML in Zwischenablage kopiert!',
    },

    validator: {
      title: 'HACS & Home Assistant Qualitätsprüfung',
      subtitle: 'Automatische Verifizierung aller Kriterien für den Home Assistant Community Store.',
      scoreLabel: 'Konformitäts-Score',
      passAll: 'Alle 6 Prüfpunkte erfolgreich bestanden (100% Bereit für HACS)',
      checkManifest: 'manifest.json Struktur & IoT-Klasse',
      checkManifestDesc: 'Gültige Domain "welock", Version 1.3.0, codeowners @Ebenhoeh80 und "cloud_polling".',
      checkHacsJson: 'HACS Store Metadaten (hacs.json)',
      checkHacsJsonDesc: 'Kompatibilitätsangabe (homeassistant: 2024.1.0) und render_readme aktiviert.',
      checkConfigFlow: 'Grafischer Einrichtungsassistent (config_flow.py)',
      checkConfigFlowDesc: 'Vollständiger ConfigFlow und OptionsFlow ohne YAML-Zwang.',
      checkTranslations: '4-Sprachen-Lokalisierung (de, en, es, fr)',
      checkTranslationsDesc: 'Alle Übersetzungsdateien mit vollständigen Schlüsseln für Dialoge, Fehler und Sensoren.',
      checkCoordinator: 'DataUpdateCoordinator Architektur',
      checkCoordinatorDesc: 'Zentralisierte Abfrage und asynchrone Fehlerbehandlung über aiohttp.',
      checkSecurity: 'Sicherheits- & Token-Handling',
      checkSecurityDesc: 'Keine hartkodierten Zugangsdaten, Berechtigungsprüfung und Reauth-Flow.',
      rulePassed: 'Bestanden',
    },

    guide: {
      title: 'Schritt-für-Schritt Installationsanleitung',
      subtitle: 'So fügen Sie das WeLock-Repository in Ihr Home Assistant System ein.',
      step1Title: '1. API-Zugangsdaten in der WeLock-App abrufen',
      step1Desc: 'Öffnen Sie die offizielle WeLock-App auf Ihrem Smartphone. Stellen Sie sicher, dass Ihr Schloss mit einer WeLock WiFiBox verbunden ist. Öffnen Sie das Seitenmenü (☰) und tippen Sie auf das "Home Assistant"-Symbol. Kopieren Sie Ihre Client-ID und das Client-Secret.',
      step2Title: '2. Repository in HACS hinzufügen',
      step2Desc: 'Öffnen Sie Home Assistant -> HACS -> Integrationen -> Menü oben rechts (drei Punkte) -> "Benutzerdefinierte Repositories". Fügen Sie die URL https://github.com/Ebenhoeh80/welock-aistudio ein und wählen Sie als Kategorie "Integration".',
      step3Title: '3. Integration herunterladen & Home Assistant neu starten',
      step3Desc: 'Suchen Sie in HACS nach "WeLock Smart Lock", klicken Sie auf "Herunterladen" und starten Sie Home Assistant einmalig unter Einstellungen -> System -> Neustart neu.',
      step4Title: '4. Einrichten unter Geräte & Dienste',
      step4Desc: 'Gehen Sie zu Einstellungen -> Geräte & Dienste -> "Integration hinzufügen", suchen Sie nach "WeLock Smart Lock" und geben Sie Ihre Client-ID sowie Ihr Client-Secret ein.',
      importantTipTitle: 'Wichtiger Hinweis zum WeLock WiFiBox Gateway',
      importantTipText: 'WeLock Smart Locks kommunizieren vor Ort via Bluetooth (BLE). Für die Fernsteuerung über Home Assistant ist zwingend eine WeLock WiFiBox (WiFiBox 2 oder WiFiBox 3) erforderlich, die als Brücke zwischen der Cloud und dem Schloss dient.',
    },
  },

  en: {
    appTitle: 'WeLock — Home Assistant HACS Integration',
    appSubtitle: 'Official HACS / Marketplace integration suite for WeLock Smart Locks with full 4-language localization.',
    repoBadge: 'Ebenhoeh80/welock-aistudio',
    forkOf: 'Suite: Ebenhoeh80/welock-aistudio',
    hacsCertified: 'HACS / Marketplace 2024–2026 Compliant',
    fourLanguagesReady: '4 Languages: Deutsch • English • Español • Français',

    tabs: {
      explorer: 'Files & Code',
      simulator: 'Home Assistant Simulator',
      yaml: 'Dashboard & Automations (YAML)',
      validator: 'HACS Compliance Checker',
      guide: 'Installation Guide',
    },

    downloadZip: 'Download Integration (.ZIP)',
    downloadZipSub: 'Extract directly into config/custom_components/welock',
    copyRepoUrl: 'Copy Repository URL',
    copied: 'Copied!',
    openGithub: 'GitHub Repository',

    selectLanguage: 'Select Language',
    languages: {
      de: 'Deutsch',
      en: 'English',
      es: 'Español',
      fr: 'Français',
    },

    explorer: {
      title: 'Integration File Structure',
      subtitle: 'All Python, JSON, and Markdown files for custom_components/welock',
      fileTree: 'File Tree',
      copyFile: 'Copy Code',
      copiedFile: 'Code copied to clipboard!',
      allFilesValid: '11 of 11 files completely generated',
      translationComparisonTitle: '4-Language Translation Matrix',
      translationComparisonSub: 'Side-by-side comparison of strings across German, English, Spanish, and French',
      keyLabel: 'Translation Key',
      filterPlaceholder: 'Search files...',
    },

    simulator: {
      title: 'Interactive Home Assistant Simulator',
      subtitle: 'Experience the config flow wizard and lock controls right inside your browser.',
      simulationNotice: 'Live simulation of the WeLock Cloud API (api.welockglobal.com) with remote unlock and mechanical auto-relock.',
      haFlowTitle: 'WeLock Smart Lock Setup',
      haFlowSub: 'Enter your WeLock API credentials obtained from the WeLock mobile application (Sidebar Menu -> Home Assistant).',
      clientIdLabel: 'Client ID',
      clientSecretLabel: 'Client Secret',
      loadDemo: 'Load Demo Credentials',
      clear: 'Reset',
      connectBtn: 'Connect to WeLock',
      connecting: 'Authenticating with WeLock Cloud...',
      connectedBadge: 'Connected to WeLock Cloud',
      devicesFound: 'Discovered Devices',
      unlockedSuccess: 'Door unlocked! The cylinder knob can now be turned.',
      lockingAuto: 'Mechanical auto-relock reset in 7s...',
      unlockBtn: 'Unlock Door',
      lockBtn: 'Locked',
      batteryLabel: 'Battery Level',
      signalLabel: 'Signal Strength (RSSI)',
      lastUnlockLabel: 'Last Unlock Method',
      gatewayStatusLabel: 'WiFiBox Gateway',
      lockSnLabel: 'Serial Number (SN)',
      logsTitle: 'Home Assistant Live Event Log',
      clearLogs: 'Clear Log',
    },

    yaml: {
      title: 'Home Assistant Dashboards & Automations',
      subtitle: 'Ready-to-use YAML snippets for Lovelace cards and push alerts.',
      lovelaceTileTitle: 'Lovelace Lock Tile Card',
      lovelaceTileDesc: 'Clean modern tile card with quick unlock action and battery state indicator.',
      batteryCardTitle: 'Lovelace Battery & Connectivity Grid',
      batteryCardDesc: 'Overview grid displaying battery percentage, gateway status, and RSSI.',
      automationBatteryTitle: 'Automation: Low Battery Notification (< 20%)',
      automationBatteryDesc: 'Sends a smartphone push notification when cylinder AAA batteries require replacement.',
      automationNfcTitle: 'Automation: Instant Unlock on NFC / RFID Tag',
      automationNfcDesc: 'Instantly unlocks the WeLock cylinder when an authorized NFC card or sticker is scanned.',
      copyYaml: 'Copy YAML',
      copiedYaml: 'YAML copied to clipboard!',
    },

    validator: {
      title: 'HACS & Marketplace Compliance Check',
      subtitle: 'Automated verification against Home Assistant Community Store standards.',
      scoreLabel: 'Compliance Score',
      passAll: 'All 6 checks passed successfully (100% Ready for HACS)',
      checkManifest: 'manifest.json Structure & IoT Class',
      checkManifestDesc: 'Valid domain "welock", version 1.3.0, codeowners @Ebenhoeh80, and "cloud_polling".',
      checkHacsJson: 'HACS Store Metadata (hacs.json)',
      checkHacsJsonDesc: 'Includes minimum Home Assistant version (2024.1.0) and render_readme flag.',
      checkConfigFlow: 'Graphical Setup Flow (config_flow.py)',
      checkConfigFlowDesc: 'Full ConfigFlow and OptionsFlow with zero mandatory YAML setup.',
      checkTranslations: '4-Language Localization (de, en, es, fr)',
      checkTranslationsDesc: 'Comprehensive translation files covering setup steps, errors, and entity names.',
      checkCoordinator: 'DataUpdateCoordinator Architecture',
      checkCoordinatorDesc: 'Centralized periodic polling and async error handling via aiohttp.',
      checkSecurity: 'Security & Token Handling',
      checkSecurityDesc: 'No hardcoded secrets, robust token refreshing, and reauthentication flow.',
      rulePassed: 'Passed',
    },

    guide: {
      title: 'Step-by-Step Installation Guide',
      subtitle: 'How to install and configure this custom integration in Home Assistant.',
      step1Title: '1. Retrieve Credentials in the WeLock App',
      step1Desc: 'Open the official WeLock app on your mobile device. Ensure your lock is connected to a WeLock WiFiBox gateway. Open the sidebar (☰) and tap the "Home Assistant" icon. Copy your Client ID and Client Secret.',
      step2Title: '2. Add Custom Repository in HACS',
      step2Desc: 'In Home Assistant, navigate to HACS -> Integrations -> top-right menu (three dots) -> "Custom repositories". Paste https://github.com/Ebenhoeh80/welock-aistudio and select "Integration" as the category.',
      step3Title: '3. Download & Restart Home Assistant',
      step3Desc: 'Search for "WeLock Smart Lock" in HACS, click "Download", then restart Home Assistant from Settings -> System -> Restart.',
      step4Title: '4. Add Integration in Devices & Services',
      step4Desc: 'Navigate to Settings -> Devices & Services -> "Add Integration", search for "WeLock Smart Lock", and enter your Client ID and Client Secret.',
      importantTipTitle: 'Important Note Regarding WeLock WiFiBox',
      importantTipText: 'WeLock cylinders operate locally via Bluetooth Low Energy (BLE). Remote cloud control through Home Assistant requires an active WeLock WiFiBox (WiFiBox 2 or WiFiBox 3) bridging your locks to the internet.',
    },
  },

  es: {
    appTitle: 'WeLock — Integración HACS para Home Assistant',
    appSubtitle: 'Suite oficial de integración HACS / Marketplace para cerraduras inteligentes WeLock con localización en 4 idiomas.',
    repoBadge: 'Ebenhoeh80/welock-aistudio',
    forkOf: 'Suite: Ebenhoeh80/welock-aistudio',
    hacsCertified: 'Compatible con HACS / Marketplace 2024–2026',
    fourLanguagesReady: '4 Idiomas: Deutsch • English • Español • Français',

    tabs: {
      explorer: 'Archivos y Código',
      simulator: 'Simulador Home Assistant',
      yaml: 'Panel y Automatizaciones (YAML)',
      validator: 'Validador de HACS',
      guide: 'Guía de Instalación',
    },

    downloadZip: 'Descargar Integración (.ZIP)',
    downloadZipSub: 'Descomprimir en config/custom_components/welock',
    copyRepoUrl: 'Copiar URL del Repositorio',
    copied: '¡Copiado!',
    openGithub: 'Repositorio GitHub',

    selectLanguage: 'Seleccionar Idioma',
    languages: {
      de: 'Deutsch',
      en: 'English',
      es: 'Español',
      fr: 'Français',
    },

    explorer: {
      title: 'Estructura de Archivos de la Integración',
      subtitle: 'Todos los archivos Python, JSON y Markdown para custom_components/welock',
      fileTree: 'Árbol de archivos',
      copyFile: 'Copiar código',
      copiedFile: '¡Código copiado al portapapeles!',
      allFilesValid: '11 de 11 archivos generados por completo',
      translationComparisonTitle: 'Matriz de Traducción en 4 Idiomas',
      translationComparisonSub: 'Comparativa paralela de cadenas en alemán, inglés, español y francés',
      keyLabel: 'Clave de traducción',
      filterPlaceholder: 'Buscar archivos...',
    },

    simulator: {
      title: 'Simulador Interactivo de Home Assistant',
      subtitle: 'Pruebe el asistente de configuración y el control de la cerradura en su navegador.',
      simulationNotice: 'Simulación en vivo de la API WeLock Cloud (api.welockglobal.com) con desbloqueo remoto y bloqueo mecánico.',
      haFlowTitle: 'Configuración de WeLock Smart Lock',
      haFlowSub: 'Introduce tus credenciales de API obtenidas en la aplicación móvil de WeLock (Menú lateral -> Home Assistant).',
      clientIdLabel: 'Client ID',
      clientSecretLabel: 'Client Secret',
      loadDemo: 'Cargar credenciales de prueba',
      clear: 'Restablecer',
      connectBtn: 'Conectar con WeLock',
      connecting: 'Autenticando con WeLock Cloud...',
      connectedBadge: 'Conectado a WeLock Cloud',
      devicesFound: 'Dispositivos detectados',
      unlockedSuccess: '¡Cerradura desbloqueada! El pomo ya se puede girar.',
      lockingAuto: 'Rebloqueo mecánico automático en 7s...',
      unlockBtn: 'Desbloquear puerta',
      lockBtn: 'Bloqueada',
      batteryLabel: 'Nivel de batería',
      signalLabel: 'Intensidad de señal (RSSI)',
      lastUnlockLabel: 'Último método de apertura',
      gatewayStatusLabel: 'Pasarela WiFiBox',
      lockSnLabel: 'Número de serie (SN)',
      logsTitle: 'Registro de eventos en vivo de Home Assistant',
      clearLogs: 'Limpiar registro',
    },

    yaml: {
      title: 'Paneles y Automatizaciones de Home Assistant',
      subtitle: 'Fragmentos YAML listos para usar en tarjetas Lovelace y notificaciones.',
      lovelaceTileTitle: 'Tarjeta Tile de Cerradura en Lovelace',
      lovelaceTileDesc: 'Tarjeta moderna con botón rápido de desbloqueo e indicador de batería.',
      batteryCardTitle: 'Cuadrícula de Batería y Conectividad',
      batteryCardDesc: 'Panel de resumen con porcentaje de batería, estado de gateway y RSSI.',
      automationBatteryTitle: 'Automatización: Alerta de batería baja (< 20%)',
      automationBatteryDesc: 'Envía una notificación al móvil cuando es necesario cambiar las pilas de la cerradura.',
      automationNfcTitle: 'Automatización: Desbloqueo inmediato con etiqueta NFC',
      automationNfcDesc: 'Desbloquea la cerradura al escanear una tarjeta o llavero NFC autorizado.',
      copyYaml: 'Copiar YAML',
      copiedYaml: '¡YAML copiado al portapapeles!',
    },

    validator: {
      title: 'Verificación de Estándares HACS y Home Assistant',
      subtitle: 'Comprobación automática de las normas del Home Assistant Community Store.',
      scoreLabel: 'Puntuación de Cumplimiento',
      passAll: 'Las 6 pruebas superadas con éxito (100% Listo para HACS)',
      checkManifest: 'Estructura de manifest.json y Clase IoT',
      checkManifestDesc: 'Dominio "welock" válido, versión 1.3.0, propietarios @Ebenhoeh80 y "cloud_polling".',
      checkHacsJson: 'Metadatos de HACS (hacs.json)',
      checkHacsJsonDesc: 'Versión mínima requerida (homeassistant: 2024.1.0) y opción render_readme activa.',
      checkConfigFlow: 'Flujo de Configuración Gráfica (config_flow.py)',
      checkConfigFlowDesc: 'ConfigFlow y OptionsFlow completos sin necesidad obligatoria de YAML.',
      checkTranslations: 'Localización en 4 Idiomas (de, en, es, fr)',
      checkTranslationsDesc: 'Archivos de traducción completos para pasos de inicio, errores y sensores.',
      checkCoordinator: 'Arquitectura DataUpdateCoordinator',
      checkCoordinatorDesc: 'Sondeo centralizado periódico y gestión asíncrona de errores mediante aiohttp.',
      checkSecurity: 'Seguridad y Manejo de Tokens',
      checkSecurityDesc: 'Sin credenciales expuestas, renovación de tokens y flujo de reautenticación.',
      rulePassed: 'Superado',
    },

    guide: {
      title: 'Guía de Instalación Paso a Paso',
      subtitle: 'Cómo instalar y activar la integración en su sistema Home Assistant.',
      step1Title: '1. Obtener credenciales en la App WeLock',
      step1Desc: 'Abra la app WeLock en su teléfono. Verifique que la cerradura esté enlazada a un gateway WiFiBox. Vaya al menú lateral (☰) y pulse sobre el icono de "Home Assistant". Copie el Client ID y el Client Secret.',
      step2Title: '2. Añadir repositorio personalizado en HACS',
      step2Desc: 'En Home Assistant, abra HACS -> Integraciones -> menú superior derecho (tres puntos) -> "Repositorios personalizados". Pegue https://github.com/Ebenhoeh80/welock-aistudio y elija "Integración".',
      step3Title: '3. Descargar y reiniciar Home Assistant',
      step3Desc: 'Busque "WeLock Smart Lock" en HACS, pulse "Descargar" y reinicie Home Assistant desde Ajustes -> Sistema -> Reiniciar.',
      step4Title: '4. Configurar en Dispositivos y Servicios',
      step4Desc: 'Vaya a Ajustes -> Dispositivos y servicios -> "Añadir integración", busque "WeLock Smart Lock" e introduzca su Client ID y Client Secret.',
      importantTipTitle: 'Nota importante sobre la pasarela WeLock WiFiBox',
      importantTipText: 'Las cerraduras WeLock funcionan localmente vía Bluetooth (BLE). Para el control remoto a través de Home Assistant es indispensable disponer de un gateway WeLock WiFiBox conectado a su red WiFi.',
    },
  },

  fr: {
    appTitle: 'WeLock — Intégration HACS pour Home Assistant',
    appSubtitle: 'Suite officielle d’intégration HACS / Marketplace pour serrures connectées WeLock avec support complet en 4 langues.',
    repoBadge: 'Ebenhoeh80/welock-aistudio',
    forkOf: 'Suite : Ebenhoeh80/welock-aistudio',
    hacsCertified: 'Conforme HACS / Marketplace 2024–2026',
    fourLanguagesReady: '4 Langues : Deutsch • English • Español • Français',

    tabs: {
      explorer: 'Fichiers & Code',
      simulator: 'Simulateur Home Assistant',
      yaml: 'Tableaux & Automatisations (YAML)',
      validator: 'Validateur HACS',
      guide: 'Guide d’installation',
    },

    downloadZip: 'Télécharger l’intégration (.ZIP)',
    downloadZipSub: 'À extraire dans config/custom_components/welock',
    copyRepoUrl: 'Copier l’URL du dépôt',
    copied: 'Copié !',
    openGithub: 'Dépôt GitHub',

    selectLanguage: 'Choisir la langue',
    languages: {
      de: 'Deutsch',
      en: 'English',
      es: 'Español',
      fr: 'Français',
    },

    explorer: {
      title: 'Arborescence des fichiers de l’intégration',
      subtitle: 'Tous les fichiers Python, JSON et Markdown pour custom_components/welock',
      fileTree: 'Arborescence',
      copyFile: 'Copier le code',
      copiedFile: 'Code copié dans le presse-papiers !',
      allFilesValid: '11 fichiers sur 11 générés avec succès',
      translationComparisonTitle: 'Matrice de traduction en 4 langues',
      translationComparisonSub: 'Comparaison simultanée des clés en allemand, anglais, espagnol et français',
      keyLabel: 'Clé de traduction',
      filterPlaceholder: 'Rechercher des fichiers...',
    },

    simulator: {
      title: 'Simulateur Interactif Home Assistant',
      subtitle: 'Testez l’assistant de configuration et le contrôle de la serrure directement dans le navigateur.',
      simulationNotice: 'Simulation en direct de l’API WeLock Cloud (api.welockglobal.com) avec déverrouillage et réenclenchement mécanique.',
      haFlowTitle: 'Configuration de WeLock Smart Lock',
      haFlowSub: 'Entrez vos identifiants d’API WeLock obtenus dans l’application mobile WeLock (Menu latéral -> Home Assistant).',
      clientIdLabel: 'Client ID',
      clientSecretLabel: 'Client Secret',
      loadDemo: 'Charger les identifiants de démo',
      clear: 'Réinitialiser',
      connectBtn: 'Connecter à WeLock',
      connecting: 'Authentification auprès du Cloud WeLock...',
      connectedBadge: 'Connecté au Cloud WeLock',
      devicesFound: 'Appareils détectés',
      unlockedSuccess: 'Serrure déverrouillée ! Le bouton cylindrique peut maintenant être tourné.',
      lockingAuto: 'Réenclenchement mécanique automatique dans 7s...',
      unlockBtn: 'Déverrouiller la porte',
      lockBtn: 'Verrouillée',
      batteryLabel: 'Niveau de batterie',
      signalLabel: 'Puissance du signal (RSSI)',
      lastUnlockLabel: 'Dernière méthode de déverrouillage',
      gatewayStatusLabel: 'Passerelle WiFiBox',
      lockSnLabel: 'Numéro de série (SN)',
      logsTitle: 'Journal d’événements en direct Home Assistant',
      clearLogs: 'Effacer le journal',
    },

    yaml: {
      title: 'Tableaux de bord et Automatisations Home Assistant',
      subtitle: 'Extraits YAML prêts à l’emploi pour cartes Lovelace et alertes.',
      lovelaceTileTitle: 'Carte Tuile (Tile) de Serrure Lovelace',
      lovelaceTileDesc: 'Carte moderne avec action rapide de déverrouillage et indicateur de batterie.',
      batteryCardTitle: 'Grille de Batterie et de Connectivité',
      batteryCardDesc: 'Vue d’ensemble du niveau de batterie, de l’état de la passerelle et du RSSI.',
      automationBatteryTitle: 'Automatisation : Alerte de batterie faible (< 20%)',
      automationBatteryDesc: 'Envoie une notification push lorsque les piles AAA du cylindre doivent être remplacées.',
      automationNfcTitle: 'Automatisation : Déverrouillage par badge NFC ou RFID',
      automationNfcDesc: 'Déverrouille instantanément la serrure lorsqu’un badge autorisé est scanné.',
      copyYaml: 'Copier le YAML',
      copiedYaml: 'YAML copié dans le presse-papiers !',
    },

    validator: {
      title: 'Conformité HACS et Home Assistant',
      subtitle: 'Vérification automatisée selon les critères officiels du Home Assistant Community Store.',
      scoreLabel: 'Score de Conformité',
      passAll: 'Les 6 contrôles validés avec succès (100% Prêt pour HACS)',
      checkManifest: 'Structure manifest.json & Classe IoT',
      checkManifestDesc: 'Domaine "welock" valide, version 1.3.0, codeowners @Ebenhoeh80 et "cloud_polling".',
      checkHacsJson: 'Métadonnées HACS (hacs.json)',
      checkHacsJsonDesc: 'Version minimale requise (homeassistant: 2024.1.0) et drapeau render_readme activé.',
      checkConfigFlow: 'Assistant Graphique de Configuration (config_flow.py)',
      checkConfigFlowDesc: 'ConfigFlow et OptionsFlow complets sans configuration YAML manuelle obligatoire.',
      checkTranslations: 'Localisation en 4 langues (de, en, es, fr)',
      checkTranslationsDesc: 'Fichiers de traduction complets pour les étapes de configuration, les erreurs et les capteurs.',
      checkCoordinator: 'Architecture DataUpdateCoordinator',
      checkCoordinatorDesc: 'Interrogation centralisée et gestion d’erreurs asynchrone via aiohttp.',
      checkSecurity: 'Sécurité et gestion des jetons',
      checkSecurityDesc: 'Aucun secret codé en dur, rafraîchissement des jetons et flux de réauthentification.',
      rulePassed: 'Validé',
    },

    guide: {
      title: 'Guide d’installation pas à pas',
      subtitle: 'Comment ajouter et configurer cette intégration dans votre système Home Assistant.',
      step1Title: '1. Récupérer les identifiants dans l’application WeLock',
      step1Desc: 'Ouvrez l’application mobile WeLock. Assurez-vous que votre serrure est associée à une passerelle WeLock WiFiBox. Ouvrez le menu latéral (☰) et appuyez sur l’icône "Home Assistant". Copiez votre Client ID et votre Client Secret.',
      step2Title: '2. Ajouter le dépôt personnalisé dans HACS',
      step2Desc: 'Dans Home Assistant, accédez à HACS -> Intégrations -> menu en haut à droite (trois points) -> "Dépôts personnalisés". Collez https://github.com/Ebenhoeh80/welock-aistudio et sélectionnez la catégorie "Intégration".',
      step3Title: '3. Télécharger & redémarrer Home Assistant',
      step3Desc: 'Recherchez "WeLock Smart Lock" dans HACS, cliquez sur "Télécharger", puis redémarrez Home Assistant depuis Paramètres -> Système -> Redémarrer.',
      step4Title: '4. Configurer dans Appareils et Services',
      step4Desc: 'Accédez à Paramètres -> Appareils et services -> "Ajouter une intégration", recherchez "WeLock Smart Lock" et saisissez votre Client ID et votre Client Secret.',
      importantTipTitle: 'Remarque essentielle sur la passerelle WeLock WiFiBox',
      importantTipText: 'Les cylindres WeLock communiquent localement par Bluetooth (BLE). Le pilotage à distance via Home Assistant requiert obligatoirement une passerelle WeLock WiFiBox connectée à Internet.',
    },
  },
};
