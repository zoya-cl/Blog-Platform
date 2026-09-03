import React from 'react';
import type { ComparisonWidgetProps } from '../types';
import { Columns } from 'lucide-react';

export const ComparisonWidget: React.FC<ComparisonWidgetProps> = ({ left_title, right_title, metrics }) => {
  return (
    <div className="my-8 rounded-xl border border-cyan-500/20 bg-slate-900/80 p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-4 mb-6">
        <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
          <Columns className="w-5 h-5" />
        </div>
        <h4 className="text-lg font-semibold text-slate-100">Architecture Comparison</h4>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className="rounded-lg bg-gradient-to-r from-blue-600/20 to-cyan-600/20 p-4 border border-blue-500/30 text-center">
          <span className="text-xs uppercase tracking-wider text-blue-400 font-bold">Option A</span>
          <h5 className="text-xl font-bold text-slate-100 mt-1">{left_title}</h5>
        </div>
        <div className="rounded-lg bg-gradient-to-r from-emerald-600/20 to-teal-600/20 p-4 border border-emerald-500/30 text-center">
          <span className="text-xs uppercase tracking-wider text-emerald-400 font-bold">Option B</span>
          <h5 className="text-xl font-bold text-slate-100 mt-1">{right_title}</h5>
        </div>
      </div>

      <div className="space-y-3">
        {metrics.map((metric, idx) => (
          <div key={idx} className="rounded-lg bg-slate-950/60 p-4 border border-slate-800/80 hover:border-slate-700 transition">
            <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">{metric.name}</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="text-sm font-medium text-blue-300 bg-blue-950/40 p-2.5 rounded border border-blue-900/40">
                {metric.left}
              </div>
              <div className="text-sm font-medium text-emerald-300 bg-emerald-950/40 p-2.5 rounded border border-emerald-900/40">
                {metric.right}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
