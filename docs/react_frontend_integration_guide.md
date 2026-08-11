# BlogGraph-AI: React Frontend Integration Guide

This guide details how to integrate the BlogGraph-AI backend API endpoints into a React frontend application, parse the custom visual components embedded in the blog posts, and render them using styled React components.

---

## 1. Backend API Integration

The React application will consume the following endpoints served by the FastAPI backend:

### A. Fetch All Blogs
*   **Endpoint**: `GET /blogs`
*   **Response Format**: A list of blog metadata records.
```json
[
  {
    "id": 1,
    "category": "AI Technology",
    "title": "What Actually Happens When You Fine-Tune a Pre-Trained LLM for Production",
    "status": "published",
    "quality_score": 8.5,
    "word_count": 2431,
    "created_at": "2026-05-30T18:15:25.278478",
    "completed_at": "2026-05-30T18:28:10.590400",
    "approved": "yes",
    "output_filename": "what-actually-happens-when-you-fine-tune-a-pre-trained-llm-for-production.md"
  }
]
```

### B. Fetch Blog Details (Single Post)
*   **Endpoint**: `GET /blogs/{blog_id}`
*   **Response Format**: Returns the raw markdown content, metadata JSON, and image mappings.
```json
{
  "id": 1,
  "category": "AI Technology",
  "title": "What Actually Happens When You Fine-Tune a Pre-Trained LLM for Production",
  "status": "published",
  "markdown_content": "# What Actually Happens When You Fine-Tune a Pre-Trained LLM for Production...",
  "metadata_json": "{\n  \"title\": \"What Actually Happens...\",\n  \"slug\": \"what-actually-happens-when-you-fine-tune-a-pre-trained-llm-for-production\",\n  \"meta_description\": \"...\",\n  \"focus_keyword\": \"...\",\n  \"generated_images\": [\n    {\n      \"image_index\": 1,\n      \"path\": \"what-actually-happens-when-you-fine-tune-a-pre-trained-llm-for-production/images/img_1.png\",\n      \"purpose\": \"...\"\n    }\n  ]\n}",
  "approved": "yes"
}
```

---

## 2. Parsing Markdown and Components in React

The `markdown_content` returned by the API contains mixed standard markdown text and custom `COMPONENT:` blocks. You should parse and render these blocks dynamically.

### Parsing Strategy (The Regex Splitter)
Use this utility function to split the markdown string into alternate blocks of raw text and parsed components:

```javascript
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Table, CodeBlock, Quiz, ComparisonWidget, Roadmap, Checklist, Confirm } from './components';

export function renderBlogContent(markdownText) {
  // Regex to capture the COMPONENT block from "COMPONENT:" to the ending "}" on its own line
  const componentRegex = /(COMPONENT:\s*\ntype:\s*\S+\s*\nprops:\s*\{[\s\S]*?\n\})/g;
  
  const segments = markdownText.split(componentRegex);
  
  return segments.map((segment, idx) => {
    if (segment.startsWith('COMPONENT:')) {
      try {
        // Parse type and props
        const typeMatch = segment.match(/type:\s*(\S+)/);
        const propsMatch = segment.match(/props:\s*(\{[\s\S]*\})/);
        
        if (!typeMatch || !propsMatch) return null;
        
        const type = typeMatch[1].trim();
        const props = JSON.parse(propsMatch[1]);
        
        const key = `comp-${idx}`;
        
        switch (type) {
          case 'table':
            return <Table key={key} {...props} />;
          case 'code_block':
            return <CodeBlock key={key} {...props} />;
          case 'quiz':
            return <Quiz key={key} {...props} />;
          case 'comparison_widget':
            return <ComparisonWidget key={key} {...props} />;
          case 'roadmap':
            return <Roadmap key={key} {...props} />;
          case 'checklist':
            return <Checklist key={key} {...props} />;
          case 'confirm':
            return <Confirm key={key} {...props} />;
          default:
            return <div key={key}>Unsupported Component: {type}</div>;
        }
      } catch (err) {
        console.error("Failed to parse component block:", err, segment);
        return <pre key={idx} className="p-4 bg-red-50 text-red-600 rounded">{segment}</pre>;
      }
    }
    
    // Fallback to standard Markdown rendering for prose
    return <ReactMarkdown key={idx}>{segment}</ReactMarkdown>;
  });
}
```

---

## 3. Component Specifications & React Implementations

Below is the raw Markdown syntax outputted by the backend, followed by its corresponding premium TailwindCSS React implementation, for all 7 components.

### 1. Code Block (`code_block`)

#### Raw Markdown Output
```text
COMPONENT:
type: code_block
props: {
  "language": "python",
  "code": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
  "explanation": "Binary search divides the search space in half with each iteration, yielding O(log n) complexity."
}
```

