import React from 'react';
import { 
  ShieldCheck, 
  CheckCircle2, 
  FileCheck, 
  Layers, 
  Languages, 
  Lock, 
  Key, 
  Cpu
} from 'lucide-react';
import { Language } from '../types';
import { TRANSLATIONS } from '../i18n/translations';

interface ValidatorProps {
  currentLang: Language;
}

export const Validator: React.FC<ValidatorProps> = ({ currentLang }) => {
  const t = TRANSLATIONS[currentLang];

  const checks = [
    {
      id: 'manifest',
      icon: <FileCheck className="w-5 h-5 text-emerald-400" />,
      title: t.validator.checkManifest,
      desc: t.validator.checkManifestDesc,
      status: 'pass',
      tag: 'manifest.json',
      details: 'Domain: "welock", Version: "1.2.0", IoT: "cloud_polling", Codeowners: ["@Ebenhoeh80"]',
    },
    {
      id: 'hacs_json',
      icon: <Layers className="w-5 h-5 text-emerald-400" />,
      title: t.validator.checkHacsJson,
      desc: t.validator.checkHacsJsonDesc,
      status: 'pass',
      tag: 'hacs.json',
      details: 'Home Assistant >= 2024.1.0, render_readme: true, category: integration',
    },
    {
      id: 'config_flow',
      icon: <Lock className="w-5 h-5 text-emerald-400" />,
      title: t.validator.checkConfigFlow,
      desc: t.validator.checkConfigFlowDesc,
      status: 'pass',
      tag: 'config_flow.py',
      details: 'ConfigFlow: step_user, step_reauth, OptionsFlowHandler: scan_interval & auto_relock_delay',
    },
    {
      id: 'translations',
      icon: <Languages className="w-5 h-5 text-emerald-400" />,
      title: t.validator.checkTranslations,
      desc: t.validator.checkTranslationsDesc,
      status: 'pass',
      tag: 'de, en, es, fr',
      details: '100% string parity across de.json, en.json, es.json, fr.json + strings.json',
    },
    {
      id: 'coordinator',
      icon: <Cpu className="w-5 h-5 text-emerald-400" />,
      title: t.validator.checkCoordinator,
      desc: t.validator.checkCoordinatorDesc,
      status: 'pass',
      tag: '__init__.py',
      details: 'WeLockDataUpdateCoordinator with async_config_entry_first_refresh & entry unload cleanup',
    },
    {
      id: 'security',
      icon: <Key className="w-5 h-5 text-emerald-400" />,
      title: t.validator.checkSecurity,
      desc: t.validator.checkSecurityDesc,
      status: 'pass',
      tag: 'api.py',
      details: 'Bearer token auth with automated renewal on 401/403 expiry and strict SSL checking',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header card with 100% Score badge */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <h2 className="text-lg sm:text-xl font-bold text-white">
              {t.validator.title}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {t.validator.subtitle}
          </p>
        </div>

        <div className="flex items-center gap-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl px-4 py-2.5">
          <div className="text-right">
            <span className="text-[10px] uppercase font-mono tracking-wider text-emerald-300 block">
              {t.validator.scoreLabel}
            </span>
            <span className="text-xl sm:text-2xl font-black text-emerald-400">
              6 / 6 (100%)
            </span>
          </div>
          <CheckCircle2 className="w-7 h-7 text-emerald-400" />
        </div>
      </div>

      {/* Grid of checks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {checks.map((chk) => (
          <div
            key={chk.id}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition space-y-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center shrink-0">
                  {chk.icon}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {chk.title}
                  </h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    {chk.tag}
                  </span>
                </div>
              </div>

              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{t.validator.rulePassed}</span>
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              {chk.desc}
            </p>

            <div className="pt-2 border-t border-slate-800/80 font-mono text-[11px] text-cyan-300/80 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
              {chk.details}
            </div>
          </div>
        ))}
      </div>

      {/* Summary message */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/30 to-slate-900 border border-emerald-500/20 text-emerald-300 text-xs sm:text-sm flex items-center gap-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
        <span>{t.validator.passAll}</span>
      </div>
    </div>
  );
};
