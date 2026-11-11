import React, { useState } from 'react';
import { 
  FileCode, 
  FileText, 
  Copy, 
  Check, 
  Search, 
  Folder, 
  Languages, 
  Download,
  Info
} from 'lucide-react';
import { Language, RepoFile } from '../types';
import { REPO_FILES } from '../data/repoFiles';
import { TRANSLATIONS } from '../i18n/translations';
import { downloadIntegrationZip } from '../utils/zipExporter';

interface FileExplorerProps {
  currentLang: Language;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({ currentLang }) => {
  const t = TRANSLATIONS[currentLang];
  const [selectedFile, setSelectedFile] = useState<RepoFile>(REPO_FILES[0]);
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [showMatrix, setShowMatrix] = useState(false);

  const filteredFiles = REPO_FILES.filter(
    (f) =>
      f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.description[currentLang].toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getFileBadgeColor = (category: RepoFile['category']) => {
    switch (category) {
      case 'python':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'json':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'markdown':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'shell':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  // Sample translation strings for the 4-language comparison matrix
  const sampleMatrix = [
    {
      key: 'config.step.user.title',
      de: 'WeLock Smart Lock Einrichtung',
      en: 'WeLock Smart Lock Setup',
      es: 'Configuración de WeLock Smart Lock',
      fr: 'Configuration de WeLock Smart Lock',
    },
    {
      key: 'config.step.user.description',
      de: 'Geben Sie Ihre WeLock API-Zugangsdaten ein, die Sie in der WeLock Mobile-App finden (Seitenmenü -> Home Assistant).',
      en: 'Enter your WeLock API credentials obtained from the WeLock mobile application (Sidebar Menu -> Home Assistant).',
      es: 'Introduce tus credenciales de API obtenidas en la aplicación móvil de WeLock (Menú lateral -> Home Assistant).',
      fr: 'Entrez vos identifiants d’API WeLock obtenus dans l’application mobile WeLock (Menu latéral -> Home Assistant).',
    },
    {
      key: 'config.error.invalid_auth',
      de: 'Ungültige Client-ID oder ungültiges Client-Secret. Bitte überprüfen Sie die Eingabe in der WeLock-App.',
      en: 'Invalid Client ID or Client Secret. Please verify in the WeLock mobile app.',
      es: 'Client ID o Client Secret no válidos. Comprueba los datos en la aplicación WeLock.',
      fr: 'Client ID ou Client Secret invalide. Veuillez vérifier dans l’application WeLock.',
    },
    {
      key: 'config.error.cannot_connect',
      de: 'Verbindung zur WeLock Cloud (api.welockglobal.com) fehlgeschlagen. Bitte prüfen Sie Ihre Netzwerkverbindung.',
      en: 'Failed to connect to WeLock Cloud (api.welockglobal.com). Please verify internet connection.',
      es: 'No se pudo conectar a la nube de WeLock (api.welockglobal.com). Comprueba tu conexión de red.',
      fr: 'Impossible de se connecter au Cloud WeLock (api.welockglobal.com). Veuillez vérifier votre connexion réseau.',
    },
    {
      key: 'entity.sensor.battery.name',
      de: 'Batterie',
      en: 'Battery',
      es: 'Batería',
      fr: 'Batterie',
    },
    {
      key: 'entity.sensor.last_unlock_type.name',
      de: 'Letzte Entriegelungsmethode',
      en: 'Last Unlock Method',
      es: 'Último método de desbloqueo',
      fr: 'Dernière méthode de déverrouillage',
    },
    {
      key: 'entity.binary_sensor.connectivity.name',
      de: 'Schloss-Verbindung',
      en: 'Lock Status',
      es: 'Estado de la cerradura',
      fr: 'État de la serrure',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner / Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
            <Folder className="w-5 h-5 text-cyan-400" />
            <span>{t.explorer.title}</span>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {t.explorer.subtitle}
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => setShowMatrix(!showMatrix)}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition cursor-pointer ${
              showMatrix
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
            }`}
          >
            <Languages className="w-4 h-4 text-indigo-400" />
            <span>{t.explorer.translationComparisonTitle}</span>
          </button>

          <button
            onClick={downloadIntegrationZip}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs sm:text-sm transition cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>.ZIP</span>
          </button>
        </div>
      </div>

      {/* Multilingual Translation Matrix View (if toggled) */}
      {showMatrix && (
        <div className="bg-slate-900 border border-indigo-500/30 rounded-xl p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Languages className="w-5 h-5 text-indigo-400" />
              <div>
                <h3 className="text-sm sm:text-base font-bold text-white">
                  {t.explorer.translationComparisonTitle}
                </h3>
                <p className="text-xs text-slate-400">
                  {t.explorer.translationComparisonSub}
                </p>
              </div>
            </div>
            <span className="text-xs font-mono px-2 py-1 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/50">
              de.json • en.json • es.json • fr.json
            </span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">{t.explorer.keyLabel}</th>
                  <th className="py-2.5 px-3">🇩🇪 Deutsch (de)</th>
                  <th className="py-2.5 px-3">🇬🇧 English (en)</th>
                  <th className="py-2.5 px-3">🇪🇸 Español (es)</th>
                  <th className="py-2.5 px-3">🇫🇷 Français (fr)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {sampleMatrix.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition">
                    <td className="py-2 px-3 font-mono text-[11px] text-cyan-300 whitespace-nowrap">
                      {item.key}
                    </td>
                    <td className="py-2 px-3 text-slate-200">{item.de}</td>
                    <td className="py-2 px-3 text-slate-300">{item.en}</td>
                    <td className="py-2 px-3 text-slate-300">{item.es}</td>
                    <td className="py-2 px-3 text-slate-300">{item.fr}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Main Split: File Tree & Code Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: File Tree (4 Cols) */}
        <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col h-[650px]">
          {/* Search Box */}
          <div className="relative mb-3">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder={t.explorer.filterPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 py-1 border-b border-slate-800/80 mb-2">
            <span>{t.explorer.fileTree}</span>
            <span className="text-cyan-400 font-mono">{filteredFiles.length} {filteredFiles.length === 1 ? 'file' : 'files'}</span>
          </div>

          {/* List of files */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
            {filteredFiles.map((file) => {
              const isSelected = selectedFile.path === file.path;
              return (
                <button
                  key={file.path}
                  onClick={() => setSelectedFile(file)}
                  className={`w-full text-left p-2.5 rounded-lg transition group flex flex-col gap-1 cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-500/10 border border-cyan-500/40 text-cyan-300'
                      : 'hover:bg-slate-800/60 border border-transparent text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="font-mono text-xs font-semibold flex items-center gap-1.5 truncate">
                      {file.category === 'python' ? (
                        <FileCode className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      ) : (
                        <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      )}
                      <span className="truncate">{file.name}</span>
                    </span>
                    <span
                      className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-mono border ${getFileBadgeColor(
                        file.category
                      )}`}
                    >
                      {file.category}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-1 group-hover:text-slate-300">
                    {file.description[currentLang]}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Status footer */}
          <div className="mt-3 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
            <span className="text-emerald-400 font-medium">✓ {t.explorer.allFilesValid}</span>
            <span className="font-mono text-slate-500 text-[10px]">v2.0.0</span>
          </div>
        </div>

        {/* Right: Code Viewer (8 Cols) */}
        <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[650px]">
          {/* Header */}
          <div className="bg-slate-950/80 border-b border-slate-800 px-4 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 overflow-hidden">
              <span className="font-mono text-xs sm:text-sm font-bold text-white truncate">
                {selectedFile.path}
              </span>
              <span className="hidden sm:inline-block text-[10px] text-slate-500 font-mono">
                ({selectedFile.content.split('\n').length} lines)
              </span>
            </div>

            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 transition cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">{t.explorer.copiedFile}</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>{t.explorer.copyFile}</span>
                </>
              )}
            </button>
          </div>

          {/* Description banner */}
          <div className="bg-slate-900/90 border-b border-slate-800/80 px-4 py-2 text-xs text-slate-400 flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span>{selectedFile.description[currentLang]}</span>
          </div>

          {/* Code Body */}
          <div className="flex-1 overflow-auto p-4 font-mono text-xs text-slate-200 bg-slate-950 select-text leading-relaxed">
            <pre className="whitespace-pre">
              {selectedFile.content.split('\n').map((line, idx) => (
                <div key={idx} className="table-row">
                  <span className="table-cell pr-4 text-right select-none text-slate-600 text-[11px] w-10">
                    {idx + 1}
                  </span>
                  <span className="table-cell">{line || ' '}</span>
                </div>
              ))}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