#### React Component
```jsx
export function CodeBlock({ language, code, explanation }) {
  return (
    <div className="my-8 border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-slate-950">
      <div className="flex justify-between items-center px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs font-mono text-slate-400">
        <span>{language.toUpperCase()}</span>
        <button 
          onClick={() => navigator.clipboard.writeText(code)}
          className="hover:text-white transition-colors"
        >
          Copy Code
        </button>
      </div>
      <pre className="p-5 overflow-x-auto text-sm font-mono text-slate-200 leading-relaxed">
        <code>{code}</code>
      </pre>
      {explanation && (
        <div className="px-5 py-3 border-t border-slate-900 bg-slate-900/50 text-sm italic text-slate-400">
          💡 {explanation}
        </div>
      )}
    </div>
  );
}
```

---

### 2. Table (`table`)

#### Raw Markdown Output
```text
COMPONENT:
type: table
props: {
  "headers": ["Comparison Criteria", "Option A", "Option B"],
  "rows": [
    ["Direct Feature X", "Supported natively", "Requires plugin"],
    ["Performance Impact", "Low overhead (<5ms)", "High overhead (>150ms)"]
  ],
  "caption": "Table 1.1: Feature and Performance Comparison"
}
```

#### React Component
```jsx
export function Table({ headers, rows, caption }) {
  return (
    <div className="my-8 border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm text-left">
          {caption && (
            <caption className="p-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-left bg-slate-50 border-b border-slate-200">
              {caption}
            </caption>
          )}
          <thead className="bg-slate-50 text-slate-700 font-semibold">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="px-6 py-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-600">
            {rows.map((row, i) => (
              <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                {row.map((cell, j) => (
                  <td key={j} className="px-6 py-4">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

### 3. Quiz (`quiz`)

#### Raw Markdown Output
```text
COMPONENT:
type: quiz
props: {
  "question": "Which visual boundary does a container share with the host OS, unlike a Virtual Machine?",
  "options": [
    "The physical hardware interface",
    "The operating system kernel",
    "The network adapter space",
    "The application runtime environment"
  ],
  "correct_answer": "The operating system kernel",
  "explanation": "Containers share the host OS kernel via namespaces and cgroups, while VMs run a complete guest OS."
}
```

#### React Component
```jsx
import { useState } from 'react';

