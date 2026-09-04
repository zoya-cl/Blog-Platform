import React, { useState, useEffect } from 'react';
import type { BlogSummary } from '../types';
import { fetchBlogs, approveBlog, deleteBlog } from '../api';
import { FileText, CheckCircle2, Clock, Award, Search, Filter, Plus, Eye, Edit3, Trash2, Check, X, RefreshCw, Calendar } from 'lucide-react';

interface DashboardProps {
  onViewBlog: (slug: string) => void;
  onEditBlog: (slug: string) => void;
  onOpenGenerate: () => void;
}


const formatTimestamp = (ts?: string) => {
  if (!ts) return 'N/A';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    const hasTime = ts.includes('T') || ts.includes(':');
    if (hasTime) {
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    }
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return ts;
  }
};

export const Dashboard: React.FC<DashboardProps> = ({ onViewBlog, onEditBlog, onOpenGenerate }) => {
  const [blogs, setBlogs] = useState<BlogSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [approvedFilter, setApprovedFilter] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchBlogs(categoryFilter || undefined, undefined, approvedFilter || undefined);
      setBlogs(data.blogs);
    } catch (err: any) {
      setError(err.message || 'Failed to load blogs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [categoryFilter, approvedFilter]);

  const handleToggleApprove = async (slug: string, currentStatus: string) => {
    const newStatus = currentStatus === 'yes' ? 'no' : 'yes';
    try {
      await approveBlog(slug, newStatus as 'yes' | 'no');
      setBlogs(prev => prev.map(b => (b.slug === slug || b.output_filename?.includes(slug)) ? { ...b, approved: newStatus } : b));
    } catch (err: any) {
      alert(`Approval update failed: ${err.message}`);
    }
  };

  const handleDelete = async (slug: string) => {
    if (!confirm(`Are you sure you want to delete '${slug}'?`)) return;
    try {
      await deleteBlog(slug);
      setBlogs(prev => prev.filter(b => b.slug !== slug && !b.output_filename?.includes(slug)));
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const filteredBlogs = blogs.filter(b => {
    const title = b.title || b.output_filename || '';
    return title.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const totalBlogs = blogs.length;
  const approvedCount = blogs.filter(b => b.approved === 'yes').length;
  const pendingCount = blogs.filter(b => b.approved !== 'yes').length;
  const avgScore = blogs.length ? (blogs.reduce((acc, b) => acc + (b.quality_score || 0), 0) / blogs.length).toFixed(1) : '0.0';

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight">Blog Content Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Manage, audit, edit, and approve your AI-generated technical publications.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={onOpenGenerate}
            className="flex items-center gap-2 rounded-xl bg-cyan-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-900/30 hover:bg-cyan-500 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Generate New Blog</span>
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Publications</span>
            <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-100 mt-3">{totalBlogs}</div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Approved Blogs</span>
            <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 mt-3">{approvedCount}</div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Pending Review</span>
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-amber-400 mt-3">{pendingCount}</div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Avg Quality Score</span>
            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400">
              <Award className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-purple-400 mt-3">{avgScore} <span className="text-xs font-normal text-slate-400">/ 10</span></div>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by title..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-slate-800 bg-slate-950 pl-10 pr-4 py-2 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>
          <select
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Categories</option>
            <option value="Developer Technology">Developer Technology</option>
            <option value="Comparison Articles">Comparison Articles</option>
            <option value="Job Role and Career Trends">Job Role and Career Trends</option>
          </select>

          <select
            value={approvedFilter}
            onChange={e => setApprovedFilter(e.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="yes">Approved</option>
            <option value="no">Pending</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 flex items-center justify-center gap-3">
            <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
            <span>Loading publications...</span>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
        ) : filteredBlogs.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">No blogs found matching filters.</div>
        ) : (
          <div className="overflow-x-auto relative">
            <table className="w-full text-left text-sm text-slate-300 border-collapse">
              <thead className="bg-[#060E20] text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3.5 min-w-[220px]">Title</th>
                  <th className="px-4 py-3.5 whitespace-nowrap">Category</th>
                  <th className="px-4 py-3.5 whitespace-nowrap">Created</th>
                  <th className="px-4 py-3.5 text-center whitespace-nowrap">Quality</th>
                  <th className="px-4 py-3.5 text-center whitespace-nowrap">Words</th>
                  <th className="px-4 py-3.5 text-center whitespace-nowrap">Status</th>
                  <th className="px-4 py-3.5 text-right whitespace-nowrap sticky right-0 z-20 bg-[#060E20] border-l border-slate-800 shadow-[-12px_0_16px_rgba(0,0,0,0.6)]">Activity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredBlogs.map((blog, idx) => {
                  const slug = blog.slug || blog.output_filename?.replace('.md', '') || `blog-${idx}`;
                  const title = blog.title || slug;
                  const isApproved = blog.approved === 'yes';
                  const score = blog.quality_score || 0;

                  let scoreBadge = "bg-rose-500/10 text-rose-400 border-rose-500/30";
                  if (score >= 8.0) scoreBadge = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
                  else if (score >= 7.0) scoreBadge = "bg-amber-500/10 text-amber-400 border-amber-500/30";

                  return (
                    <tr key={idx} className="hover:bg-slate-800/50 transition group">
                      <td className="px-4 py-3.5 font-semibold text-slate-200 max-w-[280px] lg:max-w-[340px] truncate">
                        <button
                          onClick={() => onViewBlog(slug)}
                          className="hover:text-[#4AABEF] text-left transition truncate w-full block"
                          title={title}
                        >
                          {title}
                        </button>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span className="inline-block px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700/80">
                          {blog.category || 'General'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-400 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-[#4AABEF]" />
                          <span>{formatTimestamp(blog.created_at || (blog as any).date)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-center whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${scoreBadge}`}>
                          <Award className="w-3 h-3" />
                          <span>{score > 0 ? score.toFixed(1) : 'N/A'}</span>
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-slate-400 text-xs text-center whitespace-nowrap">
                        {blog.word_count || 0} words
                      </td>
                      <td className="px-4 py-3.5 text-center whitespace-nowrap">
                        <button
                          onClick={() => handleToggleApprove(slug, blog.approved || 'no')}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition shadow-sm cursor-pointer ${
                            isApproved
                              ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/25'
                              : 'bg-amber-500/15 border-amber-500/40 text-amber-400 hover:bg-amber-500/25'
                          }`}
                          title={isApproved ? "Click to revoke approval" : "Click to approve blog"}
                        >
                          {isApproved ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              <span>Approved</span>
                            </>
                          ) : (
                            <>
                              <X className="w-3.5 h-3.5" />
                              <span>Pending</span>
                            </>
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-3.5 text-right whitespace-nowrap sticky right-0 z-20 bg-[#091124] group-hover:bg-[#101a33] border-l border-slate-800 shadow-[-12px_0_16px_rgba(0,0,0,0.6)] transition-colors">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => onViewBlog(slug)}
                            title="View Fulcrum Publication Preview"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#4AABEF]/15 text-[#4AABEF] hover:bg-[#4AABEF] hover:text-white border border-[#4AABEF]/30 text-xs font-semibold transition-all shadow-sm cursor-pointer"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>View</span>
                          </button>
                          <button
                            onClick={() => onEditBlog(slug)}
                            title="Edit Blog Markdown & Metadata"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/15 text-indigo-400 hover:bg-indigo-600 hover:text-white border border-indigo-500/30 text-xs font-semibold transition-all shadow-sm cursor-pointer"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            <span>Edit</span>
                          </button>
                          <button
                            onClick={() => handleDelete(slug)}
                            title="Delete Blog Permanently"
                            className="p-1.5 rounded-lg bg-rose-500/15 text-rose-400 hover:bg-rose-600 hover:text-white border border-rose-500/30 transition-all shadow-sm cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
