import React, { useState, useEffect, useMemo } from 'react';
import type { BlogDetail } from '../types';
import { fetchBlogBySlug, approveBlog } from '../api';
import { BlogRenderer, extractTocFromMarkdown } from './BlogRenderer';
import { TableOfContents } from './TableOfContents';
import { TableOfContentsCarousel } from './TableOfContentsCarousel';
import {
  ArrowLeft,
  Edit3,
  Check,
  X,
  Award,
  Clock,
  FileText,
  Tag,
  RefreshCw,
  Eye,
  Sliders,
  AlertTriangle,
  Layers,
} from 'lucide-react';

interface BlogViewerProps {
  slug: string;
  onBack: () => void;
  onEdit: (slug: string) => void;
}

export const BlogViewer: React.FC<BlogViewerProps> = ({ slug, onBack, onEdit }) => {
  const [blog, setBlog] = useState<BlogDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState<'preview' | 'audit'>('preview');

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

  const meta = blog?.metadata || {};
  const isApproved = blog?.approved === 'yes';
  const score = blog?.quality_score || meta.quality_score || 0;

  // Extract Table of Contents dynamically from the markdown content
  const tocItems = useMemo(() => {
    if (!blog?.markdown_content) return [];
    return extractTocFromMarkdown(blog.markdown_content);
  }, [blog?.markdown_content]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-slate-400 gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-[#4AABEF]" />
        <span>Loading publication details...</span>
      </div>
    );
  }

  if (error || !blog) {
    return (
      <div className="max-w-xl mx-auto my-12 rounded-2xl border border-rose-500/30 bg-rose-950/40 p-8 text-center text-rose-300">
        <p className="font-semibold text-lg mb-2">Error Loading Blog</p>
        <p className="text-sm text-slate-400 mb-6">{error || 'Publication not found'}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 transition"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const categoryName = blog.category || meta.category || 'Interview Prep';
  const isResumeCategory = categoryName.toLowerCase().includes('resume');
  const readTimeStr = meta.reading_time_minutes ? `${meta.reading_time_minutes} min read` : '12 min read';
  const displayDateStr = meta.date || 'Sep 4, 2026';

  // Fallback cover image or actual thumbnail
  const coverImgSrc = meta.thumbnail
    ? meta.thumbnail.startsWith('http')
      ? meta.thumbnail
      : `http://localhost:8000${meta.thumbnail.startsWith('/') ? '' : '/'}${meta.thumbnail}`
    : null;

  return (
    <div className="w-full bg-[#040D24] text-[#E0E0E0] min-h-screen font-sans">
      {/* ── STICKY TOP ADMIN ACTION BAR ── */}
      <div className="sticky top-0 z-50 bg-[#091124]/90 backdrop-blur-md border-b border-[#222A3F] px-4 sm:px-8 py-3.5 shadow-md">
        <div className="max-w-[1240px] mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="flex items-center gap-1.5 text-xs sm:text-sm font-medium text-[#8C8C9E] hover:text-white transition group"
            >
              <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
              <span>Dashboard</span>
            </button>

            <div className="h-4 w-px bg-[#222A3F] hidden sm:block" />

            {/* View Mode Toggle Switch */}
            <div className="flex items-center bg-[#040D24] border border-[#222A3F] rounded-lg p-0.5">
              <button
                type="button"
                onClick={() => setViewMode('preview')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition ${
                  viewMode === 'preview'
                    ? 'bg-[#4AABEF] text-white shadow-sm'
                    : 'text-[#8C8C9E] hover:text-white'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Fulcrum Live Preview</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('audit')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition ${
                  viewMode === 'audit'
                    ? 'bg-[#4AABEF] text-white shadow-sm'
                    : 'text-[#8C8C9E] hover:text-white'
                }`}
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Audit Inspector</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Approval Status Toggle Button */}
            <button
              onClick={handleToggleApprove}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition ${
                isApproved
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/25'
                  : 'bg-amber-500/15 border-amber-500/40 text-amber-400 hover:bg-amber-500/25'
              }`}
            >
              {isApproved ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
              <span>{isApproved ? 'Approved' : 'Mark Approved'}</span>
            </button>

            {/* Edit Blog Button */}
            <button
              onClick={() => onEdit(slug)}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#4AABEF] hover:bg-[#3b9ae0] text-white font-medium text-xs transition shadow-md cursor-pointer"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Edit Blog</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── AUDIT INSPECTOR DRAWER (Shown when audit mode is selected) ── */}
      {viewMode === 'audit' && (
        <div className="max-w-[1200px] mx-auto px-6 md:px-12 my-8">
          <div className="rounded-2xl border border-[#222A3F] bg-[#0E172D] p-6 sm:p-8 space-y-6 shadow-xl">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#222A3F] pb-4">
              <div>
                <h3 className="text-white text-lg font-bold">Pipeline Audit Metrics</h3>
                <p className="text-xs text-[#8C8C9E]">Detailed diagnostic information from LangGraph execution</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#4AABEF]/10 border border-[#4AABEF]/40 text-[#4AABEF]">
                  <Award className="w-3.5 h-3.5" />
                  <span>Quality Score: {score > 0 ? score.toFixed(1) : 'N/A'} / 10</span>
                </span>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#131F3B] border border-[#222A3F] text-[#CBD5E1]">
                  <FileText className="w-3.5 h-3.5" />
                  <span>{blog.word_count || meta.word_count || 0} words</span>
                </span>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#131F3B] border border-[#222A3F] text-[#CBD5E1]">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{readTimeStr}</span>
                </span>
              </div>
            </div>

            {/* Truncation Warnings */}
            {meta.truncation_warnings && meta.truncation_warnings.length > 0 && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 text-amber-300 text-xs space-y-1">
                <div className="flex items-center gap-2 font-bold text-sm text-amber-400">
                  <AlertTriangle className="w-4 h-4" />
                  <span>{meta.truncation_warnings.length} Sentence Truncation Warnings</span>
                </div>
                {meta.truncation_warnings.map((tw: string, i: number) => (
                  <p key={i} className="pl-6 text-slate-300">• {tw}</p>
                ))}
              </div>
            )}

            {/* SEO & Audience Meta */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-3.5 rounded-xl bg-[#091124] border border-[#222A3F]">
                <span className="text-[#8C8C9E] block mb-1">Focus Keyword</span>
                <span className="font-semibold text-white">{meta.focus_keyword || 'N/A'}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-[#091124] border border-[#222A3F]">
                <span className="text-[#8C8C9E] block mb-1">Audience Level</span>
                <span className="font-semibold text-white capitalize">{meta.audience_level || 'Intermediate'}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-[#091124] border border-[#222A3F]">
                <span className="text-[#8C8C9E] block mb-1">Blog Format</span>
                <span className="font-semibold text-white capitalize">{meta.blog_format || 'Deep Dive'}</span>
              </div>
            </div>

            {meta.meta_description && (
              <div className="p-4 rounded-xl bg-[#091124] border border-[#222A3F]">
                <span className="text-[#8C8C9E] text-xs block mb-1">Meta Description ({meta.meta_description.length} chars)</span>
                <p className="text-sm text-[#E0E0E0] italic">"{meta.meta_description}"</p>
              </div>
            )}

            {/* Tags */}
            {meta.tags && meta.tags.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <Tag className="w-3.5 h-3.5 text-[#8C8C9E]" />
                {meta.tags.map((t: string, idx: number) => (
                  <span
                    key={idx}
                    className="px-2.5 py-0.5 rounded text-xs bg-[#091124] text-[#CBD5E1] border border-[#222A3F]"
                  >
                    #{t}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── FULCRUM HERO BANNER (1:1 MATCH) ── */}
      <section className="w-full bg-[#040D24] border-b border-white/[0.07] py-8 lg:py-10 relative z-10 shadow-[0_4px_13.2px_rgba(0,0,0,0.37)]">
        <div className="max-w-[1200px] mx-auto px-6 md:px-12 w-full grid grid-cols-1 lg:grid-cols-2 items-center gap-8 lg:gap-[48px]">
          {/* Left Column: Content */}
          <div className="flex flex-col items-start gap-4 lg:py-4">
            {/* Category Badge */}
            <div>
              <span className="text-[10px] font-bold text-[#4AABEF] tracking-[2.5px] uppercase">
                {categoryName}
              </span>
            </div>

            {/* Title */}
            <div>
              <h1 className="text-white text-2xl sm:text-3xl md:text-[32px] font-medium leading-tight lg:leading-[43.2px] tracking-[-0.5px]">
                {blog.title || meta.title}
              </h1>
            </div>

            {/* Metadata Row */}
            <div className="flex items-center gap-3 text-[#8C8C9E] text-[12px] font-light leading-[19.2px]">
              <span>{readTimeStr}</span>
              <div className="w-[3px] h-[3px] rounded-full bg-[#8C8C9E]" />
              <span>{displayDateStr}</span>
            </div>

            {/* Action CTA Button */}
            <div className="mt-2">
              <button
                type="button"
                className="w-[222px] h-[44px] bg-[#4AABEF] hover:opacity-90 active:scale-95 transition-all rounded-lg text-white text-[16px] font-medium flex items-center justify-center shadow-[2px_4px_8px_rgba(0,0,0,0.04)] cursor-pointer"
              >
                {isResumeCategory ? 'Build Your Resume' : 'Practice Mock Interview'}
              </button>
            </div>
          </div>

          {/* Right Column: Hero Image Box */}
          <div className="relative w-full h-[220px] sm:h-[280px] lg:h-[340px] rounded-xl overflow-hidden bg-gradient-to-br from-[#1A222E] via-[#0F1A2E] to-[#0E161A] shadow-[0_4px_13.2px_rgba(0,0,0,0.37)] border border-white/[0.07]">
            {coverImgSrc ? (
              <img
                src={coverImgSrc}
                alt={blog.title || 'Blog Hero Thumbnail'}
                className="object-cover w-full h-full opacity-90"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center bg-gradient-to-br from-[#0F1A2E] via-[#0E172D] to-[#1E293B]">
                <div className="w-16 h-16 rounded-2xl bg-[#4AABEF]/10 border border-[#4AABEF]/30 flex items-center justify-center text-[#4AABEF] mb-3 shadow-lg">
                  <Layers className="w-8 h-8" />
                </div>
                <h3 className="text-white text-[16px] font-medium max-w-[280px] line-clamp-2">
                  {blog.title || meta.title}
                </h3>
                <span className="text-[11px] text-[#4AABEF] uppercase tracking-wider font-mono mt-1">
                  {categoryName}
                </span>
              </div>
            )}

            {/* Decorative radial gradients matching Fulcrum */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_70%,rgba(80,120,200,0.12),transparent_60%)] pointer-events-none" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_40%,rgba(56,132,232,0.16),transparent_65%)] pointer-events-none" />
          </div>
        </div>
      </section>

      {/* ── MAIN 2-COLUMN ARTICLE CONTENT & SIDEBAR ── */}
      <div className="max-w-[1200px] mx-auto px-6 md:px-12">
        <div className="py-12 flex flex-col lg:flex-row gap-12 lg:gap-16 items-start">
          {/* Left: Main Content Column */}
          <div className="flex-1 min-w-0 flex flex-col gap-10">
            <BlogRenderer content={blog.markdown_content} />
          </div>

          {/* Right: Sticky Sidebar with TOC & Carousel */}
          <aside className="w-full lg:w-[320px] flex-shrink-0 flex flex-col gap-8 lg:sticky lg:top-[90px]">
            {/* Table of Contents */}
            {tocItems.length > 0 && <TableOfContents items={tocItems} />}

            {/* Sidebar CTA Card Carousel */}
            <TableOfContentsCarousel />
          </aside>
        </div>

        {/* ── Divider ── */}
        <div className="w-full h-px bg-white/[0.07] mb-12" />

        {/* ── Related Articles Section Mockup ── */}
        <div className="mb-16">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-white text-[24px] font-bold tracking-tight">Related Articles</h3>
            <span className="text-xs text-[#4AABEF] font-medium uppercase tracking-wider">Explore More</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'What a Backend Engineer Really Requires in Placement Interviews',
                cat: 'Interview Prep',
                time: '13 min read',
                date: 'Sep 4, 2026',
              },
              {
                title: 'LeetCode vs GitHub — Which Resume Section Matters More?',
                cat: 'Resume',
                time: '12 min read',
                date: 'Sep 4, 2026',
              },
              {
                title: 'SQL vs NoSQL Schema Design Philosophy in Production',
                cat: 'Companies Test',
                time: '14 min read',
                date: 'Sep 4, 2026',
              },
            ].map((art, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-[#222A3F] bg-[#0E172D] overflow-hidden flex flex-col p-5 hover:border-[#4AABEF]/40 transition group cursor-pointer shadow-lg"
              >
                <div className="h-[120px] rounded-lg bg-gradient-to-br from-[#1E293B] to-[#0A1128] mb-4 flex items-center justify-center text-[#4AABEF]/60 group-hover:text-[#4AABEF] transition-colors">
                  <Layers className="w-8 h-8" />
                </div>
                <span className="text-[10px] font-bold text-[#4AABEF] tracking-wider uppercase mb-1.5">
                  {art.cat}
                </span>
                <h4 className="text-white font-medium text-[16px] leading-[22px] group-hover:text-[#4AABEF] transition-colors line-clamp-2 mb-3">
                  {art.title}
                </h4>
                <div className="mt-auto flex items-center justify-between text-xs text-[#8C8C9E] pt-2 border-t border-[#222A3F]/50">
                  <span>{art.time}</span>
                  <span>{art.date}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
