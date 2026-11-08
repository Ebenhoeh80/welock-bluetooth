import React, { useState } from 'react';
import { 
  BookOpen, 
  Smartphone, 
  GitFork, 
  DownloadCloud, 
  SlidersHorizontal, 
  Copy, 
  Check, 
  AlertTriangle,
  Radio,
  ExternalLink
} from 'lucide-react';
import { Language } from '../types';
import { TRANSLATIONS } from '../i18n/translations';

interface SetupGuideProps {
  currentLang: Language;
}

export const SetupGuide: React.FC<SetupGuideProps> = ({ currentLang }) => {
  const t = TRANSLATIONS[currentLang];
  const [copiedUrl, setCopiedUrl] = useState(false);

  const handleCopyRepo = () => {
    navigator.clipboard.writeText('https://github.com/Ebenhoeh80/welock');
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const steps = [
    {
      num: 1,
      icon: <Smartphone className="w-5 h-5 text-cyan-400" />,
      title: t.guide.step1Title,
      desc: t.guide.step1Desc,
      tips: [
        'WeLock Mobile App -> Menü (☰) -> Home Assistant',
        'Erzeugt: Client ID & Client Secret',
      ],
    },
    {
      num: 2,
      icon: <GitFork className="w-5 h-5 text-blue-400" />,
      title: t.guide.step2Title,
      desc: t.guide.step2Desc,
      repoAction: true,
    },
    {
      num: 3,
      icon: <DownloadCloud className="w-5 h-5 text-emerald-400" />,
      title: t.guide.step3Title,
      desc: t.guide.step3Desc,
      tips: [
        'HACS -> Integrationen -> WeLock Smart Lock -> Herunterladen',
        'Home Assistant neu starten (Einstellungen -> System -> Neustart)',
      ],
    },
    {
      num: 4,
      icon: <SlidersHorizontal className="w-5 h-5 text-amber-400" />,
      title: t.guide.step4Title,
      desc: t.guide.step4Desc,
      tips: [
        'Einstellungen -> Geräte & Dienste -> Integration hinzufügen',
        'Wählen Sie "WeLock Smart Lock" und geben Sie Ihre Daten ein',
      ],
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-cyan-400" />
          <span>{t.guide.title}</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          {t.guide.subtitle}
        </p>
      </div>

      {/* Crucial Gateway Hardware Notice */}
      <div className="bg-gradient-to-r from-amber-950/40 via-slate-900 to-amber-950/20 border border-amber-500/30 rounded-xl p-5 shadow-lg">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
            <Radio className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-amber-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>{t.guide.importantTipTitle}</span>
            </h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {t.guide.importantTipText}
            </p>
          </div>
        </div>
      </div>

      {/* Step Cards */}
      <div className="space-y-4">
        {steps.map((step) => (
          <div
            key={step.num}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 transition hover:border-slate-700 space-y-3"
          >
            <div className="flex items-start gap-4">
              <div className="w-9 h-9 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center font-bold text-cyan-400 text-sm shrink-0 shadow-inner">
                {step.num}
              </div>

              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  {step.icon}
                  <h3 className="text-sm sm:text-base font-bold text-white">
                    {step.title}
                  </h3>
                </div>

                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  {step.desc}
                </p>

                {step.repoAction && (
                  <div className="pt-2 flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 px-3 py-2 rounded-lg font-mono text-xs text-cyan-300">
                      <span>https://github.com/Ebenhoeh80/welock</span>
                    </div>
                    <button
                      onClick={handleCopyRepo}
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition cursor-pointer"
                    >
                      {copiedUrl ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedUrl ? t.copied : t.copyRepoUrl}</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
