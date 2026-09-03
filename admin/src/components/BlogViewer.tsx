import React, { useState, useEffect } from 'react';
import type { BlogDetail } from '../types';
import { fetchBlogBySlug, approveBlog } from '../api';
import { BlogRenderer } from './BlogRenderer';
import { ArrowLeft, Edit3, Check, X, Award, Clock, FileText, Calendar, Tag, RefreshCw } from 'lucide-react';

interface BlogViewerProps {
  slug: string;
  onBack: () => void;
  onEdit: (slug: string) => void;
}

export const BlogViewer: React.FC<BlogViewerProps> = ({ slug, onBack, onEdit }) => {
  const [blog, setBlog] = useState<BlogDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadBlog = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchBlogBySlug(slug);
      setBlog(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load blog detail');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBlog();
  }, [slug]);

  const handleToggleApprove = async () => {
    if (!blog) return;
    const newStatus = blog.approved === 'yes' ? 'no' : 'yes';
    try {
      await approveBlog(slug, newStatus as 'yes' | 'no');
      setBlog({ ...blog, approved: newStatus });
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-slate-400 gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span>Loading publication details...</span>
      </div>
    );
  }

  if (error || !blog) {
    return (
      <div className="rounded-2xl border border-rose-500/30 bg-rose-950/40 p-8 text-center text-rose-300">
        <p className="font-semibold text-lg mb-2">Error Loading Blog</p>
        <p className="text-sm text-slate-400 mb-6">{error || 'Publication not found'}</p>
        <button onClick={onBack} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const meta = blog.metadata || {};
  const isApproved = blog.approved === 'yes';
  const score = blog.quality_score || meta.quality_score || 0;

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      {/* Top Action Bar */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-5">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-white transition group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={handleToggleApprove}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold border transition ${
              isApproved
                ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/20'
                : 'bg-amber-500/10 border-amber-500/40 text-amber-400 hover:bg-amber-500/20'
            }`}
          >
            {isApproved ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
            <span>{isApproved ? 'Approved' : 'Mark Approved'}</span>
          </button>

          <button
            onClick={() => onEdit(slug)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-lg shadow-indigo-900/30"
          >
            <Edit3 className="w-4 h-4" />
            <span>Edit Blog</span>
          </button>
        </div>
      </div>

      {/* Header Info Block */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            {blog.category || meta.category || 'General'}
          </span>

          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-900 border border-slate-800 text-purple-400">
            <Award className="w-3.5 h-3.5" />
            <span>Score: {score > 0 ? score.toFixed(1) : 'N/A'} / 10</span>
          </span>

          {meta.date && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-900 border border-slate-800 text-slate-400">
              <Calendar className="w-3.5 h-3.5" />
              <span>{meta.date}</span>
            </span>
          )}

          {meta.reading_time_minutes && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-900 border border-slate-800 text-slate-400">
              <Clock className="w-3.5 h-3.5" />
              <span>{meta.reading_time_minutes} min read</span>
            </span>
          )}

          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-900 border border-slate-800 text-slate-400">
            <FileText className="w-3.5 h-3.5" />
            <span>{blog.word_count || meta.word_count || 0} words</span>
          </span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight leading-tight">
          {blog.title || meta.title}
        </h1>

        {meta.meta_description && (
          <p className="text-base text-slate-400 leading-relaxed italic border-l-2 border-slate-700 pl-4 py-1">
            "{meta.meta_description}"
          </p>
        )}

        {meta.tags && meta.tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-2">
            <Tag className="w-3.5 h-3.5 text-slate-500" />
            {meta.tags.map((t, idx) => (
              <span key={idx} className="px-2.5 py-0.5 rounded text-xs bg-slate-900 text-slate-400 border border-slate-800">
                #{t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Hero Thumbnail Banner */}
      {meta.thumbnail && (
        <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-2xl max-h-[440px] bg-slate-900/80 relative group">
          <img
            src={meta.thumbnail.startsWith('http') ? meta.thumbnail : `http://localhost:8000${meta.thumbnail.startsWith('/') ? '' : '/'}${meta.thumbnail}`}
            alt={blog.title || 'Blog Hero Thumbnail'}
            className="w-full h-full object-cover max-h-[440px]"
          />
          <div className="absolute top-4 right-4 px-3 py-1 rounded-full text-[11px] font-mono tracking-wider uppercase bg-slate-950/80 text-cyan-400 border border-cyan-800/60 backdrop-blur-md">
            Hero Visual
          </div>
        </div>
      )}

      {/* Rendered Publication Container */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 sm:p-10 shadow-2xl">
        <BlogRenderer content={blog.markdown_content} />
      </div>
    </div>
  );
};
