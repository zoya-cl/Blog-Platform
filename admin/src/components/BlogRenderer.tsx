import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ComparisonWidget } from './ComparisonWidget';
import { DataTable } from './DataTable';
import { QuizCard } from './QuizCard';
import { CodeBlock } from './CodeBlock';

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
            props: parsedProps
          }
        });
      } catch {
        segments.push({ type: 'markdown', content: match[0] });
      }
    } else if (match[3]) {
      // IMAGE: block
      const rawSrc = match[3].trim();
      const alt = match[4].trim();
      const src = rawSrc.startsWith('http') ? rawSrc : `http://localhost:8000${rawSrc.startsWith('/') ? '' : '/'}${rawSrc}`;
      segments.push({
        type: 'image',
        content: match[0],
        imageData: { src, alt }
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
    <div className="prose prose-invert prose-slate max-w-none space-y-6 text-slate-300 leading-relaxed font-sans text-base">
      {segments.map((seg, idx) => {
        if (seg.type === 'markdown') {
          return (
            <ReactMarkdown
              key={idx}
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => <h1 className="text-3xl font-extrabold text-slate-100 mt-8 mb-4 border-b border-slate-800 pb-3">{children}</h1>,
                h2: ({ children }) => <h2 className="text-2xl font-bold text-slate-100 mt-10 mb-4 border-b border-slate-800/80 pb-2">{children}</h2>,
                h3: ({ children }) => <h3 className="text-xl font-semibold text-cyan-400 mt-6 mb-3">{children}</h3>,
                p: ({ children }) => <p className="mb-4 text-slate-300 leading-relaxed text-base">{children}</p>,
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:text-cyan-300 underline underline-offset-4 font-medium transition">
                    {children}
                  </a>
                ),
                ul: ({ children }) => <ul className="list-disc list-inside space-y-2 mb-4 text-slate-300">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside space-y-2 mb-4 text-slate-300">{children}</ol>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-cyan-500 bg-slate-900/60 p-4 rounded-r-lg italic text-slate-300 my-6">
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="border-slate-800 my-8" />
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
          }
        } else if (seg.type === 'image' && seg.imageData) {
          return (
            <div key={idx} className="my-8 rounded-2xl overflow-hidden border border-slate-800 bg-slate-900/70 shadow-2xl transition hover:border-slate-700">
              <img
                src={seg.imageData.src}
                alt={seg.imageData.alt}
                className="w-full h-auto max-h-[520px] object-cover"
                loading="lazy"
              />
              {seg.imageData.alt && (
                <div className="px-5 py-3 bg-slate-950/90 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <span className="italic">{seg.imageData.alt}</span>
                  <span className="text-[10px] font-mono tracking-wider uppercase px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800/50">
                    AI Visual
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
