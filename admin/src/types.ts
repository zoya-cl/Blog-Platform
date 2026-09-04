export interface BlogSummary {
  title?: string;
  slug?: string;
  category?: string;
  status?: string;
  approved?: string;
  quality_score?: number;
  word_count?: number;
  created_at?: string;
  updated_at?: string;
  output_filename?: string;
  thumbnail?: string;
}

export interface BlogListResponse {
  total: number;
  skip: number;
  limit: number;
  blogs: BlogSummary[];
}

export interface BlogMetadata {
  title?: string;
  slug?: string;
  date?: string;
  category?: string;
  blog_format?: string;
  audience_level?: string;
  tags?: string[];
  meta_description?: string;
  focus_keyword?: string;
  secondary_keywords?: string[];
  word_count?: number;
  word_count_target?: number;
  section_count_target?: number;
  reading_time_minutes?: number;
  quality_score?: number;
  revision_count?: number;
  approved?: string;
  thumbnail?: string;
  thumbnail_prompt?: string;
  image_count?: number;
  truncation_warnings?: string[];
}

export interface BlogDetail {
  slug: string;
  title: string;
  category: string;
  approved: string;
  status: string;
  quality_score: number;
  word_count: number;
  metadata: BlogMetadata;
  markdown_content: string;
}

export interface ComparisonMetric {
  name: string;
  left: string;
  right: string;
}

export interface ComparisonWidgetProps {
  left_title: string;
  right_title: string;
  metrics: ComparisonMetric[];
}

export interface DataTableProps {
  headers: string[];
  rows: string[][];
}

export interface QuizProps {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

export interface CodeBlockProps {
  language?: string;
  code: string;
}

export interface BlogUpdateRequest {
  title?: string;
  markdown_content?: string;
  meta_description?: string;
  category?: string;
  tags?: string[];
  focus_keyword?: string;
}
