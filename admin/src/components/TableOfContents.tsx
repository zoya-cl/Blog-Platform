import React, { useState, useEffect } from 'react';

export interface TocItem {
  id: string;
  label: string;
}

interface TableOfContentsProps {
  items: TocItem[];
}

export const TableOfContents: React.FC<TableOfContentsProps> = ({ items }) => {
  const [activeId, setActiveId] = useState<string>(items[0]?.id || '');

  useEffect(() => {
    if (items.length === 0) return;

    const handleScroll = () => {
      const scrollPosition = window.scrollY + 140;
      for (let i = items.length - 1; i >= 0; i--) {
        const el = document.getElementById(items[i].id);
        if (el && el.offsetTop <= scrollPosition) {
          setActiveId(items[i].id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [items]);

  if (!items || items.length === 0) return null;

  return (
    <div className="flex flex-col gap-4 w-full max-w-[320px]">
      <h3 className="text-white text-[18px] lg:text-[20px] font-bold leading-[22px] tracking-[0.5px] uppercase">
        Table of Contents
      </h3>
      <ul className="flex flex-col gap-[12px]">
        {items.map((item, idx) => {
          const isActive = activeId === item.id;
          return (
            <li key={item.id} className="list-none">
              <a
                href={`#${item.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  const target = document.getElementById(item.id);
                  if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                    setActiveId(item.id);
                  }
                }}
                className={`text-[15px] lg:text-[16px] leading-[22px] transition-all duration-200 block font-normal hover:translate-x-0.5 ${
                  isActive
                    ? 'text-[#4AABEF] font-medium translate-x-0.5'
                    : 'text-[#B6BFCE] hover:text-white'
                }`}
              >
                {idx + 1}. {item.label}
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
