import type { CategoryLine, ExperienceEntry, ResumeSection } from '@/features/shared/types';

export enum SectionKind {
  Summary = 'summary',
  TechnicalSkills = 'technical-skills',
  Experience = 'experience',
  Generic = 'generic',
}

export interface CategoryLineFormValue {
  category: string;
  items: string;
}

export interface ExperienceEntryFormValue {
  role: string;
  company: string;
  location: string;
  date_range: string;
  bullets: string;
}

export interface SectionFormValue {
  title: string;
  kind: SectionKind;
  paragraphs: string;
  bullets: string;
  categoryLines?: CategoryLineFormValue[];
  experiences?: ExperienceEntryFormValue[];
  rawMeta?: Record<string, unknown>;
}

export interface ResumeEditorFormValues {
  sections: SectionFormValue[];
}

const EXPERIENCE_TITLES = ['professional experience', 'experience'];

function normaliseParagraphs(paragraphs: string[]): string {
  return paragraphs.join('\n\n');
}

function normaliseBullets(bullets: string[]): string {
  return bullets.join('\n');
}

function serialiseParagraphs(value: string): string[] {
  return value
    .split(/\n{2,}/)
    .map((line) => line.trim())
  .filter(Boolean);
}

function serialiseBullets(value: string): string[] {
  return value
    .split(/\n+/)
    .map((line) => line.replace(/^[-■]\s*/, '').trim())
    .filter(Boolean);
}

function determineKind(section: ResumeSection): SectionKind {
  const title = section.title.toLowerCase();
  if (title.includes('technical') && title.includes('skill')) {
    return SectionKind.TechnicalSkills;
  }
  if (EXPERIENCE_TITLES.includes(title)) {
    return SectionKind.Experience;
  }
  if (title.includes('summary')) {
    return SectionKind.Summary;
  }
  return SectionKind.Generic;
}

function normaliseCategoryLines(meta?: ResumeSection['meta']): CategoryLine[] {
  const raw = meta?.category_lines;
  if (!Array.isArray(raw)) {
    return [];
  }

  return raw.map((entry) => {
    if (Array.isArray(entry)) {
      const [category, items] = entry;
      return {
        category: String(category ?? ''),
        items: Array.isArray(items) ? (items as string[]) : [],
      };
    }
    return entry as CategoryLine;
  });
}

function normaliseExperiences(meta?: ResumeSection['meta']): ExperienceEntry[] {
  const entries = meta?.entries;
  if (!Array.isArray(entries)) {
    return [];
  }
  return entries as ExperienceEntry[];
}

export function mapSectionsToForm(sections: ResumeSection[]): SectionFormValue[] {
  return sections.map((section) => {
    const kind = determineKind(section);
    const base: SectionFormValue = {
      title: section.title,
      kind,
      paragraphs: normaliseParagraphs(section.paragraphs),
      bullets: normaliseBullets(section.bullets),
      rawMeta: section.meta ?? {},
    };

    if (kind === SectionKind.TechnicalSkills) {
      const lines = normaliseCategoryLines(section.meta);
      base.categoryLines =
        lines.length > 0
          ? lines.map((line) => ({
              category: line.category,
              items: line.items.join(', '),
            }))
          : [
              {
                category: '',
                items: '',
              },
            ];
    }

    if (kind === SectionKind.Experience) {
      const entries = normaliseExperiences(section.meta);
      base.experiences =
        entries.length > 0
          ? entries.map((entry) => ({
              role: entry.role ?? '',
              company: entry.company ?? '',
              location: entry.location ?? '',
              date_range: entry.date_range ?? '',
              bullets: (entry.bullets ?? []).join('\n'),
            }))
          : [
              {
                role: '',
                company: '',
                location: '',
                date_range: '',
                bullets: '',
              },
            ];
    }

    return base;
  });
}

export function mapFormToSections(values: SectionFormValue[]): ResumeSection[] {
  return values.map((value) => {
    const paragraphs = serialiseParagraphs(value.paragraphs);
    const bullets = serialiseBullets(value.bullets);
    const meta = { ...(value.rawMeta ?? {}) } as Record<string, unknown>;

    if (value.kind === SectionKind.TechnicalSkills) {
      const categoryLines = (value.categoryLines ?? [])
        .map((line) => ({
          category: line.category.trim(),
          items: line.items
            .split(/(?:,\s*|\n+)/)
            .map((item) => item.trim())
            .filter(Boolean),
        }))
        .filter((line) => line.category.length > 0 && line.items.length > 0)
        .map((line) => [line.category, line.items]);

      if (categoryLines.length > 0) {
        meta.category_lines = categoryLines;
      } else {
        delete meta.category_lines;
      }
    }

    if (value.kind === SectionKind.Experience) {
      const entries = (value.experiences ?? [])
        .map((entry) => {
          const formattedBullets = serialiseBullets(entry.bullets);
          const clean = {
            role: entry.role.trim(),
            company: entry.company.trim(),
            location: entry.location.trim(),
            date_range: entry.date_range.trim(),
            bullets: formattedBullets,
          };
          const hasContent =
            clean.role ||
            clean.company ||
            clean.location ||
            clean.date_range ||
            formattedBullets.length > 0;
          return hasContent ? clean : null;
        })
        .filter((entry): entry is ExperienceEntry => entry !== null);

      if (entries.length > 0) {
        meta.entries = entries;
      } else {
        delete meta.entries;
      }
    }

    return {
      title: value.title,
      paragraphs,
      bullets,
      meta,
    };
  });
}