export function Quiz({ question, options, correct_answer, explanation }) {
  const [selected, setSelected] = useState(null);
  
  return (
    <div className="my-8 border border-slate-200 rounded-xl p-6 bg-slate-50/50 shadow-sm">
      <div className="text-xs font-bold uppercase tracking-wider text-indigo-500 mb-2">Knowledge Check</div>
      <h4 className="text-base font-bold text-slate-800 mb-4">{question}</h4>
      <div className="space-y-2">
        {options.map((opt, i) => {
          let optionStyle = "border-slate-200 text-slate-700 bg-white hover:bg-slate-50";
          if (selected !== null) {
            if (opt === correct_answer) {
              optionStyle = "border-green-500 bg-green-50 text-green-700 font-medium";
            } else if (opt === selected) {
              optionStyle = "border-red-400 bg-red-50 text-red-700";
            } else {
              optionStyle = "border-slate-200 text-slate-400 opacity-60 bg-white";
            }
          }
          
          return (
            <button
              key={i}
              disabled={selected !== null}
              onClick={() => setSelected(opt)}
              className={`w-full text-left px-4 py-3 border rounded-lg text-sm transition-all duration-200 ${optionStyle}`}
            >
              {opt}
            </button>
          );
        })}
      </div>
      {selected !== null && (
        <div className="mt-4 pt-3 border-t border-dashed border-slate-200 text-sm text-slate-500 italic animate-fade-in">
          ✦ {explanation}
        </div>
      )}
    </div>
  );
}
```

---

### 4. Comparison Widget (`comparison_widget`)

#### Raw Markdown Output
```text
COMPONENT:
type: comparison_widget
props: {
  "left_title": "Relational Databases (SQL)",
  "right_title": "Non-Relational Databases (NoSQL)",
  "metrics": [
    {"name": "Schema Design", "left": "Strict predefined tables", "right": "Dynamic schema models"},
    {"name": "Horizontal Scalability", "left": "Complex (sharding required)", "right": "Native scale-out support"}
  ]
}
```

#### React Component
```jsx
export function ComparisonWidget({ left_title, right_title, metrics }) {
  return (
    <div className="my-8 border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
      <div className="grid grid-cols-2 text-center text-sm font-bold text-white bg-slate-900">
        <div className="py-3 border-r border-slate-800">{left_title}</div>
        <div className="py-3">{right_title}</div>
      </div>
      <div className="divide-y divide-slate-100 text-sm">
        {metrics.map((m, idx) => (
          <div key={idx} className="grid grid-cols-2 divide-x divide-slate-100 hover:bg-slate-50/50">
            <div className="p-4">
              <div className="text-xs font-semibold text-slate-400 mb-1">{m.name}</div>
              <div className="text-slate-700">{m.left}</div>
            </div>
            <div className="p-4">
              <div className="text-xs font-semibold text-slate-400 mb-1">{m.name}</div>
              <div className="text-slate-700">{m.right}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### 5. Roadmap (`roadmap`)

#### Raw Markdown Output
```text
COMPONENT:
type: roadmap
props: {
  "title": "Your DSA Interview Preparation Path",
  "steps": [
    {"label": "Arrays & Hashing", "description": "Build foundational pattern recognition with frequency maps and prefix sums."},
    {"label": "Two Pointers", "description": "Learn pointer manipulation for sorted arrays and boundary windows."}
  ]
}
```

#### React Component
```jsx
export function Roadmap({ title, steps }) {
  return (
    <div className="my-8 border border-slate-200 rounded-xl p-6 bg-white shadow-sm">
      {title && <h4 className="text-lg font-bold text-slate-800 mb-6">{title}</h4>}
      <div className="relative pl-10 border-l-2 border-indigo-200 space-y-8 ml-3">
        {steps.map((step, idx) => (
          <div key={idx} className="relative">
            <div className="absolute -left-[51px] top-0.5 w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shadow-md">
              {idx + 1}
            </div>
            <h5 className="font-semibold text-sm text-slate-800 mb-1">{step.label}</h5>
            <p className="text-xs text-slate-500 leading-relaxed">{step.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### 6. Checklist (`checklist`)

#### Raw Markdown Output
```text
COMPONENT:
type: checklist
props: {
  "title": "Immediate Actions Checklist",
  "items": [
    "Identify performance bottlenecks via profilers.",
    "Choose a target quantization scale (e.g. FP8 or INT4).",
    "Run inference benchmarks on deployment GPUs."
  ]
}
```

#### React Component
```jsx
export function Checklist({ title, items }) {
  return (
    <div className="my-8 border border-slate-200 rounded-xl p-6 bg-white shadow-sm">
      {title && <h4 className="text-base font-bold text-slate-800 mb-4">{title}</h4>}
      <ul className="space-y-3">
        {items.map((item, idx) => (
          <li key={idx} className="flex items-start gap-3 text-sm text-slate-600">
            <span className="flex-shrink-0 w-5 h-5 rounded-md bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center font-bold text-xs">
              ✓
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

### 7. Confirmation Widget (`confirm`)

#### Raw Markdown Output
```text
COMPONENT:
type: confirm
props: {
  "title": "Code Trace Verification",
  "prompt": "Trace the recursive call stack above. Do you understand the boundary conditions?",
  "button_text": "I Understand",
  "success_message": "Awesome! You have successfully verified the trace boundary.",
  "image_path": ""
}
```

#### React Component
```jsx
import { useState } from 'react';

export function Confirm({ title, prompt, button_text, success_message, image_path }) {
  const [confirmed, setConfirmed] = useState(false);
  
  return (
    <div className="my-8 border border-slate-200 rounded-xl p-6 bg-gradient-to-br from-slate-50 to-blue-50/50 text-center shadow-sm">
      {title && <h4 className="text-lg font-extrabold text-blue-900 mb-2">{title}</h4>}
      {prompt && <p className="text-sm text-slate-600 mb-4 leading-relaxed">{prompt}</p>}
      
      {image_path && (
        <div className="my-4 border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm max-w-md mx-auto">
          <img src={image_path} alt="Visual Illustration" className="w-full h-auto object-cover" />
        </div>
      )}
      
      {!confirmed ? (
        <button
          onClick={() => setConfirmed(true)}
          className="mt-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-750 hover:to-indigo-750 text-white text-sm font-bold py-2.5 px-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
        >
          {button_text}
        </button>
      ) : (
        <div className="mt-4 py-2 px-4 bg-green-50 border border-green-200 text-green-700 text-sm font-bold rounded-lg animate-bounce">
          ✓ {success_message}
        </div>
      )}
    </div>
  );
}
```

---

## 4. Overall Blog Markdown Schema/Format

Each generated blog post (returned via the `markdown_content` API field or stored physically on disk) follows this exact structural format:

```markdown
# [Blog Title Heading]

**Category:** [Category Name] | **Date:** [YYYY-MM-DD] | **Word Count:** [Word Count] | **Reading Time:** [Time] min | **Score:** [Quality Score]/10 | **Revisions:** [Count]
---

## Introduction to [Topic]
[Prose introduction paragraph...]

💡 tip: [This gets converted to a styled TIP box in the admin dashboard, but remains a standard text block inside the raw markdown file]

## [H2 Heading 1]
[Prose...]

COMPONENT:
type: table
props: {
  "headers": ["...", "..."],
  "rows": [
    ["...", "..."]
  ]
}

![[Visual Image Purpose]]([absolute_url_or_s3_url_to_image])

## [H2 Heading 2]
[Prose...]

COMPONENT:
type: code_block
props: {
  "language": "python",
  "code": "...",
  "explanation": "..."
}

## Frequently Asked Questions

### [FAQ Question 1]?
[FAQ Answer 1...]

### [FAQ Question 2]?
[FAQ Answer 2...]

## Conclusion and Next Steps: [Topic]
[Prose summary...]

COMPONENT:
type: quiz
props: {
  "question": "...",
  "options": ["...", "..."],
  "correct_answer": "...",
  "explanation": "..."
}

COMPONENT:
type: quiz
props: {
  ...
}

COMPONENT:
type: quiz
props: {
  ...
}
```

---

## 5. Overall Sidecar Metadata JSON Schema

When retrieving single blog details (or loading the sidecar `.json` file generated on disk), you will receive the following JSON metadata structure in the `metadata_json` field. Use these fields to drive SEO cards, tag indexes, reading speed labels, or dashboard status tables.

```json
{
  "title": "What Actually Happens When You Fine-Tune a Pre-Trained LLM for Production",
  "slug": "what-actually-happens-when-you-fine-tune-a-pre-trained-llm-for-production",
  "date": "2026-05-30",
  "category": "AI Technology",
  "audience_level": "intermediate",
  "tags": [
    "Fine-Tuning",
    "LLM",
    "Production AI"
  ],
  "meta_description": "A deep look at fine-tuning LLMs for production environments, covering hyperparameters, latency, and open-source tooling.",
  "focus_keyword": "fine-tuning llm for production",
  "secondary_keywords": [
    "supervised fine-tuning",
    "inference latency",
    "open-source frameworks"
  ],
  "word_count": 2431,
  "word_count_target": 2000,
  "section_count_target": 6,
  "reading_time_minutes": 13,
  "quality_score": 8.5,
  "revision_count": 0,
  "prompt_version": 1,
  "generated_images": [
    {
      "image_index": 1,
      "path": "what-actually-happens-when-you-fine-tune-a-pre-trained-llm-for-production/images/img_1.png",
      "purpose": "Illustrate the different fine-tuning methods for LLMs."
    }
  ],
  "approved": "no"
}
```

### JSON Property Dictionary
*   `title` (*string*): The clean, final heading title of the blog.
*   `slug` (*string*): Sanitized lowercase url-friendly string. Used for directories and url routes.
*   `date` (*string*): ISO or standard date of generation (YYYY-MM-DD).
*   `category` (*string*): One of the 8 predefined pipeline category tags.
*   `audience_level` (*string*): Target reader difficulty level (`"fresher"` or `"intermediate"`).
*   `tags` (*array of strings*): Core topics covered in the post.
*   `meta_description` (*string*): Compelling SEO description capped under 160 characters.
*   `focus_keyword` (*string*): The primary target keyword targeted for search engines.
*   `secondary_keywords` (*array of strings*): Related terms curated for context optimization.
*   `word_count` (*number*): Total word count of the compiled markdown text.
*   `word_count_target` (*number*): The original target word count requested in config.
*   `section_count_target` (*number*): Count of H2 sections in the outline configuration.
*   `reading_time_minutes` (*number*): Average estimated reading speed minutes (Word Count / 200).
*   `quality_score` (*number*): Qualitative grading score awarded by the agent auditor (0.0 to 10.0).
*   `revision_count` (*number*): Count of total rewrite runs triggered during compile loops.
*   `prompt_version` (*number*): Pipeline prompts catalog version.
*   `generated_images` (*array of objects*): Mappings of images generated by the pipeline. Contains `image_index`, image endpoint `path` (relative local or absolute S3 URL), and visual `purpose`.
*   `approved` (*string*): Reviewer status (`"yes"` or `"no"`).

---

## 6. Code Consistency

### Why is this component syntax consistent?
The component block syntax is guaranteed to remain 100% consistent across every single run of the pipeline:
1.  **Strict Prompt Rules**: The writing nodes enforce strict structure guidelines.
2.  **Strict Evaluator Capping**: The grader and detector loops validate that all syntax constraints are respected, ensuring incorrect formats never get published.
3.  **Coherence Node Preservation**: The coherence editor treats any block starting with `COMPONENT:` and ending with `}` as an **immutable, black-box object**, preventing syntax modifications during stitching.
