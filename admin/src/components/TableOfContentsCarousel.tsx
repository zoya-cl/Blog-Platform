import React, { useState, useEffect } from 'react';
import { Sparkles, FileText, Target, BookOpen, Compass, ChevronRight } from 'lucide-react';

interface SlideData {
  id: number;
  type: string;
  title: string;
  description: string;
  gradient: string;
  icon: React.ComponentType<{ className?: string }>;
  buttonText: string;
}

const slides: SlideData[] = [
  {
    id: 1,
    type: 'build-resume',
    title: 'Build ATS Friendly Resume',
    description: 'Use our AI Resume builder to tailor your resume with 10+ ATS Friendly templates.',
    gradient: 'from-[#1E293B] via-[#0F172A] to-[#0284C7]/20',
    icon: FileText,
    buttonText: 'Try Now',
  },
  {
    id: 2,
    type: 'ats-score',
    title: 'Check Resume ATS Score',
    description: 'Find and fix hidden issues and gaps instantly to make sure your resume survives recruiter filters.',
    gradient: 'from-[#1E293B] via-[#0F172A] to-[#6366F1]/20',
    icon: Target,
    buttonText: 'Try Now',
  },
  {
    id: 3,
    type: 'projects',
    title: 'Industry Level Projects',
    description: 'Explore a curated project library personalized to your role and resume to bridge skills gap.',
    gradient: 'from-[#1E293B] via-[#0F172A] to-[#14B8A6]/20',
    icon: Sparkles,
    buttonText: 'Try Now',
  },
  {
    id: 4,
    type: 'playbook',
    title: 'Interview Playbook',
    description: 'Master your preparation with our famous frameworks to prepare for your next interview.',
    gradient: 'from-[#1E293B] via-[#0F172A] to-[#3B82F6]/20',
    icon: BookOpen,
    buttonText: 'Try Now',
  },
  {
    id: 5,
    type: 'dream-track',
    title: 'Dream Company Track',
    description: 'Follow a step-by-step prep roadmap tailored around the hiring process of your target company.',
    gradient: 'from-[#1E293B] via-[#0F172A] to-[#8B5CF6]/20',
    icon: Compass,
    buttonText: 'Try Now',
  },
];

export const TableOfContentsCarousel: React.FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const slide = slides[currentSlide];
  const IconComponent = slide.icon;

  return (
    <div className="w-full max-w-[320px] bg-[#0E172D] border border-[#222A3F] rounded-xl overflow-hidden flex flex-col shadow-[0_4px_11.2px_rgba(0,0,0,0.25)] transition-all duration-300 group relative">
      {/* Top Graphics Area */}
      <div className={`w-full h-[150px] relative flex-shrink-0 overflow-hidden bg-gradient-to-br ${slide.gradient} flex items-center justify-center border-b border-[#222A3F]/50`}>
        {/* Background glow circle */}
        <div className="absolute w-32 h-32 rounded-full bg-[#4AABEF]/10 blur-xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col items-center gap-2 text-center p-4">
          <div className="p-3 rounded-2xl bg-[#0E172D]/90 border border-[#222A3F] shadow-lg text-[#4AABEF]">
            <IconComponent className="w-6 h-6" />
          </div>
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#4AABEF] font-semibold">
            {slide.type.replace('-', ' ')}
          </span>
        </div>
      </div>

      {/* Content Area */}
      <div className="px-5 py-4 flex flex-col gap-4">
        <div className="min-h-[85px] flex flex-col gap-1.5">
          <h4 className="text-white text-[18px] font-medium leading-[24px]">
            {slide.title}
          </h4>
          <p className="text-[#7F889E] text-[13px] font-normal leading-[20px] line-clamp-3">
            {slide.description}
          </p>
        </div>

        {/* CTA Button and pagination dots row */}
        <div className="flex flex-col gap-3.5">
          <button
            type="button"
            className="w-full h-[36px] rounded-lg text-white text-[13px] font-medium flex items-center justify-center gap-1.5 hover:opacity-95 active:scale-[0.98] transition-all shadow-[2px_4px_8px_rgba(0,0,0,0.04)] cursor-pointer"
            style={{
              background: 'linear-gradient(47.22deg, #6E6CD8 5.72%, #40A0EF 48.21%, #77E1EE 94.27%)',
            }}
          >
            <span>{slide.buttonText}</span>
            <ChevronRight className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-0.5" />
          </button>

          {/* Pagination Indicators */}
          <div className="flex items-center justify-center gap-1.5 h-2">
            {slides.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentSlide(idx)}
                className={`rounded-full transition-all duration-300 ${
                  idx === currentSlide
                    ? 'w-4 h-1.5 bg-[#4AABEF]'
                    : 'w-1.5 h-1.5 bg-[#222A3F] hover:bg-[#7F889E]'
                }`}
                aria-label={`Go to slide ${idx + 1}`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
