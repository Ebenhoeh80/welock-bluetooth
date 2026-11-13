import React, { useState } from 'react';
import { 
  Download, 
  GitFork, 
  Globe, 
  Check, 
  Copy, 
  ExternalLink,
  ShieldCheck,
  FolderTree,
  Sliders,
  Code2,
  BookOpen
} from 'lucide-react';
import { Language } from '../types';
import { TRANSLATIONS } from '../i18n/translations';
import { downloadIntegrationZip } from '../utils/zipExporter';

interface HeaderProps {
  currentLang: Language;
  onSelectLang: (lang: Language) => void;
  activeTab: 'explorer' | 'simulator' | 'yaml' | 'validator' | 'guide';
  onSelectTab: (tab: 'explorer' | 'simulator' | 'yaml' | 'validator' | 'guide') => void;
}

const LANGUAGE_FLAGS: Record<Language, { flag: string; label: string }> = {
  de: { flag: '🇩🇪', label: 'Deutsch' },
  en: { flag: '🇬🇧', label: 'English' },
  es: { flag: '🇪🇸', label: 'Español' },
  fr: { flag: '🇫🇷', label: 'Français' },
};

export const Header: React.FC<HeaderProps> = ({
  currentLang,
  onSelectLang,
  activeTab,
  onSelectTab,
}) => {
  const t = TRANSLATIONS[currentLang];
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleCopyRepo = () => {
    navigator.clipboard.writeText('https://github.com/Ebenhoeh80/welock-bluetooth');
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await downloadIntegrationZip();
    } finally {
      setTimeout(() => setIsDownloading(false), 800);
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-40">
      {/* Top Notification Bar */}
      <div className="bg-gradient-to-r from-cyan-950 via-slate-900 to-indigo-950 border-b border-cyan-800/40 px-4 py-2 text-xs flex flex-wrap items-center justify-between gap-2 text-cyan-200">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-semibold text-white">{t.forkOf}</span>
          <span className="text-slate-400">•</span>
          <span className="text-cyan-300 font-mono text-[11px] bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-700/50">
            v2.0.0 (HACS Ready)
          </span>
        </div>
        <div className="flex items-center gap-3 text-slate-300">
          <span className="hidden sm:inline text-xs text-slate-400">{t.fourLanguagesReady}</span>
          <button
            onClick={handleCopyRepo}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-cyan-300 hover:text-white transition text-xs font-mono border border-slate-700/70"
            title="https://github.com/Ebenhoeh80/welock-bluetooth"
          >
            {copiedUrl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedUrl ? t.copied : 'github.com/Ebenhoeh80/welock-bluetooth'}</span>
          </button>
        </div>
      </div>

      {/* Main Header Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 text-white font-bold ring-1 ring-cyan-400/30">
              <span className="text-xl">🔐</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-white">
                  WeLock <span className="text-cyan-400 font-medium">Smart Lock</span>
                </h1>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  <GitFork className="w-3 h-3" /> HACS
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 max-w-xl line-clamp-1">
                {t.appSubtitle}
              </p>
            </div>
          </div>

          {/* Right Controls: Language Selector & Primary Download */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Language Switcher */}
            <div className="flex items-center bg-slate-800/90 rounded-lg p-1 border border-slate-700">
              <Globe className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1" />
              {(['de', 'en', 'es', 'fr'] as Language[]).map((lang) => {
                const isActive = currentLang === lang;
                return (
                  <button
                    key={lang}
                    onClick={() => onSelectLang(lang)}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition ${
                      isActive
                        ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                        : 'text-slate-300 hover:text-white hover:bg-slate-700/60'
                    }`}
                    title={LANGUAGE_FLAGS[lang].label}
                  >
                    <span>{LANGUAGE_FLAGS[lang].flag}</span>
                    <span className="uppercase text-[11px] tracking-wider">{lang}</span>
                  </button>
                );
              })}
            </div>

            {/* Direct ZIP Download */}
            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-semibold text-xs sm:text-sm shadow-md shadow-cyan-500/20 active:scale-95 transition cursor-pointer"
            >
              <Download className={`w-4 h-4 ${isDownloading ? 'animate-bounce' : ''}`} />
              <span>{isDownloading ? 'Generiere ZIP...' : t.downloadZip}</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1.5 sm:gap-2 mt-4 pt-3 border-t border-slate-800/80 overflow-x-auto scrollbar-none text-xs sm:text-sm">
          <button
            onClick={() => onSelectTab('explorer')}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium whitespace-nowrap transition ${
              activeTab === 'explorer'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <FolderTree className="w-4 h-4" />
            <span>{t.tabs.explorer}</span>
          </button>

          <button
            onClick={() => onSelectTab('simulator')}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium whitespace-nowrap transition ${
              activeTab === 'simulator'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>{t.tabs.simulator}</span>
          </button>

          <button
            onClick={() => onSelectTab('yaml')}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium whitespace-nowrap transition ${
              activeTab === 'yaml'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <Code2 className="w-4 h-4" />
            <span>{t.tabs.yaml}</span>
          </button>

          <button
            onClick={() => onSelectTab('validator')}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium whitespace-nowrap transition ${
              activeTab === 'validator'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{t.tabs.validator}</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
          </button>

          <button
            onClick={() => onSelectTab('guide')}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium whitespace-nowrap transition ${
              activeTab === 'guide'
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>{t.tabs.guide}</span>
          </button>
        </nav>
      </div>
    </header>
  );
};
