from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .models import ResumeProfile, ResumeSection

_SECTION_ALIASES = {
    "professional summary": "Professional Summary",
    "summary": "Professional Summary",
    "profile summary": "Professional Summary",
    "career summary": "Professional Summary",
    "executive summary": "Professional Summary",
    "career objective": "Professional Summary",
    "objective": "Professional Summary",
    "about": "Professional Summary",
    "about me": "Professional Summary",
    "technical skills": "Technical Skills",
    "skills": "Technical Skills",
    "key skills": "Technical Skills",
    "core skills": "Technical Skills",
    "core competencies": "Technical Skills",
    "competencies": "Technical Skills",
    "technical expertise": "Technical Skills",
    "technologies": "Technical Skills",
    "tech stack": "Technical Skills",
    "professional experience": "Professional Experience",
    "experience": "Professional Experience",
    "work experience": "Professional Experience",
    "employment history": "Professional Experience",
    "work history": "Professional Experience",
    "career history": "Professional Experience",
    "professional background": "Professional Experience",
    "education": "Education",
    "academic background": "Education",
    "academic qualifications": "Education",
    "qualifications": "Education",
    "qualification": "Education",
    "education & awards": "Education & Awards",
    "education and awards": "Education & Awards",
    "awards": "Awards",
    "honors": "Awards",
    "honours": "Awards",
    "achievements": "Awards",
    "accomplishments": "Awards",
    "recognitions": "Awards",
    "honors & awards": "Awards",
    "honors and awards": "Awards",
    "honours & awards": "Awards",
    "honours and awards": "Awards",
    "projects": "Projects",
    "certifications": "Certifications",
    "licenses & certifications": "Certifications",
    "licenses and certifications": "Certifications",
    "licences & certifications": "Certifications",
    "licences and certifications": "Certifications",
}
_INSTITUTION_HINT_PATTERN = re.compile(
    r"\b(university|college|school|institute|academy|polytechnic|iit|nit)\b",
    re.IGNORECASE,
)
_MONTH_PATTERN = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.IGNORECASE,
)
_ROLE_HINT_PATTERN = re.compile(
    r"\b(engineer|developer|architect|manager|lead|staff|intern|consultant|analyst|"
    r"director|principal|designer|specialist|frontend|front-end|full[ -]?stack|devops|qa|sde)\b",
    re.IGNORECASE,
)
_COMPANY_HINT_PATTERN = re.compile(
    r"\b(inc|corp|corporation|llc|ltd|limited|plc|technologies|technology|solutions|systems|"
    r"labs|group|software|university|college|school)\b",
    re.IGNORECASE,
)
_DEGREE_HINT_PATTERN = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?e\.?|m\.?\s?tech|m\.?\s?e\.?|bachelor|master|mba|bsc|msc|phd|doctorate|diploma)\b",
    re.IGNORECASE,
)
_AWARD_HINT_PATTERN = re.compile(
    r"\b(award|awards|honor|honour|champion|recognition|recognized|accomplishment|spot award|feather)\b",
    re.IGNORECASE,
)
_LIST_DELIMITER_PATTERN = re.compile(r"\s*(?:\||•|·|●|▪|◦)\s*")
_SKILL_SPLIT_PATTERN = re.compile(r"\s*(?:•|·|●|▪|◦|;|,)\s*")
_SKILL_LABEL_PATTERN = re.compile(
    r"\b(skills?|technolog(?:y|ies)|tools?|frameworks?|languages?|libraries|expertise|competenc(?:y|ies))\b",
    re.IGNORECASE,
)
_COMMON_ACTION_VERB_PATTERN = re.compile(
    r"\b(accelerated|automated|built|created|decreased|delivered|designed|developed|elevated|enabled|enhanced|"
    r"implemented|improved|increased|integrated|led|managed|maintained|migrated|optimized|owned|raised|reduced|"
    r"resolved|revamped|validated)\b",
    re.IGNORECASE,
)
_AUTO_SKILL_CATEGORY_RULES: List[tuple[str, re.Pattern[str]]] = [
    (
        "Frontend",
        re.compile(
            r"\b(react|next\.?js|angular|vue|svelte|html|css|scss|sass|styled components|"
            r"redux|mobx|context|javascript|typescript|webpack|vite|module federation)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Backend",
        re.compile(
            r"\b(node\.?js|express|nestjs|spring|django|flask|fastapi|graphql|rest|api|websocket)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Languages",
        re.compile(r"\b(javascript|typescript|python|java|go|c\+\+|c#|ruby|php|kotlin|swift|sql)\b", re.IGNORECASE),
    ),
    (
        "Testing",
        re.compile(r"\b(jest|mocha|chai|enzyme|cypress|playwright|selenium|testing library|pytest|unit test)\b", re.IGNORECASE),
    ),
    (
        "DevOps & Tools",
        re.compile(r"\b(git|jira|jenkins|ci\/cd|docker|kubernetes|maven|npm|yarn|pnpm)\b", re.IGNORECASE),
    ),
    (
        "Cloud",
        re.compile(r"\b(aws|azure|gcp|oci|cloud|lambda)\b", re.IGNORECASE),
    ),
    (
        "Data & Databases",
        re.compile(r"\b(sql|postgres|mysql|mongodb|redis|database|nosql)\b", re.IGNORECASE),
    ),
    (
        "AI Tools",
        re.compile(r"\b(ai|copilot|codex|cline|chatgpt|llm|prompt)\b", re.IGNORECASE),
    ),
]
_NOISE_LINE_PATTERN = re.compile(
    r"^(rewrite|this section is empty and won[’']t appear in your resume\.?)$",
    re.IGNORECASE,
)
_TENURE_SUFFIX_PATTERN = re.compile(
    r"\s*\((?:[^)]*\b(?:yr|yrs|year|years|mo|mos|month|months)\b[^)]*)\)\s*$",
    re.IGNORECASE,
)
_EXPERIENCE_COMPANY_PREFIX_PATTERN = re.compile(r"^(?:company|organization|organisation|employer)\s*:\s*", re.IGNORECASE)
_EXPERIENCE_ROLE_PREFIX_PATTERN = re.compile(r"^(?:role|title|position)\s*:\s*", re.IGNORECASE)
_EXPERIENCE_LOCATION_PREFIX_PATTERN = re.compile(r"^(?:location|loc)\s*:\s*", re.IGNORECASE)
_EXPERIENCE_DATE_PREFIX_PATTERN = re.compile(
    r"^(?:timeline|duration|date|dates|tenure|period)\s*:\s*",
    re.IGNORECASE,
)
_PAGE_FOOTER_PATTERN = re.compile(r"^.+\s*-\s*page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-()]{6,}")
_INVISIBLE_CHARS_PATTERN = re.compile(
    r"[\u00ad\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060\u2066-\u2069\ufeff]"
)
_HEADING_SIMPLIFY_PATTERN = re.compile(r"[^a-z0-9]+")
_HEADING_TRIM_TOKENS = {
    "section",
    "sections",
    "details",
    "information",
    "info",
}
_HEADING_KEYWORDS = {
    "professional",
    "summary",
    "profile",
    "career",
    "executive",
    "about",
    "objective",
    "objectives",
    "highlights",
    "overview",
    "objective",
    "technical",
    "skills",
    "skill",
    "core",
    "key",
    "competencies",
    "competency",
    "expertise",
    "technologies",
    "technology",
    "tools",
    "frameworks",
    "languages",
    "stack",
    "experience",
    "work",
    "employment",
    "background",
    "career",
    "history",
    "employment",
    "education",
    "academic",
    "qualification",
    "qualifications",
    "academics",
    "academic",
    "awards",
    "award",
    "achievements",
    "accomplishments",
    "recognitions",
    "honors",
    "honour",
    "honours",
    "projects",
    "project",
    "certifications",
    "certification",
    "licenses",
    "license",
    "licences",
    "licence",
    "and",
}


def _normalize_line(value: str) -> str:
    text = (value or "").replace("\u00a0", " ")
    text = _INVISIBLE_CHARS_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", text.strip())


def _strip_bullet_prefix(value: str) -> str:
    cleaned = re.sub(r"^[\-•■]+\s*", "", _normalize_line(value))
    cleaned = re.sub(r"\s*(?:•|·|●|▪|◦|\|)\s*$", "", cleaned)
    return _normalize_line(cleaned)


def _section_heading(value: str) -> str | None:
    normalized = _normalize_line(value).lower()
    if not normalized:
        return None

    normalized = re.sub(r"^\d+[\).\s\-–—]*", "", normalized)
    normalized = normalized.rstrip(":")
    normalized = normalized.replace("＆", "&")
    normalized = re.sub(r"\s+", " ", normalized).strip(" -–—|")
    normalized_tokens = [token for token in re.findall(r"[a-z0-9]+", normalized)]
    while normalized_tokens and normalized_tokens[-1] in _HEADING_TRIM_TOKENS:
        normalized_tokens.pop()
    if normalized_tokens:
        normalized = " ".join(normalized_tokens)
    else:
        normalized = ""

    direct = _SECTION_ALIASES.get(normalized)
    if direct:
        return direct

    simplified = _HEADING_SIMPLIFY_PATTERN.sub(" ", normalized).strip()
    if not simplified:
        return None

    for alias, target in _SECTION_ALIASES.items():
        alias_simplified = _HEADING_SIMPLIFY_PATTERN.sub(" ", alias).strip()
        if simplified == alias_simplified:
            return target

    tokens = [token for token in re.findall(r"[a-z]+", simplified) if token not in _HEADING_TRIM_TOKENS]
    if not tokens or len(tokens) > 6:
        return None
    if any(token not in _HEADING_KEYWORDS for token in tokens):
        return None
    if len(normalized) > 80:
        return None
    if normalized.endswith("."):
        return None
    if "|" in normalized or "@" in normalized:
        return None
    if ":" in normalized and not normalized.endswith(":"):
        return None

    if "education" in simplified and "award" in simplified:
        return "Education & Awards"
    if "honor" in simplified and "award" in simplified:
        return "Awards"
    if "award" in simplified:
        return "Awards"
    if "license" in simplified and "certification" in simplified:
        return "Certifications"
    if "certification" in simplified:
        return "Certifications"
    if "skill" in simplified:
        return "Technical Skills"
    if "experience" in simplified or "employment" in simplified:
        return "Professional Experience"
    if "summary" in simplified or "objective" in simplified or simplified == "profile":
        return "Professional Summary"
    if "education" in simplified:
        return "Education"

    return None


def _is_noise_line(value: str) -> bool:
    normalized = _normalize_line(value)
    if not normalized:
        return False
    if _NOISE_LINE_PATTERN.fullmatch(normalized):
        return True
    return bool(_PAGE_FOOTER_PATTERN.fullmatch(normalized))


def _strip_prefixed_label(value: str, pattern: re.Pattern[str]) -> str:
    candidate = _normalize_line(value)
    if not candidate:
        return ""
    return _normalize_line(pattern.sub("", candidate, count=1))


def _clean_date_range_text(value: str) -> str:
    candidate = _normalize_line(value)
    if not candidate:
        return ""
    candidate = _strip_prefixed_label(candidate, _EXPERIENCE_DATE_PREFIX_PATTERN)
    return _normalize_line(_TENURE_SUFFIX_PATTERN.sub("", candidate))


def _paragraphs_from_lines(lines: List[str]) -> List[str]:
    paragraphs: List[str] = []
    current: List[str] = []
    for raw in lines:
        line = _strip_bullet_prefix(raw)
        if _is_noise_line(line):
            continue
        if not line:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current).strip())
    return [paragraph for paragraph in paragraphs if paragraph]


