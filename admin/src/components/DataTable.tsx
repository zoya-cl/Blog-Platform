import React from 'react';
import type { DataTableProps } from '../types';
import { Table } from 'lucide-react';

export const DataTable: React.FC<DataTableProps> = ({ headers, rows }) => {
  return (
    <div className="my-8 rounded-xl border border-slate-800 bg-slate-900/90 overflow-hidden shadow-xl">
      <div className="flex items-center gap-2 p-4 bg-slate-950 border-b border-slate-800">
        <Table className="w-5 h-5 text-indigo-400" />
        <span className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Summary Table</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/80 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="px-6 py-3.5">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-slate-800/40 transition">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className={`px-6 py-4 ${cIdx === 0 ? 'font-medium text-slate-200' : 'text-slate-300'}`}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
