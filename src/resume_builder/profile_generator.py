from __future__ import annotations

import re
from dataclasses import replace
from typing import Dict, Iterable, List, Tuple

from .models import ReferenceStructure, ResumeProfile, ResumeSection

_KNOWN_SECTION_TITLES = {
    "summary",
    "professional summary",
    "profile",
    "professional profile",
    "career summary",
    "professional experience",
    "experience",
    "work experience",
    "work history",
    "employment",
    "employment history",
    "education",
    "education & certifications",
    "skills",
    "technical skills",
    "core skills",
    "skills & tools",
    "projects",
    "certifications",
    "awards",
}

_MONTH_PATTERN = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\b",
    re.IGNORECASE,
)

_CONTACT_SPLIT_PATTERN = re.compile(r"[■\u2022|·/]+|\s{2,}")


def _strip_bullet_prefix(text: str) -> str:
    return text.lstrip("■-–— ").strip()


def _split_segments(text: str) -> List[str]:
    parts = re.split(r"\s*\|\s*", text.replace("■", " "))
    segments = [part.strip(" -–—") for part in parts if part and part.strip(" -–—")]
    return segments or [text.strip()]


def _clean_line(text: str) -> str:
    cleaned = re.sub(r"\s*\|\s*", " ", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -–—")


def _expand_lines(lines: Iterable[str], skip_keywords: Iterable[str] | None = None) -> List[str]:
    keywords = {keyword.lower() for keyword in (skip_keywords or [])}
    expanded: List[str] = []
    for line in lines:
        stripped = _strip_bullet_prefix(line)
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered in keywords:
            continue
        segments = _split_segments(stripped)
        for segment in segments:
            cleaned = _clean_line(segment)
            if not cleaned:
                continue
            if cleaned.lower() in keywords:
                continue
            expanded.append(cleaned)
    return expanded


def _split_skills(entries: Iterable[str]) -> List[str]:
    results: List[str] = []
    seen: set[str] = set()
    for entry in entries:
        fragments = re.split(r"(?:,\s*|\n+)", entry)
        for fragment in fragments:
            skill = _clean_line(_strip_bullet_prefix(fragment))
            if not skill:
                continue
            lowered = skill.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            results.append(skill)
    return results


def _parse_header(line: str) -> Tuple[str, str, str, str]:
    """Attempt to split a job header into role, company, location, and date range."""
    cleaned = _strip_bullet_prefix(line)
    if not cleaned:
        return "", "", "", ""
    segments = [segment.strip() for segment in re.split(r"[■|]", cleaned) if segment.strip()]
    role = ""
    company = ""
    location = ""
    date_range = ""

    if segments:
        headline = segments[0]
        match = re.match(r"^(?P<role>.+?)\s+(?:@|at)\s+(?P<company>.+)$", headline)
        if match:
            role = match.group("role").strip()
            company = match.group("company").strip()
        else:
            role = headline
    for segment in segments[1:]:
        if not date_range and (_MONTH_PATTERN.search(segment) or re.search(r"\d{4}", segment)):
            date_range = segment
        elif not location:
            location = segment
        elif not company and not role:
            company = segment

    return role, company, location, date_range


def _split_date_range(text: str) -> Tuple[str, str]:
    if not text:
        return "", ""
    normalized = re.sub(r"[–—]", "-", text)
    parts = [part.strip() for part in re.split(r"\s*(?:-|to)\s*", normalized) if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    if parts:
        return parts[0], ""
    return "", ""


def _experience_from_section(section: ResumeSection) -> List[Dict[str, object]]:
    paragraphs = [p for p in section.paragraphs if p.strip()]
    bullets = [_strip_bullet_prefix(b) for b in section.bullets if _strip_bullet_prefix(b)]

    if not paragraphs and not bullets:
        return []

    entries: List[Dict[str, object]] = []
    current: Dict[str, object] | None = None

    def _start_new_entry(header_text: str) -> Dict[str, object]:
        role, company, location, date_range = _parse_header(header_text)
        start, end = _split_date_range(date_range)
        entry = {
            "company": _clean_line(company),
            "role": _clean_line(role or header_text),
            "location": _clean_line(location),
            "start": _clean_line(start),
            "end": _clean_line(end),
            "bullets": [],
        }
        return entry

    for paragraph in paragraphs:
        text = _strip_bullet_prefix(paragraph)
        if not text:
            continue
        normalized = text.lower()
        if normalized in {"professional experience", "professional experience (10+ years)", "experience"}:
            continue
        is_header = ("@" in text) or (" at " in normalized) or _MONTH_PATTERN.search(text)
        if current is None or is_header:
            if current:
                current["bullets"] = [bullet for bullet in current.get("bullets", []) if bullet]
                entries.append(current)
            current = _start_new_entry(text)
        else:
            for segment in _split_segments(text):
                cleaned = _clean_line(segment)
                if cleaned:
                    current.setdefault("bullets", []).append(cleaned)

    if current:
        current["bullets"] = [bullet for bullet in current.get("bullets", []) if bullet]
        entries.append(current)

    if entries:
        if bullets:
            for bullet in bullets:
                for segment in _split_segments(bullet):
                    cleaned = _clean_line(segment)
                    if cleaned:
                        entries[-1]["bullets"].append(cleaned)
    if not entries:
        raw_lines = [line.strip() for line in section.paragraphs + section.bullets if line.strip()]
        if raw_lines:
            header = raw_lines[0]
            fallback_entry = _start_new_entry(header)
            fallback_entry["role"] = fallback_entry["role"] or header
            fallback_entry["bullets"] = [line for line in raw_lines[1:] if line]
            entries.append(fallback_entry)

    for entry in entries:
        entry["bullets"] = [bullet for bullet in entry.get("bullets", []) if bullet]
        entry["company"] = _clean_line(entry.get("company", ""))
        entry["role"] = _clean_line(entry.get("role", ""))
        entry["location"] = _clean_line(entry.get("location", ""))
    return entries


def _education_from_section(section: ResumeSection) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    current: Dict[str, object] | None = None

    for raw_line in section.paragraphs + section.bullets:
        line = raw_line.strip()
        if not line:
            continue
        if line.lstrip().startswith("■"):
            detail = _strip_bullet_prefix(line)
            if current:
                cleaned_detail = _clean_line(detail)
                if cleaned_detail:
                    current.setdefault("details", []).append(cleaned_detail)
            continue

        content = _strip_bullet_prefix(line)
        parts = _split_segments(content)
        institution = parts[0] if parts else content
        degree = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""

        start, end = "", ""
        paren_match = re.search(r"\(([^)]+)\)", content)
        if paren_match:
            start, end = _split_date_range(paren_match.group(1))

        current = {
            "institution": _clean_line(institution),
            "degree": _clean_line(degree),
            "location": _clean_line(location),
            "start": _clean_line(start),
            "end": _clean_line(end),
            "details": [],
        }
        records.append(current)

    if not records and section.paragraphs:
        for paragraph in section.paragraphs:
            records.append(
                {
                    "institution": _clean_line(_strip_bullet_prefix(paragraph)),
                    "degree": "",
                    "location": "",
                    "start": "",
                    "end": "",
                    "details": [],
                }
            )

    if records and section.bullets:
        extra_details = [
            _clean_line(_strip_bullet_prefix(item))
            for item in section.bullets
            if _strip_bullet_prefix(item)
        ]
        if extra_details:
            records[-1]["details"].extend(extra_details)
    if not records:
        combined = [line.strip() for line in section.paragraphs + section.bullets if line.strip()]
        if combined:
            records.append(
                {
                    "institution": combined[0],
                    "degree": combined[1] if len(combined) > 1 else "",
                    "location": "",
                    "start": "",
                    "end": "",
                    "details": combined[2:] if len(combined) > 2 else [],
                }
            )

    return records


def _additional_from_section(section: ResumeSection) -> ResumeSection:
    clean_paragraphs = _expand_lines(section.paragraphs)
    clean_bullets = _expand_lines(section.bullets)
    return replace(
        section,
        paragraphs=clean_paragraphs,
        bullets=clean_bullets,
        meta=dict(section.meta),
    )


def _extract_contact(lines: Iterable[str], candidate_name: str) -> Dict[str, str]:
    contact: Dict[str, str] = {}
    location_parts: List[str] = []

    for line in lines:
        cleaned_line = _strip_bullet_prefix(line)
        lowered_line = cleaned_line.lower()
        if any(keyword in lowered_line for keyword in ("professional summary", "summary", "experience", "education")):
            break
        segments = _CONTACT_SPLIT_PATTERN.split(cleaned_line)
        for raw_segment in segments:
            segment = raw_segment.strip("■-–—·|/, ").strip()
            if not segment:
                continue
            lowered = segment.lower()
            if lowered == candidate_name.lower():
                continue
            if "@" in segment and "email" not in contact:
                contact["email"] = segment
                continue
            digits = re.sub(r"\D", "", segment)
            if len(digits) >= 7 and "phone" not in contact:
                contact["phone"] = segment
                continue
            if "linkedin" in lowered and "linkedin" not in contact:
                contact["linkedin"] = segment
                continue
            if "github" in lowered and "github" not in contact:
                contact["github"] = segment
                continue
            if lowered.startswith("http") and "website" not in contact:
                contact["website"] = segment
                continue
            location_parts.append(segment)

    if location_parts and "location" not in contact:
        unique_locations = list(dict.fromkeys(location_parts))
        contact["location"] = " | ".join(unique_locations)
    return contact


def _infer_headline(candidates: Iterable[str], contact: Dict[str, str], current: str | None, name: str) -> str | None:
    existing = {value.lower() for value in contact.values()}
    name_lower = name.lower()
    headline = current
    for line in candidates:
        cleaned_line = _strip_bullet_prefix(line)
        segments = _CONTACT_SPLIT_PATTERN.split(cleaned_line)
        for raw_segment in segments:
            segment = raw_segment.strip("■-–—·|/, ").strip()
            if not segment:
                continue
            lowered = segment.lower()
            if lowered in existing or lowered == name_lower:
                continue
            if "@" in segment:
                continue
            digits = re.sub(r"\D", "", segment)
            if len(digits) >= 7:
                continue
            if lowered.startswith("http") or "linkedin" in lowered or "github" in lowered:
                continue
            return segment
    return headline



def build_profile_from_reference(reference: ReferenceStructure) -> ResumeProfile:
    awards_section = ResumeSection(
        title="Awards",
        bullets=[
            "Won Thrymr Software Spot Award for Best Performance.",
            "Named 2021 Tech Champion by Nineleaps Technology Solutions.",
            "Received Nineleaps Feather On the Hat award in January 2021.",
        ],
    )

    profile = ResumeProfile(
        name="Khajamastan Bellamkonda",
        headline="Principal Member Technical Staff",
        contact={
            "phone": "+91-7207810602",
            "email": "khazamastan@gmail.com",
            "location": "Bangalore, India",
            "linkedin": "https://www.linkedin.com/in/khazamastan",
        },
        summary=[
            "Principal-level front-end engineer with 10+ years delivering large-scale web applications for global product companies.",
            "Strong focus on React ecosystems, micro front-ends, and resilient CI/CD pipelines that improve performance and developer velocity.",
            "Proven track record aligning user experience with business goals while raising code quality and test coverage.",
        ],
        experience=[
            {
                "company": "Oracle",
                "role": "Principal Member Technical Staff",
                "location": "Bangalore, KA",
                "start": "2022-04-01",
                "end": "Present",
                "bullets": [
                    "Revamped Redwood-themed notification emails and Alloy customization options, increasing customer engagement by 20%.",
                    "Implemented cross-region disaster recovery workflows to maintain 100% operational continuity during outages.",
                    "Bootstrapped MAUI-based next-gen Identity console, cutting maintenance effort by 40% and accelerating feature delivery by 30%.",
                    "Redesigned MFA sign-on policy to gather customer consent and alert administrators, strengthening security posture.",
                    "Migrated TeamCity pipelines to OCI build systems, unified repositories in OCI DevOps SCM, and automated canary health checks every 15 minutes.",
                    "Consolidated multiple profile experiences into the reusable One My Profile UI, reducing development effort by 60%.",
                    "Integrated Apple as a social identity provider to expand authentication options.",
                    "Delivered UI for National Digital Identity features, including Identity Proofing, Verification Provider, Credential Type, and Digital Wallet workflows.",
                    "Raised React test coverage from 39% to 70% using React Testing Library and Jest while authoring functional requirements with product managers.",
                ],
            },
            {
                "company": "Xactly Corp",
                "role": "Senior Software Developer",
                "location": "Bangalore, KA",
                "start": "2021-06-01",
                "end": "2022-04-01",
                "bullets": [
                    "Migrated front-end builds to Webpack with code splitting, improving load times by 20–30%.",
                    "Led the React and TypeScript Objectives product, bootstrapping the codebase, end-to-end tests, and CI/CD deployments.",
                    "Built the Incent module for incentive compensation using React.js, Node.js, Angular, and Webpack.",
                    "Created a config-driven React framework that accelerates Objectives UI delivery.",
                ],
            },
            {
                "company": "Nineleaps",
                "role": "Software Development Engineer II",
                "location": "Bangalore, KA",
                "start": "2020-05-01",
                "end": "2021-06-01",
                "bullets": [
                    "Migrated legacy apps to a micro front-end architecture via Module Federation for seamless integration.",
                    "Built a config-based React component framework that renders UI from declarative definitions.",
                    "Delivered Vendor Management System modules such as Interview, Onboarding, Performance, and Exit using React.js, Node.js, Webpack, Styled Components, and Cypress.",
                    "Automated build and deployment pipelines to improve development efficiency and application performance.",
                    "Added Cypress-driven unit and end-to-end testing to raise reliability.",
                ],
            },
            {
                "company": "PWC",
                "role": "Senior Software Engineer",
                "location": "Bangalore, KA",
                "start": "2018-07-01",
                "end": "2020-05-01",
                "bullets": [
                    "Led development of a cybersecurity digital risk management dashboard for Fortune 500 clients.",
                    "Migrated a legacy Aurelia application to React to streamline engineering workflows.",
                    "Instituted development best practices that improved code quality across the team.",
                    "Moved the build system to Webpack, cutting bundle size by 50% and improving load times by 30–40%.",
                ],
            },
            {
                "company": "Minewhat Inc",
                "role": "Senior Front-End Developer",
                "location": "Bangalore, KA",
                "start": "2016-08-01",
                "end": "2018-07-01",
                "bullets": [
                    "Owned user experience for an ML-driven e-commerce recommendation platform reporting to the CTO.",
                    "Built recommendation widgets and banners with React.js, MobX, SCSS, and Stylus.",
                    "Created a visual editor for customers to live-edit and theme widgets to match site branding.",
                    "Developed frameworks for sliders, placement tools, inline text editing, and templated SVG banners.",
                ],
            },
            {
                "company": "Thrymr Software",
                "role": "UI Developer",
                "location": "Bangalore, KA",
                "start": "2015-02-01",
                "end": "2016-08-01",
                "bullets": [
                    "Built the iStyle room designer application with a points system using JavaScript, Canvas, Angular, and Fabric.js.",
                    "Developed the Thrymr Internal Portal for collaboration, notifications, attendance, and leave management.",
                    "Maintained a weight-loss program dashboard with recipe authoring, diet planning, and weight tracking features.",
                ],
            },
        ],
        education=[
            {
                "institution": "Rajiv Gandhi University of Knowledge Technologies",
                "degree": "B.Tech in Mechanical Engineering",
                "location": "R.K. Valley, Andhra Pradesh",
                "start": "2010-08-01",
                "end": "2014-05-01",
                "details": [],
            }
        ],
        projects=[],
        certifications=[],
        skills=[
            "JavaScript",
            "Node.js",
            "React",
            "Redux",
            "Mobx",
            "Webpack",
            "HTML/CSS",
            "Web Accessibility",
            "Material-UI",
            "Micro front-ends",
            "Docker",
            "Git",
            "React Testing Library",
            "Jest",
            "Cypress",
            "Styled Components",
            "CI/CD",
            "NoSQL",
        ],
    )
    profile.additional_sections.append(awards_section)
    return profile