def _split_date_range(value: str) -> Tuple[str, str]:
    normalized = _normalize_line(value)
    if not normalized:
        return "", ""
    parts = [part.strip() for part in re.split(r"\s*(?:-|–|—|to)\s*", normalized) if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if parts:
        return parts[0], ""
    return "", ""


def _looks_like_institution(value: str) -> bool:
    return bool(_INSTITUTION_HINT_PATTERN.search(_normalize_line(value)))


def _looks_like_year_text(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    if re.fullmatch(r"\d{4}", candidate):
        return True
    if re.fullmatch(r"\d{4}\s*[-–/]\s*\d{2,4}", candidate):
        return True
    lowered = candidate.lower()
    return "present" in lowered or "current" in lowered


def _looks_like_grade_text(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    lowered = candidate.lower()
    if any(token in lowered for token in ("grade", "cgpa", "gpa", "marks", "score", "percentage", "percent")):
        return True
    return bool(re.search(r"\d", candidate) and "/" in candidate)


def _looks_like_date_range_text(value: str) -> bool:
    candidate = _clean_date_range_text(value)
    if not candidate:
        return False

    if _looks_like_year_text(candidate):
        return True

    lowered = candidate.lower()
    has_year = bool(re.search(r"\b\d{4}\b", candidate))
    has_month = bool(_MONTH_PATTERN.search(candidate))
    has_range_separator = bool(re.search(r"(?:-|–|—|/|\bto\b)", lowered))
    if (has_month and has_year) or ("present" in lowered) or ("current" in lowered):
        return True
    return has_year and has_range_separator


def _looks_like_location_text(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    lowered = candidate.lower()
    if "linkedin.com" in lowered or lowered.startswith("http"):
        return False
    if "@" in candidate:
        return False
    if _PHONE_PATTERN.search(candidate):
        return False
    if len(candidate.split()) > 12:
        return False
    return "," in candidate


def _looks_like_role_text(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    if len(candidate.split()) > 12:
        return False
    return bool(_ROLE_HINT_PATTERN.search(candidate))


def _looks_like_company_text(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    lowered = candidate.lower()
    if lowered in {"oracle", "pwc", "google", "meta", "amazon", "microsoft"}:
        return True
    if _COMPANY_HINT_PATTERN.search(candidate):
        return True
    if candidate.isupper() and len(candidate) <= 8:
        return True
    return False


def _looks_like_entry_title_text(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    if _is_noise_line(candidate):
        return False
    if _looks_like_date_range_text(candidate):
        return False
    if ":" in candidate:
        return False
    if candidate.endswith("."):
        return False
    if len(candidate.split()) > 12:
        return False
    return True


def _looks_like_degree_text(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    return bool(_DEGREE_HINT_PATTERN.search(candidate))


def _looks_like_award_line(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    if _section_heading(candidate) == "Awards":
        return False
    if _looks_like_date_range_text(candidate):
        return False
    return bool(_AWARD_HINT_PATTERN.search(candidate))


def _looks_like_skill_item(value: str) -> bool:
    candidate = _normalize_line(value)
    if not candidate:
        return False
    if not re.search(r"[A-Za-z0-9]", candidate):
        return False
    lowered = candidate.lower()
    if _is_noise_line(candidate):
        return False
    if _section_heading(candidate):
        return False
    if candidate.endswith("."):
        return False
    if "@" in candidate or "linkedin.com" in lowered or lowered.startswith("http"):
        return False
    if _looks_like_date_range_text(candidate):
        return False
    if _looks_like_award_line(candidate):
        return False
    if _looks_like_degree_text(candidate):
        return False
    if _COMMON_ACTION_VERB_PATTERN.search(candidate):
        return False
    if " by " in lowered:
        return False
    if len(candidate.split()) > 7:
        return False
    if re.search(r"\b\d{4}\b", candidate):
        return False
    return True


def _infer_skill_lines(lines: List[str]) -> List[str]:
    inferred: List[str] = []
    for raw in lines:
        line = _normalize_line(raw)
        if not line or _is_noise_line(line):
            continue
        if _section_heading(line):
            continue
        lowered = line.lower()
        if "linkedin.com" in lowered or lowered.startswith("http") or "@" in line:
            continue
        if _looks_like_date_range_text(line):
            continue

        if ":" in line:
            label, _ = line.split(":", 1)
            if _SKILL_LABEL_PATTERN.search(label):
                inferred.append(line)
                continue

        if re.search(r"\s{2,}", raw or ""):
            inferred.append(str(raw))
            continue
        if re.search(r"[;,]", line) and not _COMMON_ACTION_VERB_PATTERN.search(line) and not line.endswith("."):
            inferred.append(line)
            continue
    return inferred


def _infer_education_lines(lines: List[str]) -> List[str]:
    inferred: List[str] = []
    normalized = [_normalize_line(raw) for raw in lines]
    index = 0
    while index < len(normalized):
        line = normalized[index]
        if not line or _is_noise_line(line):
            index += 1
            continue
        if _section_heading(line):
            index += 1
            continue
        lowered = line.lower()
        if "linkedin.com" in lowered or lowered.startswith("http") or "@" in line:
            index += 1
            continue

        next_line = normalized[index + 1] if index + 1 < len(normalized) else ""
        if _looks_like_institution(line):
            inferred.append(line)
            if next_line and _looks_like_degree_text(next_line):
                inferred.append(next_line)
                index += 2
                continue
            index += 1
            continue

        if _looks_like_degree_text(line) and next_line and _looks_like_institution(next_line):
            inferred.append(next_line)
            inferred.append(line)
            index += 2
            continue

        if "|" in line:
            parts = [_normalize_line(part) for part in line.split("|") if _normalize_line(part)]
            if parts and (_looks_like_institution(parts[0]) or any(_looks_like_degree_text(part) for part in parts)):
                inferred.append(" | ".join(parts))

        index += 1

    deduped: List[str] = []
    seen: set[str] = set()
    for line in inferred:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    return deduped


def _infer_awards_lines(lines: List[str]) -> List[str]:
    deduped: List[str] = []
    seen: set[str] = set()
    for raw in lines:
        line = _strip_bullet_prefix(raw)
        if not line or _is_noise_line(line):
            continue
        if not _looks_like_award_line(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    return deduped


def _infer_summary_paragraphs(lines: List[str]) -> List[str]:
    paragraphs = _paragraphs_from_lines(lines)
    inferred: List[str] = []
    for paragraph in paragraphs:
        line = _normalize_line(paragraph)
        if not line:
            continue
        lowered = line.lower()
        word_count = len(line.split())
        if word_count < 12:
            continue
        if _section_heading(line):
            continue
        if _looks_like_date_range_text(line):
            continue
        if "linkedin.com" in lowered or lowered.startswith("http") or "@" in line:
            continue
        if _looks_like_award_line(line):
            continue
        if _SKILL_LABEL_PATTERN.search(line) and word_count < 20:
            continue
        inferred.append(line)
        if len(inferred) >= 2:
            break
    return inferred


def _parse_company_role_line(value: str) -> tuple[str, str] | None:
    if "|" not in value:
        return None
    parts = [_normalize_line(part) for part in value.split("|") if _normalize_line(part)]
    if len(parts) < 2:
        return None
    company, role = parts[0], parts[1]
    if _looks_like_date_range_text(role):
        return None
    if _looks_like_degree_text(company) and _looks_like_institution(role):
        return None
    if _looks_like_institution(company) and _looks_like_degree_text(role):
        return None
    if _looks_like_award_line(company) or _looks_like_award_line(role):
        return None
    return company, role


def _parse_company_role_date_line(value: str) -> tuple[str, str, str, str] | None:
    if "|" not in value:
        return None
    parts = [_normalize_line(part) for part in value.split("|") if _normalize_line(part)]
    if len(parts) < 3:
        return None

    date_range = _clean_date_range_text(parts[-1])
    if not _looks_like_date_range_text(date_range):
        return None

    leading_parts = parts[:-1]
    location = ""
    normalized_location = _strip_prefixed_label(leading_parts[-1], _EXPERIENCE_LOCATION_PREFIX_PATTERN)
    if len(leading_parts) >= 3 and _looks_like_location_text(normalized_location):
        location = normalized_location
        leading_parts = leading_parts[:-1]
    if len(leading_parts) < 2:
        return None

    first = _strip_prefixed_label(leading_parts[0], _EXPERIENCE_COMPANY_PREFIX_PATTERN)
    second = " | ".join(leading_parts[1:]) if len(leading_parts) > 2 else leading_parts[1]
    second = _strip_prefixed_label(second, _EXPERIENCE_ROLE_PREFIX_PATTERN)
    if not first or not second:
        return None
    if _looks_like_date_range_text(first) or _looks_like_date_range_text(second):
        return None
    if _looks_like_award_line(first) or _looks_like_award_line(second):
        return None
    if _looks_like_degree_text(first) and _looks_like_institution(second):
        return None
    if _looks_like_institution(first) and _looks_like_degree_text(second):
        return None

    first_is_company = _looks_like_company_text(first)
    second_is_company = _looks_like_company_text(second)
    first_is_role = _looks_like_role_text(first)
    second_is_role = _looks_like_role_text(second)

    if first_is_company and not second_is_company:
        company, role = first, second
    elif second_is_company and not first_is_company:
        company, role = second, first
    elif first_is_role and not second_is_role:
        role, company = first, second
    elif second_is_role and not first_is_role:
        role, company = second, first
    else:
        company, role = first, second

    return company, role, location, date_range


def _parse_company_role_delimited_line(value: str) -> tuple[str, str] | None:
    candidate = _normalize_line(value)
    if not candidate:
        return None
    if _is_noise_line(candidate):
        return None
    if _looks_like_date_range_text(candidate):
        return None
    if candidate.endswith("."):
        return None
    if len(candidate.split()) > 12:
        return None
    if ":" in candidate:
        return None
    if _COMMON_ACTION_VERB_PATTERN.search(candidate):
        return None

    for delimiter in (",",):
        if delimiter not in candidate:
            continue
        left, right = [part.strip() for part in candidate.split(delimiter, 1)]
        if not left or not right:
            continue
        if not (_looks_like_entry_title_text(left) and _looks_like_entry_title_text(right)):
            continue
        left_is_company = _looks_like_company_text(left)
        right_is_company = _looks_like_company_text(right)
        left_is_role = _looks_like_role_text(left)
        right_is_role = _looks_like_role_text(right)

        if left_is_company and not right_is_company:
            return left, right
        if right_is_company and not left_is_company:
            return right, left
        if left_is_company and right_is_role:
            return left, right
        if right_is_company and left_is_role:
            return right, left

    return None


def _parse_location_date_line(value: str) -> tuple[str, str] | None:
    if "|" not in value:
        return None
    parts = [_normalize_line(part) for part in value.split("|") if _normalize_line(part)]
    if len(parts) < 2:
        return None
    location = parts[0]
    date_range = " | ".join(parts[1:])
    if not _looks_like_date_range_text(date_range):
        return None
    return location, _clean_date_range_text(date_range)


def _parse_role_company_date_triplet(
    first: str,
    second: str,
    third: str,
) -> tuple[str, str, str] | None:
    role_or_company = _normalize_line(first)
    company_or_role = _normalize_line(second)
    date_line = _clean_date_range_text(third)
    if not role_or_company or not company_or_role or not date_line:
        return None
    if not _looks_like_date_range_text(date_line):
        return None
    if not _looks_like_entry_title_text(role_or_company):
        return None
    if not _looks_like_entry_title_text(company_or_role):
        return None

    first_is_company = _looks_like_company_text(role_or_company)
    second_is_company = _looks_like_company_text(company_or_role)
    first_is_role = _looks_like_role_text(role_or_company)
    second_is_role = _looks_like_role_text(company_or_role)

    if first_is_company and not second_is_company:
        company, role = role_or_company, company_or_role
    elif second_is_company and not first_is_company:
        company, role = company_or_role, role_or_company
    elif first_is_role and not second_is_role:
        role, company = role_or_company, company_or_role
    elif second_is_role and not first_is_role:
        role, company = company_or_role, role_or_company
    else:
        # LinkedIn exports usually provide Role first and Company second.
        role, company = role_or_company, company_or_role

    return role, company, date_line


def _extract_header(lines: List[str]) -> tuple[str, Dict[str, str]]:
    non_empty = [
        _normalize_line(line)
        for line in lines
        if _normalize_line(line) and not _is_noise_line(line)
    ]
    if not non_empty:
        return "Candidate", {}

    name = non_empty[0]
    contact: Dict[str, str] = {}

    def assign_field(key: str, value: str) -> None:
        clean = _normalize_line(value)
        if not clean:
            return
        lower = key.lower()
        if any(token in lower for token in ("mobile", "phone")):
            contact["phone"] = clean
            return
        if "email" in lower:
            contact["email"] = clean
            return
        if "location" in lower:
            contact["location"] = clean
            return
        if "linkedin" in lower:
            contact["linkedin"] = clean
            return
        if "available" in lower:
            contact["notice_note"] = f"Available to Join: {clean}"
            return
        if "notice" in lower:
            contact["notice_note"] = clean

    for line in non_empty[1:]:
        segments = [segment.strip() for segment in _LIST_DELIMITER_PATTERN.split(line) if segment.strip()]
        if len(segments) <= 1:
            segments = [segment.strip() for segment in line.split("|") if segment.strip()]
        if not segments:
            continue
        for segment in segments:
            if ":" in segment and "://" not in segment:
                key, value = segment.split(":", 1)
                assign_field(key, value)
                continue

            lowered = segment.lower()
            if "linkedin.com" in lowered:
                contact["linkedin"] = segment
            elif "@" in segment and "email" not in contact:
                contact["email"] = segment
            elif _PHONE_PATTERN.search(segment) and "phone" not in contact:
                contact["phone"] = segment
            elif "location" not in contact and _looks_like_location_text(segment):
                contact["location"] = segment

    return name, contact


def _extract_skills(lines: List[str]) -> tuple[List[tuple[str, List[str]]], List[str]]:
    category_lines: List[tuple[str, List[str]]] = []
    all_skills: List[str] = []

    for raw in lines:
        raw_line = re.sub(r"^[\-•■]+\s*", "", (raw or "").strip())
        line = _normalize_line(raw_line)
        if not line or _is_noise_line(line):
            continue
        if ":" in line:
            category, values = line.split(":", 1)
            category = _normalize_line(category)
            items = [
                _normalize_line(item)
                for item in _SKILL_SPLIT_PATTERN.split(values)
                if _normalize_line(item) and _looks_like_skill_item(item)
            ]
            if category and items:
                category_lines.append((category, items))
                all_skills.extend(items)
                continue
        if re.search(r"[•·●▪◦]", raw_line):
            items = [
                _normalize_line(item)
                for item in _SKILL_SPLIT_PATTERN.split(raw_line)
                if _normalize_line(item) and _looks_like_skill_item(item)
            ]
        elif re.search(r"\s{2,}", raw_line) and not re.search(r"[;,]", raw_line):
            items = [
                _normalize_line(item)
                for item in re.split(r"\s{2,}", raw_line)
                if _normalize_line(item) and _looks_like_skill_item(item)
            ]
        else:
            items = [
                _normalize_line(item)
                for item in _SKILL_SPLIT_PATTERN.split(line)
                if _normalize_line(item) and _looks_like_skill_item(item)
            ]
        if items:
            all_skills.extend(items)

    seen: set[str] = set()
    unique_skills: List[str] = []
    for skill in all_skills:
        lowered = skill.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique_skills.append(skill)
    return category_lines, unique_skills


def _auto_group_skills(skills: List[str]) -> List[tuple[str, List[str]]]:
    grouped: Dict[str, List[str]] = {}
    additional_key = "Additional Skills"
    for raw_skill in skills:
        skill = _normalize_line(raw_skill)
        if not skill:
            continue
        matched_category = additional_key
        for category, pattern in _AUTO_SKILL_CATEGORY_RULES:
            if pattern.search(skill):
                matched_category = category
                break
        grouped.setdefault(matched_category, [])
        if skill not in grouped[matched_category]:
            grouped[matched_category].append(skill)

    ordered: List[tuple[str, List[str]]] = []
    known_order = [category for category, _ in _AUTO_SKILL_CATEGORY_RULES]
    for category in known_order:
        items = grouped.get(category, [])
        if items:
            ordered.append((category, items))
    additional_items = grouped.get(additional_key, [])
    if additional_items:
        ordered.append((additional_key, additional_items))
    return ordered


def _extract_experience(lines: List[str]) -> List[Dict[str, object]]:
    normalized_lines = [
        _normalize_line(line)
        for line in lines
        if _normalize_line(line) and not _is_noise_line(line)
    ]

    entries: List[Dict[str, object]] = []
    current: Dict[str, object] | None = None

    def _new_entry(role: str = "", company: str = "") -> Dict[str, object]:
        return {"role": role, "company": company, "location": "", "date_range": "", "bullets": []}

    def flush_current() -> None:
        nonlocal current
        if current is None:
            return
        role = _normalize_line(str(current.get("role", "")))
        company = _normalize_line(str(current.get("company", "")))
        location = _normalize_line(str(current.get("location", "")))
        date_range = _clean_date_range_text(str(current.get("date_range", "")))
        bullets = [
            _strip_bullet_prefix(str(item))
            for item in (current.get("bullets", []) or [])
            if _strip_bullet_prefix(str(item)) and not _is_noise_line(str(item))
        ]
        if role or company or location or date_range or bullets:
            entries.append(
                {
                    "role": role,
                    "company": company,
                    "location": location,
                    "date_range": date_range,
                    "bullets": bullets,
                }
            )
        current = None

    index = 0
    while index < len(normalized_lines):
        line = normalized_lines[index]
        lowered = line.lower()

        if lowered.startswith("company:"):
            flush_current()
            current = _new_entry()
            value = _normalize_line(line.split(":", 1)[1])
            parts = [_normalize_line(part) for part in value.split("|") if _normalize_line(part)]
            if parts:
                current["company"] = _strip_prefixed_label(parts[0], _EXPERIENCE_COMPANY_PREFIX_PATTERN)
            if len(parts) > 1:
                current["role"] = _strip_prefixed_label(parts[1], _EXPERIENCE_ROLE_PREFIX_PATTERN)
            for part in parts[2:]:
                if not part:
                    continue
                normalized_part = _normalize_line(part)
                normalized_location = _strip_prefixed_label(normalized_part, _EXPERIENCE_LOCATION_PREFIX_PATTERN)
                if normalized_location != normalized_part:
                    if normalized_location and not current.get("location"):
                        current["location"] = normalized_location
                    continue

                if _EXPERIENCE_DATE_PREFIX_PATTERN.match(normalized_part):
                    date_value = _clean_date_range_text(normalized_part)
                    if date_value:
                        current["date_range"] = date_value
                    continue

                if not current.get("date_range") and _looks_like_date_range_text(normalized_part):
                    current["date_range"] = _clean_date_range_text(normalized_part)
                    continue
                if not current.get("location") and _looks_like_location_text(normalized_part):
                    current["location"] = normalized_location
                    continue
            index += 1
            continue

        if lowered.startswith(("role:", "title:", "position:")):
            value = _normalize_line(line.split(":", 1)[1])
            if current is None:
                current = _new_entry()
            if value and not current.get("role"):
                current["role"] = value
            index += 1
            continue

        if lowered.startswith("location:"):
            value = _normalize_line(line.split(":", 1)[1])
            parts = [_normalize_line(part) for part in value.split("|") if _normalize_line(part)]
            if current is None:
                current = _new_entry()
            if parts:
                current["location"] = parts[0]
            if len(parts) > 1:
                current["date_range"] = _clean_date_range_text(parts[1])
            index += 1
            continue

        if lowered.startswith(("duration:", "date:", "tenure:")):
            value = _clean_date_range_text(line.split(":", 1)[1])
            if current is None:
                current = _new_entry()
            current["date_range"] = value
            index += 1
            continue

        company_role_delimited = _parse_company_role_delimited_line(line)
        if company_role_delimited:
            flush_current()
            company, role = company_role_delimited
            current = _new_entry(role=role, company=company)
            index += 1
            continue

        company_role_date = _parse_company_role_date_line(line)
        if company_role_date:
            flush_current()
            company, role, location, date_range = company_role_date
            current = _new_entry(role=role, company=company)
            if location:
                current["location"] = location
            current["date_range"] = date_range
            index += 1
            continue

        if index + 2 < len(normalized_lines):
            triplet = _parse_role_company_date_triplet(
                line,
                normalized_lines[index + 1],
                normalized_lines[index + 2],
            )
            if triplet:
                flush_current()
                role, company, date_range = triplet
                current = _new_entry(role=role, company=company)
                current["date_range"] = date_range
                index += 3
                continue

        company_role = _parse_company_role_line(line)
        if company_role:
            flush_current()
            company, role = company_role
            current = _new_entry(role=role, company=company)
            index += 1
            continue

        location_date = _parse_location_date_line(line)
        if location_date:
            location, date_range = location_date
            if current is None:
                current = _new_entry()
            if not current.get("location"):
                current["location"] = location
            if not current.get("date_range"):
                current["date_range"] = _clean_date_range_text(date_range)
            index += 1
            continue

        if current is None:
            if (
                index + 1 < len(normalized_lines)
                and _looks_like_entry_title_text(line)
                and _looks_like_date_range_text(normalized_lines[index + 1])
            ):
                current = _new_entry()
                if _looks_like_company_text(line) and not _looks_like_role_text(line):
                    current["company"] = line
                else:
                    current["role"] = line
                current["date_range"] = _clean_date_range_text(normalized_lines[index + 1])
                index += 2
                continue
            index += 1
            continue

        if _looks_like_date_range_text(line) and not current.get("date_range"):
            current["date_range"] = _clean_date_range_text(line)
            index += 1
            continue

        if (
            not current.get("company")
            and current.get("role")
            and _looks_like_entry_title_text(line)
            and not _looks_like_date_range_text(line)
        ):
            current["company"] = line
            index += 1
            continue

        if (
            not current.get("role")
            and current.get("company")
            and _looks_like_entry_title_text(line)
            and not _looks_like_date_range_text(line)
        ):
            current["role"] = line
            index += 1
            continue

        current.setdefault("bullets", []).append(line)
        index += 1

    flush_current()
    return entries


def _backfill_experience_location(entries: List[Dict[str, object]], fallback_location: str) -> None:
    location = _normalize_line(fallback_location)
    if not location:
        return
    for entry in entries:
        current = _normalize_line(str(entry.get("location", "")))
        if current:
            continue
        entry["location"] = location


def _split_education_and_awards_lines(lines: List[str]) -> tuple[List[str], List[str]]:
    education_lines: List[str] = []
    awards_lines: List[str] = []
    active_bucket = "education"

    for raw in lines:
        line = _strip_bullet_prefix(raw)
        if not line or _is_noise_line(line):
            continue

        lowered = line.lower().strip()
        if lowered in {"education", "education:"}:
            active_bucket = "education"
            continue
        if lowered in {"awards", "awards:", "award", "award:"}:
            active_bucket = "awards"
            continue
        if lowered.startswith("education:"):
            value = _normalize_line(line.split(":", 1)[1])
            if value:
                education_lines.append(value)
            active_bucket = "education"
            continue
        if lowered.startswith("awards:") or lowered.startswith("award:"):
            value = _normalize_line(line.split(":", 1)[1])
            if value:
                awards_lines.append(value)
            active_bucket = "awards"
            continue

        if active_bucket == "awards":
            awards_lines.append(line)
        else:
            education_lines.append(line)

    return education_lines, awards_lines


def _extract_notice_note(value: str) -> str | None:
    line = _normalize_line(value)
    if not line:
        return None
    lowered = line.lower()
    if lowered.startswith("note:"):
        note_text = _normalize_line(line.split(":", 1)[1])
        if not note_text:
            return None
        if "notice" in note_text.lower() or "available to join" in note_text.lower():
            return note_text
        return None
    if "notice" in lowered and "available to join" in lowered:
        return line
    return None


def parse_resume_text(text: str) -> tuple[ResumeProfile, List[ResumeSection]]:
    """Parse plain-text resume content into profile and structured sections."""
    normalized_text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized_text.split("\n")

    first_heading_index = None
    for index, line in enumerate(lines):
        if _section_heading(line):
            first_heading_index = index
            break

    header_lines = lines[:first_heading_index] if first_heading_index is not None else lines
    body_lines = lines[first_heading_index:] if first_heading_index is not None else []
    name, contact = _extract_header(header_lines)

    grouped_sections: Dict[str, List[str]] = {}
    section_order: List[str] = []
    active_section: str | None = None
    for raw in body_lines:
        heading = _section_heading(raw)
        if heading:
            active_section = heading
            if heading not in grouped_sections:
                grouped_sections[heading] = []
                section_order.append(heading)
            continue
        if active_section is None:
            continue
        grouped_sections[active_section].append(raw.strip())

    inference_source_lines = body_lines if body_lines else header_lines[1:]

    summary_paragraphs = _paragraphs_from_lines(grouped_sections.get("Professional Summary", []))
    skill_categories, flattened_skills = _extract_skills(grouped_sections.get("Technical Skills", []))
    experience_entries = _extract_experience(grouped_sections.get("Professional Experience", []))
    education_lines = [
        _strip_bullet_prefix(line)
        for line in grouped_sections.get("Education", [])
        if _strip_bullet_prefix(line) and not _is_noise_line(line)
    ]
    awards_lines = [
        _strip_bullet_prefix(line)
        for line in grouped_sections.get("Awards", [])
        if _strip_bullet_prefix(line) and not _is_noise_line(line)
    ]
    combined_education_awards_lines = grouped_sections.get("Education & Awards", [])
    if combined_education_awards_lines:
        combined_education, combined_awards = _split_education_and_awards_lines(combined_education_awards_lines)
        education_lines.extend(combined_education)
        awards_lines.extend(combined_awards)

    if not summary_paragraphs:
        summary_paragraphs = _infer_summary_paragraphs(inference_source_lines)

    if not experience_entries:
        experience_entries = _extract_experience(inference_source_lines)
    _backfill_experience_location(experience_entries, contact.get("location", ""))

    if not flattened_skills:
        inferred_skill_lines = _infer_skill_lines(inference_source_lines)
        _, inferred_skills = _extract_skills(inferred_skill_lines)
        flattened_skills = inferred_skills

    if not skill_categories and flattened_skills:
        skill_categories = _auto_group_skills(flattened_skills)

    if not education_lines:
        education_lines = _infer_education_lines(inference_source_lines)

    if not awards_lines:
        awards_lines = _infer_awards_lines(inference_source_lines)

    extracted_notice_note = ""
    filtered_education_lines: List[str] = []
    for line in education_lines:
        notice_note = _extract_notice_note(line)
        if notice_note:
            if not extracted_notice_note:
                extracted_notice_note = notice_note
            continue
        filtered_education_lines.append(line)
    education_lines = filtered_education_lines

    filtered_awards_lines: List[str] = []
    for line in awards_lines:
        notice_note = _extract_notice_note(line)
        if notice_note:
            if not extracted_notice_note:
                extracted_notice_note = notice_note
            continue
        filtered_awards_lines.append(line)
    awards_lines = filtered_awards_lines

    if extracted_notice_note and "notice_note" not in contact:
        contact["notice_note"] = extracted_notice_note

    profile_experience: List[Dict[str, object]] = []
    for entry in experience_entries:
        start, end = _split_date_range(str(entry.get("date_range", "")))
        profile_experience.append(
            {
                "role": entry.get("role", ""),
                "company": entry.get("company", ""),
                "location": entry.get("location", ""),
                "start": start,
                "end": end or ("Present" if re.search(r"\bpresent\b", str(entry.get("date_range", "")), re.IGNORECASE) else ""),
                "bullets": list(entry.get("bullets", []) or []),
            }
        )

    profile_education: List[Dict[str, object]] = []
    education_index = 0
    while education_index < len(education_lines):
        line = education_lines[education_index]
        next_line = (
            education_lines[education_index + 1]
            if education_index + 1 < len(education_lines)
            else ""
        )

        if "|" not in line and "|" not in next_line and next_line:
            first = _normalize_line(line)
            second = _normalize_line(next_line)
            if first and second and not _looks_like_year_text(second):
                if _looks_like_institution(first) and not _looks_like_institution(second):
                    profile_education.append({"institution": first, "degree": second})
                    education_index += 2
                    continue
                if _looks_like_institution(second) and not _looks_like_institution(first):
                    profile_education.append({"degree": first, "institution": second})
                    education_index += 2
                    continue

        parts = [_normalize_line(part) for part in line.split("|") if _normalize_line(part)]
        if not parts:
            education_index += 1
            continue
        if len(parts) == 1:
            profile_education.append({"institution": parts[0]})
            education_index += 1
            continue

        first, second = parts[0], parts[1]
        if _looks_like_institution(first) and not _looks_like_institution(second):
            institution, degree = first, second
        elif _looks_like_institution(second) and not _looks_like_institution(first):
            degree, institution = first, second
        else:
            degree, institution = first, second

        record: Dict[str, object] = {
            "degree": degree,
            "institution": institution,
        }
        remainder = parts[2:]
        if remainder:
            record["location"] = remainder[0]

        details: List[str] = []
        for token in remainder[1:]:
            if "year" not in record and _looks_like_year_text(token):
                record["year"] = token
                continue
            if "grade" not in record and _looks_like_grade_text(token):
                record["grade"] = token
                continue
            if "year" not in record:
                record["year"] = token
                continue
            if "grade" not in record:
                record["grade"] = token
                continue
            details.append(token)
        if details:
            record["details"] = details
        profile_education.append(record)
        education_index += 1

    headline = ""
    if experience_entries:
        first = experience_entries[0]
        role = _normalize_line(str(first.get("role", "")))
        company = _normalize_line(str(first.get("company", "")))
        if role and company:
            headline = f"{role} at {company}"
        else:
            headline = role or company

    profile = ResumeProfile(
        name=name,
        headline=headline or None,
        contact=contact,
        summary=summary_paragraphs,
        experience=profile_experience,
        education=profile_education,
        skills=flattened_skills,
    )

    sections: List[ResumeSection] = []

    if summary_paragraphs:
        sections.append(ResumeSection(title="Professional Summary", paragraphs=summary_paragraphs))

    if skill_categories or flattened_skills:
        skill_section = ResumeSection(title="Technical Skills")
        if skill_categories:
            skill_section.meta["category_lines"] = list(skill_categories)
        elif flattened_skills:
            skill_section.bullets = flattened_skills
        sections.append(skill_section)

    if experience_entries:
        experience_section = ResumeSection(title="Professional Experience")
        experience_section.meta["entries"] = experience_entries
        sections.append(experience_section)

    if education_lines:
        sections.append(ResumeSection(title="Education", paragraphs=education_lines))

    if awards_lines:
        awards_section = ResumeSection(title="Awards", bullets=awards_lines)
        sections.append(awards_section)
        profile.additional_sections.append(
            ResumeSection(title="Awards", bullets=list(awards_lines))
        )

    # Keep any known section heading order not covered above as generic sections.
    covered = {section.title for section in sections}
    if combined_education_awards_lines:
        covered.add("Education & Awards")
    for heading in section_order:
        if heading in covered:
            continue
        lines_for_section = [
            _strip_bullet_prefix(line)
            for line in grouped_sections.get(heading, [])
            if _strip_bullet_prefix(line) and not _is_noise_line(line)
        ]
        if lines_for_section:
            sections.append(ResumeSection(title=heading, paragraphs=lines_for_section))

    if not sections:
        fallback_paragraphs = _paragraphs_from_lines(lines)
        if fallback_paragraphs:
            sections.append(ResumeSection(title="Professional Summary", paragraphs=fallback_paragraphs))
            profile.summary = fallback_paragraphs

    return profile, sections
