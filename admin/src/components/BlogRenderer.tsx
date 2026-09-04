import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ComparisonWidget } from './ComparisonWidget';
import { DataTable } from './DataTable';
import { QuizCard } from './QuizCard';
import { CodeBlock } from './CodeBlock';
import { CheckCircle2 } from 'lucide-react';

interface BlogRendererProps {
  content: string;
}

interface Segment {
  type: 'markdown' | 'component' | 'image';
  content: string;
  componentData?: {
    type: string;
    props: any;
  };
  imageData?: {
    src: string;
    alt: string;
  };
}

export function extractTocFromMarkdown(content: string): { id: string; label: string }[] {
  if (!content) return [];
  const lines = content.split('\n');
  const toc: { id: string; label: string }[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('## ') && !trimmed.startsWith('### ')) {
      const heading = trimmed.replace(/^##\s+/, '').replace(/\*\*/g, '').trim();
      const id = heading
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/[-\s]+/g, '-')
        .replace(/^-+|-+$/g, '');
      if (heading && id) {
        toc.push({ id, label: heading });
      }
    }
  }
  return toc;
}

const RoadmapComponent: React.FC<{ title?: string; steps?: { label: string; description: string }[] }> = ({
  title,
  steps = [],
}) => {
  return (
    <div className="my-8 p-6 rounded-2xl bg-[#0E172D] border border-[#222A3F] shadow-xl">
      {title && (
        <h4 className="text-white text-[20px] font-semibold mb-6 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-[#4AABEF]" />
          <span>{title}</span>
        </h4>
      )}
      <div className="space-y-4">
        {steps.map((step, idx) => (
          <div key={idx} className="flex gap-4 items-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#4AABEF]/10 border border-[#4AABEF]/40 text-[#4AABEF] font-bold text-sm flex items-center justify-center">
              {idx + 1}
            </div>
            <div className="flex-1">
              <div className="text-white text-[16px] font-medium">{step.label}</div>
              {step.description && (
                <div className="text-[#8C8C9E] text-[14px] mt-0.5 leading-relaxed">{step.description}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export const BlogRenderer: React.FC<BlogRendererProps> = ({ content }) => {
  if (!content) return null;

  // Remove frontmatter header line `# Title \n **Category:** ... \n ---` if present
  let cleanContent = content;
  cleanContent = cleanContent.replace(/^#\s+[^\n]+\n\s*\*\*Category:\*\*.*?\n---\s*/s, '');

  // Regex matching either COMPONENT: or IMAGE: blocks
  const blockRegex = /(?:COMPONENT:\s*\nType:\s*([a-zA-Z0-9_]+)\s*\nProps:\s*(\{[\s\S]*?\})|IMAGE:\s*\nsrc:\s*([^\n]+)\s*\nalt:\s*([^\n]+))(?=\n\n|\n[A-Z#]|\s*$)/g;

  const segments: Segment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = blockRegex.exec(cleanContent)) !== null) {
    const matchIndex = match.index;
    if (matchIndex > lastIndex) {
      const textChunk = cleanContent.substring(lastIndex, matchIndex).trim();
      if (textChunk) {
        segments.push({ type: 'markdown', content: textChunk });
      }
    }

    if (match[1]) {
      // COMPONENT: block
      const compType = match[1].trim();
      const propsJsonStr = match[2].trim();
      try {
        const parsedProps = JSON.parse(propsJsonStr);
        segments.push({
          type: 'component',
          content: match[0],
          componentData: {
            type: compType,
            props: parsedProps,
          },
        });
      } catch {
        segments.push({ type: 'markdown', content: match[0] });
      }
    } else if (match[3]) {
      // IMAGE: block
      const rawSrc = match[3].trim();
      const alt = match[4].trim();
      const src = rawSrc.startsWith('http')
        ? rawSrc
        : `http://localhost:8000${rawSrc.startsWith('/') ? '' : '/'}${rawSrc}`;
      segments.push({
        type: 'image',
        content: match[0],
        imageData: { src, alt },
      });
    }

    lastIndex = blockRegex.lastIndex;
  }

  if (lastIndex < cleanContent.length) {
    const tailChunk = cleanContent.substring(lastIndex).trim();
    if (tailChunk) {
      segments.push({ type: 'markdown', content: tailChunk });
    }
  }

  return (
    <div className="w-full space-y-6 text-[#E0E0E0] font-sans">
      {segments.map((seg, idx) => {
        if (seg.type === 'markdown') {
          return (
            <ReactMarkdown
              key={idx}
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h1 className="text-white text-3xl md:text-[32px] font-medium leading-tight lg:leading-[43.2px] tracking-[-0.5px] mt-8 mb-4 border-b border-white/[0.07] pb-3">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => {
                  const text = String(children).replace(/\*\*/g, '').trim();
                  const id = text
                    .toLowerCase()
                    .replace(/[^\w\s-]/g, '')
                    .replace(/[-\s]+/g, '-')
                    .replace(/^-+|-+$/g, '');
                  return (
                    <h2
                      id={id}
                      className="text-white text-[28px] lg:text-[32px] font-medium leading-[38px] lg:leading-[40px] tracking-[-0.5px] mt-12 mb-4 scroll-mt-24"
                    >
                      {children}
                    </h2>
                  );
                },
                h3: ({ children }) => (
                  <h3 className="text-white text-[22px] lg:text-[24px] font-medium leading-[32px] mt-8 mb-3">
                    {children}
                  </h3>
                ),
                p: ({ children }) => (
                  <p className="mb-5 text-[#E0E0E0] text-[18px] lg:text-[20px] leading-[30px] lg:leading-[32px] font-normal">
                    {children}
                  </p>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#4AABEF] hover:underline underline-offset-4 font-medium transition"
                  >
                    {children}
                  </a>
                ),
                strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                ul: ({ children }) => (
                  <ul className="list-disc list-outside space-y-2 mb-6 pl-6 text-[#E0E0E0] text-[17px] lg:text-[19px] leading-[30px]">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-outside space-y-2 mb-6 pl-6 text-[#E0E0E0] text-[17px] lg:text-[19px] leading-[30px]">
                    {children}
                  </ol>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-[#4AABEF] bg-[#0E172D] border border-y border-r border-[#222A3F] p-5 rounded-r-xl italic text-[#E0E0E0] my-6">
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="border-white/[0.07] my-10" />,
                table: ({ children }) => (
                  <div className="overflow-x-auto my-6 rounded-xl border border-[#222A3F] bg-[#0E172D]">
                    <table className="w-full text-left text-[15px] border-collapse">{children}</table>
                  </div>
                ),
                thead: ({ children }) => <thead className="bg-[#131F3B] text-white border-b border-[#222A3F]">{children}</thead>,
                th: ({ children }) => <th className="p-3.5 font-semibold text-white tracking-wide">{children}</th>,
                td: ({ children }) => <td className="p-3.5 border-b border-[#222A3F]/60 text-[#CBD5E1]">{children}</td>,
              }}
            >
              {seg.content}
            </ReactMarkdown>
          );
        } else if (seg.type === 'component' && seg.componentData) {
          const { type, props } = seg.componentData;
          if (type === 'comparison_widget') {
            return <ComparisonWidget key={idx} {...props} />;
          } else if (type === 'table') {
            return <DataTable key={idx} {...props} />;
          } else if (type === 'quiz') {
            return <QuizCard key={idx} {...props} />;
          } else if (type === 'code_block') {
            return <CodeBlock key={idx} {...props} />;
          } else if (type === 'roadmap') {
            return <RoadmapComponent key={idx} {...props} />;
          }
        } else if (seg.type === 'image' && seg.imageData) {
          return (
            <div
              key={idx}
              className="my-8 rounded-2xl overflow-hidden border border-[#222A3F] bg-[#0E172D] shadow-2xl transition hover:border-[#4AABEF]/40"
            >
              <img
                src={seg.imageData.src}
                alt={seg.imageData.alt}
                className="w-full h-auto max-h-[520px] object-cover"
                loading="lazy"
              />
              {seg.imageData.alt && (
                <div className="px-5 py-3 bg-[#091124] border-t border-[#222A3F] flex items-center justify-between text-xs text-[#8C8C9E]">
                  <span className="italic">{seg.imageData.alt}</span>
                  <span className="text-[10px] font-mono tracking-wider uppercase px-2 py-0.5 rounded-full bg-[#4AABEF]/10 text-[#4AABEF] border border-[#4AABEF]/30">
                    Visual
                  </span>
                </div>
              )}
            </div>
          );
        }
        return null;
      })}
    </div>
  );
};
