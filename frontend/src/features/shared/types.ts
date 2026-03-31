export interface ResumeProfile {
  name: string;
  headline?: string;
  contact?: Record<string, string>;
}

export interface ExperienceEntry {
  role: string;
  company: string;
  location: string;
  date_range: string;
  bullets: string[];
}

export interface CategoryLine {
  category: string;
  items: string[];
}

export interface ResumeSection {
  title: string;
  paragraphs: string[];
  bullets: string[];
  meta?: {
    category_lines?: CategoryLine[];
    entries?: ExperienceEntry[];
    [key: string]: unknown;
  };
}

export interface ResumeDocumentPayload {
  resume_id: string;
  profile: ResumeProfile;
  sections: ResumeSection[];
  theme: Record<string, unknown>;
  pdf: string; // base64 encoded
}
