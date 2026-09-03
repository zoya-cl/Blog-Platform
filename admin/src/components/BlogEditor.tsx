import React, { useState, useEffect } from 'react';
import { fetchBlogBySlug, updateBlog } from '../api';
import { BlogRenderer } from './BlogRenderer';
import { ArrowLeft, Save, Loader2, Eye, Edit3, Settings } from 'lucide-react';

interface BlogEditorProps {
  slug: string;
  onBack: () => void;
  onSaved: () => void;
}

export const BlogEditor: React.FC<BlogEditorProps> = ({ slug, onBack, onSaved }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'split' | 'edit' | 'preview'>('split');

  // Form State
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [metaDescription, setMetaDescription] = useState('');
  const [focusKeyword, setFocusKeyword] = useState('');
  const [tagsStr, setTagsStr] = useState('');
  const [markdownContent, setMarkdownContent] = useState('');

  const loadBlog = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchBlogBySlug(slug);
      setTitle(data.title || data.metadata?.title || '');
      setCategory(data.category || data.metadata?.category || '');
      setMetaDescription(data.metadata?.meta_description || '');
      setFocusKeyword(data.metadata?.focus_keyword || '');
      setTagsStr((data.metadata?.tags || []).join(', '));
      setMarkdownContent(data.markdown_content || '');
    } catch (err: any) {
      setError(err.message || 'Failed to load blog for editing');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBlog();
  }, [slug]);

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const tags = tagsStr.split(',').map(t => t.trim()).filter(Boolean);
      await updateBlog(slug, {
        title,
        category,
        meta_description: metaDescription,
        focus_keyword: focusKeyword,
        tags,
        markdown_content: markdownContent,
      });
      setSaving(false);
      onSaved();
    } catch (err: any) {
      setSaving(false);
      setError(err.message || 'Failed to save blog changes');
    }
  };

  const wordCount = markdownContent ? markdownContent.split(/\s+/).filter(Boolean).length : 0;

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-slate-400 gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
        <span>Loading editor environment...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Action Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-white transition">
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>
          <div className="h-4 w-px bg-slate-800" />
          <h2 className="text-xl font-bold text-slate-100 truncate max-w-lg">{title || slug}</h2>
          <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-slate-900 text-cyan-400 border border-slate-800">
            {wordCount} words
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Mobile view tabs */}
          <div className="flex lg:hidden bg-slate-900 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('edit')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${activeTab === 'edit' ? 'bg-cyan-600 text-white' : 'text-slate-400'}`}
            >
              Edit
            </button>
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${activeTab === 'preview' ? 'bg-cyan-600 text-white' : 'text-slate-400'}`}
            >
              Preview
            </button>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-900/30 transition disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span>Save Changes</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/40 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Metadata Panel */}
      <details className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg group">
        <summary className="cursor-pointer font-semibold text-sm text-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-cyan-400">
            <Settings className="w-4 h-4" />
            <span>Edit Blog Metadata Sidecar</span>
          </div>
          <span className="text-xs text-slate-500 group-open:rotate-180 transition-transform">▼</span>
        </summary>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 mt-4 border-t border-slate-800 text-xs">
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Blog Title</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-slate-200 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-semibold mb-1">Category</label>
            <input
              type="text"
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-slate-200 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-semibold mb-1">Focus Keyword</label>
            <input
              type="text"
              value={focusKeyword}
              onChange={e => setFocusKeyword(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-slate-200 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-semibold mb-1">Tags (Comma-separated)</label>
            <input
              type="text"
              value={tagsStr}
              onChange={e => setTagsStr(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-slate-200 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-slate-400 font-semibold mb-1">Meta Description</label>
            <textarea
              rows={2}
              value={metaDescription}
              onChange={e => setMetaDescription(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-slate-200 focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </div>
      </details>

      {/* Editor Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-[600px]">
        {/* Left Pane: Markdown Textarea */}
        <div className={`flex flex-col rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden shadow-xl ${activeTab === 'preview' ? 'hidden lg:flex' : 'flex'}`}>
          <div className="flex items-center gap-2 px-4 py-3 bg-slate-950 border-b border-slate-800 text-xs font-semibold text-slate-300">
            <Edit3 className="w-4 h-4 text-cyan-400" />
            <span>Markdown Source Editor</span>
          </div>
          <textarea
            value={markdownContent}
            onChange={e => setMarkdownContent(e.target.value)}
            className="w-full flex-1 p-5 bg-slate-950 font-mono text-sm text-cyan-100 focus:outline-none resize-none leading-relaxed"
            placeholder="Write markdown here..."
          />
        </div>

        {/* Right Pane: Live Rendered Preview */}
        <div className={`flex flex-col rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden shadow-xl ${activeTab === 'edit' ? 'hidden lg:flex' : 'flex'}`}>
          <div className="flex items-center gap-2 px-4 py-3 bg-slate-950 border-b border-slate-800 text-xs font-semibold text-slate-300">
            <Eye className="w-4 h-4 text-emerald-400" />
            <span>Live Article Preview</span>
          </div>
          <div className="flex-1 p-6 overflow-y-auto max-h-[700px]">
            <BlogRenderer content={markdownContent} />
          </div>
        </div>
      </div>
    </div>
  );
};
