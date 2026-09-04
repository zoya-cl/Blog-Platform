import { useState } from 'react';
import { Dashboard } from './components/Dashboard';
import { BlogViewer } from './components/BlogViewer';
import { BlogEditor } from './components/BlogEditor';
import { GenerateModal } from './components/GenerateModal';
import { Sparkles, Layers, FileCode2 } from 'lucide-react';

type ViewMode = 'dashboard' | 'viewer' | 'editor';

export function App() {
  const [currentView, setCurrentView] = useState<ViewMode>('dashboard');
  const [selectedSlug, setSelectedSlug] = useState<string>('');
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleViewBlog = (slug: string) => {
    setSelectedSlug(slug);
    setCurrentView('viewer');
  };

  const handleEditBlog = (slug: string) => {
    setSelectedSlug(slug);
    setCurrentView('editor');
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
    setSelectedSlug('');
  };

  const handleSaved = () => {
    showToast('Blog updated and saved successfully!');
    setCurrentView('viewer');
  };

  const handleGenerateSuccess = () => {
    showToast('Blog generation task initiated in background!');
    setCurrentView('dashboard');
  };

  return (
    <div className="min-h-screen bg-[#040D24] text-slate-100 font-sans flex flex-col">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-5 right-5 z-50 rounded-xl bg-[#4AABEF] px-5 py-3 text-sm font-semibold text-white shadow-2xl animate-bounce">
          {toastMessage}
        </div>
      )}

      {/* Main Top Navigation Header (hidden in full viewer mode to let the preview shine) */}
      {currentView !== 'viewer' && (
        <header className="sticky top-0 z-40 border-b border-[#222A3F] bg-[#091124]/90 backdrop-blur-md px-6 py-4">
          <div className="max-w-[1440px] mx-auto flex items-center justify-between">
            <div
              onClick={handleBackToDashboard}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-[#4AABEF] to-[#6E6CD8] text-white shadow-lg shadow-[#4AABEF]/20 group-hover:scale-105 transition-transform">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-extrabold text-white tracking-tight">BlogGraph-AI</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[#4AABEF]/10 border border-[#4AABEF]/30 text-[#4AABEF]">
                    Admin
                  </span>
                </div>
                <p className="text-xs text-[#8C8C9E]">Autonomous Content & Publishing Control Center</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {currentView !== 'dashboard' && (
                <button
                  onClick={handleBackToDashboard}
                  className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-[#0E172D] border border-[#222A3F] text-slate-300 hover:bg-[#131F3B] transition"
                >
                  <FileCode2 className="w-4 h-4 text-[#4AABEF]" />
                  <span>Dashboard</span>
                </button>
              )}

              <button
                onClick={() => setIsGenerateOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#4AABEF] hover:bg-[#3b9ae0] text-white font-semibold text-xs transition shadow-lg shadow-[#4AABEF]/20 cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                <span>New AI Generation</span>
              </button>
            </div>
          </div>
        </header>
      )}

      {/* Main Content Area */}
      <main className={`flex-1 w-full ${currentView === 'viewer' ? '' : 'max-w-[1440px] mx-auto p-4 sm:p-6 lg:p-8'}`}>
        {currentView === 'dashboard' && (
          <Dashboard
            onViewBlog={handleViewBlog}
            onEditBlog={handleEditBlog}
            onOpenGenerate={() => setIsGenerateOpen(true)}
          />
        )}

        {currentView === 'viewer' && (
          <BlogViewer
            slug={selectedSlug}
            onBack={handleBackToDashboard}
            onEdit={handleEditBlog}
          />
        )}

        {currentView === 'editor' && (
          <BlogEditor
            slug={selectedSlug}
            onBack={handleBackToDashboard}
            onSaved={handleSaved}
          />
        )}
      </main>

      {/* Footer (shown on dashboard & editor) */}
      {currentView !== 'viewer' && (
        <footer className="border-t border-[#222A3F] py-6 text-center text-xs text-[#8C8C9E] bg-[#091124]">
          BlogGraph-AI Engine & Admin Dashboard • Powered by LangGraph, FastAPI, MongoDB & Fulcrum Design System
        </footer>
      )}

      {/* Generate AI Modal */}
      <GenerateModal
        isOpen={isGenerateOpen}
        onClose={() => setIsGenerateOpen(false)}
        onSuccess={handleGenerateSuccess}
      />
    </div>
  );
}

export default App;
