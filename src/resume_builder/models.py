from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Theme:
    """Visual styling extracted from the reference resume."""

    body_font: str = "Helvetica"
    body_size: float = 10.0
    heading_font: str = "Helvetica-Bold"
    heading_size: float = 14.0
    primary_color: str = "#000000"
    accent_color: str = "#1a1a1a"
    line_height: float = 1.2
    margin_left: float = 50
    margin_right: float = 50
    margin_top: float = 60
    margin_bottom: float = 60
    page_width: float = 595.0
    page_height: float = 842.0
    template: str = "standard"


@dataclass
class ResumeSection:
    """Logical resume section with paragraphs or bullet points."""

    title: str
    bullets: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    meta: Dict[str, str] = field(default_factory=dict)


@dataclass
class ResumeProfile:
    """Structured representation of the candidate profile."""

    name: str
    headline: Optional[str] = None
    contact: Dict[str, str] = field(default_factory=dict)
    summary: List[str] = field(default_factory=list)
    experience: List[Dict[str, object]] = field(default_factory=list)
    education: List[Dict[str, object]] = field(default_factory=list)
    projects: List[Dict[str, object]] = field(default_factory=list)
    certifications: List[Dict[str, object]] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    additional_sections: List[ResumeSection] = field(default_factory=list)


@dataclass
class ReferenceStructure:
    """Combination of theme and sections extracted from the reference PDF."""

    theme: Theme
    sections: List[ResumeSection]


@dataclass
class SkillInsights:
    """Skills extracted from the Job Description."""

    mandatory: List[str] = field(default_factory=list)
    preferred: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


@dataclass
class ResumeDocument:
    """Final resume document to render."""

    profile: ResumeProfile
    sections: List[ResumeSection]
    theme: Theme
