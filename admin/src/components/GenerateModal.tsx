import React, { useState } from 'react';
import { Sparkles, X, Loader2 } from 'lucide-react';
import { generateBlog } from '../api';

interface GenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const GenerateModal: React.FC<GenerateModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [topic, setTopic] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await generateBlog(category || undefined, topic || undefined);
      setLoading(false);
      onSuccess();
      onClose();
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'Failed to trigger blog generation');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
          <div className="flex items-center gap-2 text-cyan-400">
            <Sparkles className="w-5 h-5" />
            <h3 className="text-lg font-bold text-slate-100">Generate New AI Blog</h3>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Topic / Blog Title (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Modern System Design Best Practices in 2026"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none"
            />
            <p className="text-xs text-slate-500 mt-1">Leave blank to auto-generate a trending topic.</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Category (Optional)
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              <option value="">Auto-Select Category</option>
              <option value="Developer Technology">Developer Technology</option>
              <option value="Comparison Articles">Comparison Articles</option>
              <option value="Job Role and Career Trends">Job Role and Career Trends</option>
              <option value="System Architecture">System Architecture</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-800 pt-4 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 rounded-lg bg-cyan-600 px-5 py-2 text-sm font-semibold text-white shadow-lg hover:bg-cyan-500 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Initiating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Start Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
