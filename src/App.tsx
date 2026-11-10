/**
 * @license
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from 'react';
import { Language } from './types';
import { Header } from './components/Header';
import { FileExplorer } from './components/FileExplorer';
import { HaSimulator } from './components/HaSimulator';
import { YamlGenerator } from './components/YamlGenerator';
import { Validator } from './components/Validator';
import { SetupGuide } from './components/SetupGuide';
import { TRANSLATIONS } from './i18n/translations';
import { GitFork, Heart, Download } from 'lucide-react';
import { downloadIntegrationZip } from './utils/zipExporter';

export default function App() {
  const [currentLang, setCurrentLang] = useState<Language>('de');
  const [activeTab, setActiveTab] = useState<'explorer' | 'simulator' | 'yaml' | 'validator' | 'guide'>('explorer');

  const t = TRANSLATIONS[currentLang];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top App Header with Language Switcher and Primary Download */}
      <Header
        currentLang={currentLang}
        onSelectLang={setCurrentLang}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeTab === 'explorer' && <FileExplorer currentLang={currentLang} />}
        {activeTab === 'simulator' && <HaSimulator currentLang={currentLang} />}
        {activeTab === 'yaml' && <YamlGenerator currentLang={currentLang} />}
        {activeTab === 'validator' && <Validator currentLang={currentLang} />}
        {activeTab === 'guide' && <SetupGuide currentLang={currentLang} />}
      </main>

      {/* Global Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/60 mt-12 py-8 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white">WeLock Home Assistant HACS Integration</span>
            <span>•</span>
            <span className="text-slate-500">v1.2.0</span>
            <span>•</span>
            <span className="text-cyan-400 font-mono">@Ebenhoeh80</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <span>DE • EN • ES • FR</span>
            <button
              onClick={downloadIntegrationZip}
              className="inline-flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 font-medium transition cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{t.downloadZip}</span>
            </button>
            <a
              href="https://github.com/Ebenhoeh80/welock-aistudio"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white transition flex items-center gap-1"
            >
              <GitFork className="w-3.5 h-3.5" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
