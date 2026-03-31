from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List

from .models import SkillInsights

MANDATORY_MARKERS = (
    "must have",
    "required",
    "mandatory",
    "minimum",
    "at least",
    "need to",
)

PREFERRED_MARKERS = (
    "nice to have",
    "preferred",
    "plus",
    "bonus",
    "optional",
)

STOPWORDS = {
    "and",
    "with",
    "for",
    "the",
    "experience",
    "skills",
    "including",
    "knowledge",
    "ability",
    "should",
    "must",
    "have",
    "to",
    "in",
    "of",
    "or",
    "on",
    "as",
    "you",
    "will",
}


def _tokenize_phrases(text: str) -> Iterable[str]:
    text = re.sub(r"[•·\-\u2013\u2014]", "\n", text)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        yield line


def _extract_skills_from_line(line: str) -> List[str]:
    candidates = re.split(r"[;,/]", line)
    skills: List[str] = []
    for candidate in candidates:
        cleaned = re.sub(r"[^A-Za-z0-9+#.& ]", " ", candidate).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if len(cleaned) < 2:
            continue
        if cleaned.lower() in STOPWORDS:
            continue
        skills.append(cleaned)
    return skills


def analyze_job_description(text: str) -> SkillInsights:
    """Extract mandatory and preferred skills from the job description text."""
    lines = list(_tokenize_phrases(text))
    mandatory: List[str] = []
    preferred: List[str] = []
    keywords: List[str] = []

    for line in lines:
        lower = line.lower()
        extracted = _extract_skills_from_line(line)
        if not extracted:
            continue
        if any(marker in lower for marker in MANDATORY_MARKERS):
            mandatory.extend(extracted)
        elif any(marker in lower for marker in PREFERRED_MARKERS):
            preferred.extend(extracted)
        else:
            keywords.extend(extracted)

    # Deduplicate while preserving order, favoring highest frequency.
    def dedupe(skills: List[str]) -> List[str]:
        counter = Counter(skill.lower() for skill in skills)
        seen = set()
        ordered: List[str] = []
        for skill in skills:
            key = skill.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(skill.strip())
        ordered.sort(key=lambda item: (-counter[item.lower()], item))
        return ordered

    return SkillInsights(
        mandatory=dedupe(mandatory),
        preferred=dedupe(preferred),
        keywords=dedupe(mandatory + preferred + keywords),
    )
