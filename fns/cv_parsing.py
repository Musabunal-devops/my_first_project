"""CV section parsing and block structuring utilities."""
import re


def has_year(text):
    """Check if text contains a 4-digit year (1900-2099)"""
    for i in range(len(text) - 3):
        if text[i : i + 4].isdigit():
            year = int(text[i : i + 4])
            if 1900 <= year <= 2099:
                return True
    return False


EXPECTED_HEADINGS = {
    "PROFIL": "PROFIL",
    "KENNTNISSE": "KENNTNISSE",
    "SPRACHKENNTNISSE": "SPRACHKENNTNISSE",
    "SPRACHEN": "SPRACHKENNTNISSE",
    "BERUFSERFAHRUNGEN": "BERUFSERFAHRUNGEN",
    "BERUFSERFAHRUNG": "BERUFSERFAHRUNGEN",
    "AUSBILDUNG": "AUSBILDUNG",
    "PROJEKTE UND VERANSTALTUNGEN": "PROJEKTE UND VERANSTALTUNGEN",
    "PROJEKTE & VERANSTALTUNGEN": "PROJEKTE UND VERANSTALTUNGEN",
    "PROJEKTE LEITUNG": "PROJEKTE LEITUNG",
    "PROJEKT LEITUNG": "PROJEKTE LEITUNG",
    "PROJEKTLEITUNG": "PROJEKTE LEITUNG",
    "PROJEKTELEITUNG": "PROJEKTE LEITUNG",
    "PROJEKTLEITUNGEN": "PROJEKTE LEITUNG",
    "ZUSÄTZLICHE QUALIFIKATIONEN": "ZUSÄTZLICHE QUALIFIKATIONEN",
    "ZUSATZLICHE QUALIFIKATIONEN": "ZUSÄTZLICHE QUALIFIKATIONEN",
    "ZUSATZLICHE QUALIFIKATION": "ZUSÄTZLICHE QUALIFIKATIONEN",
    "ZUSÄTZLICHE QUALIFIKATION": "ZUSÄTZLICHE QUALIFIKATIONEN",
}

LANGUAGE_PATTERNS = [
    "türkisch", "deutsch", "englisch", "französisch", "spanisch",
    "italienisch", "russisch", "arabisch", "chinesisch", "japanisch",
    "muttersprache", "niveau", "a1", "a2", "b1", "b2", "c1", "c2",
]


def normalize_heading(text):
    """Normalize text to uppercase heading format."""
    chars = []
    for ch in text:
        if ch.isalpha() or ch.isdigit() or ch.isspace() or ch in ["&", "-", "/"]:
            chars.append(ch.upper())
        else:
            chars.append(" ")
    joined = "".join(chars)
    parts = [segment for segment in joined.split() if segment]
    return " ".join(parts)


def is_probable_heading(text):
    """Heuristic to detect headings written in uppercase."""
    if not text:
        return False
    stripped = text.strip()
    if not stripped or stripped.startswith("\u2022") or stripped.startswith("- "):
        return False
    if not stripped[0].isalpha():
        return False
    if any(ch.islower() for ch in stripped):
        return False
    letters = sum(1 for ch in stripped if ch.isalpha())
    return letters >= 3 and len(stripped) <= 60


def parse_section_blocks(
    section_text, section_name=None
):  # pylint: disable=unused-argument
    """Split a CV section into structured blocks using improved heuristics."""
    blocks = []
    lines = []

    date_regex = re.compile(r"\b(19|20)\d{2}\b")

    def line_has_year(text):
        return bool(date_regex.search(text))

    def is_mostly_date(text):
        """Check if the line is predominantly composed of date-like chars."""
        text_without_dates = date_regex.sub("", text)
        text_without_dates = re.sub(r"[\d\.\/\-\s,]", "", text_without_dates)
        return len(text_without_dates) < 4

    for raw_line in section_text.split("\n"):
        cleaned = raw_line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("•"):
            cleaned = cleaned[1:].strip()
        elif cleaned.startswith("- "):
            cleaned = cleaned[2:].strip()
        lines.append(cleaned)

    if not lines:
        return blocks

    date_count = sum(1 for line in lines if line_has_year(line))
    total_length = sum(len(line) for line in lines)
    avg_length = total_length / len(lines) if lines else 0
    long_line_count = sum(1 for line in lines if len(line) > 60)

    if date_count >= 1:

        current_block = {
            "title": "",
            "date": "",
            "org": "",
            "details": [],
            "subblocks": [],
        }
        blocks.append(current_block)

        def is_strong_title(text):
            """Check for clear title indicators."""
            if not text:
                return False
            if "|" in text:
                return True
            if "(" in text and ")" in text:
                return True
            if " - " in text:
                return True
            if "&" in text:
                return True
            if text.isupper() and len(text.split()) < 6:
                return True
            return False

        pending_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]

            if line_has_year(line):
                match = date_regex.search(line)
                clean_date = line

                range_pattern = re.search(
                    r"(\d{2}\.\d{4}|\d{4})\s*[-\u2013\u2014]\s*"
                    r"(\d{2}\.\d{4}|\d{4}|heute|present|jetzt)",
                    line,
                    re.IGNORECASE,
                )
                if range_pattern:
                    clean_date = range_pattern.group(0)
                else:
                    clean_date = match.group(0) if match else line

                if not is_mostly_date(line):
                    part_title = line.replace(clean_date, "").strip(" -\u2013,")
                    final_title = part_title
                    first_detail = None

                    promoted_pending = False
                    if pending_lines:
                        candidate = pending_lines[-1]
                        if is_strong_title(candidate) and not is_strong_title(
                            part_title
                        ):
                            final_title = candidate
                            first_detail = part_title
                            pending_lines.pop()
                            promoted_pending = True

                    if not promoted_pending:
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]

                            word_count_current = len(part_title.split())
                            word_count_next = len(next_line.split())

                            is_current_sentence_like = word_count_current >= 4
                            is_next_compact = word_count_next < 6

                            current_strong = is_strong_title(part_title)
                            next_strong = is_strong_title(next_line)

                            should_swap = False

                            if "|" in next_line:
                                should_swap = True
                            elif not current_strong and next_strong:
                                should_swap = True
                            elif is_current_sentence_like and is_next_compact:
                                if next_line and next_line[0].isupper():
                                    should_swap = True

                            if not part_title.strip():
                                should_swap = True

                            if should_swap:
                                final_title = next_line
                                if part_title.strip():
                                    first_detail = part_title
                                i += 1

                    if blocks and (blocks[-1]["date"] or blocks[-1]["title"]):
                        blocks[-1]["details"].extend(
                            [{"type": "text", "text": ln} for ln in pending_lines]
                        )
                    else:
                        if pending_lines and not blocks[0]["title"]:
                            blocks[0]["details"].extend(
                                [{"type": "text", "text": ln} for ln in pending_lines]
                            )

                    if (
                        len(blocks) == 1
                        and not blocks[0]["date"]
                        and not blocks[0]["title"]
                    ):
                        blocks[0]["title"] = final_title
                        blocks[0]["date"] = clean_date
                        if first_detail:
                            blocks[0]["details"].insert(
                                0, {"type": "text", "text": first_detail}
                            )
                    else:
                        new_block = {
                            "title": final_title,
                            "date": clean_date,
                            "org": "",
                            "details": [],
                            "subblocks": [],
                        }
                        if first_detail:
                            new_block["details"].append(
                                {"type": "text", "text": first_detail}
                            )
                        blocks.append(new_block)

                    pending_lines = []

                else:
                    potential_title = "Unknown"
                    used_pending_as_title = False

                    if pending_lines:
                        potential_title = pending_lines.pop()
                        used_pending_as_title = True
                    elif i + 1 < len(lines) and (
                        is_strong_title(lines[i + 1])
                        or len(lines[i + 1].split()) < 6
                    ):
                        potential_title = lines[i + 1]
                        i += 1

                    prev_block_idx = len(blocks) - 1
                    if (
                        len(blocks) == 1
                        and not blocks[0]["date"]
                        and not blocks[0]["title"]
                    ):
                        pass
                    else:
                        blocks[prev_block_idx]["details"].extend(
                            [{"type": "text", "text": ln} for ln in pending_lines]
                        )

                    if (
                        (used_pending_as_title or potential_title != "Unknown")
                        and len(blocks) == 1
                        and not blocks[0]["date"]
                    ):
                        blocks[0]["title"] = potential_title
                        blocks[0]["date"] = clean_date
                    else:
                        new_block = {
                            "title": potential_title,
                            "date": clean_date,
                            "org": "",
                            "details": [],
                            "subblocks": [],
                        }
                        blocks.append(new_block)

                    pending_lines = []

            else:
                pending_lines.append(line)

            i += 1

        if blocks:
            blocks[-1]["details"].extend(
                [{"type": "text", "text": ln} for ln in pending_lines]
            )

        if (
            not blocks[0]["date"]
            and not blocks[0]["title"]
            and not blocks[0]["details"]
        ):
            blocks.pop(0)
        elif not blocks[0]["date"] and not blocks[0]["title"]:
            pass

    elif long_line_count > len(lines) * 0.5 or avg_length > 50:
        full_text = " ".join(lines)
        blocks.append(
            {
                "title": "",
                "date": "",
                "org": "",
                "details": [{"type": "paragraph", "text": full_text}],
                "subblocks": [],
            }
        )

    else:
        blocks.append(
            {
                "title": "",
                "date": "",
                "org": "",
                "details": [{"type": "text", "text": line} for line in lines],
                "subblocks": [],
            }
        )

    return blocks


def parse_cv_content(text):
    """Identify CV sections and map their content."""
    for heading in EXPECTED_HEADINGS:
        pattern = (
            r"([a-zA-ZäöüÄÖÜß])("
            + re.escape(heading)
            + r")(?=\s|$)"
        )
        text = re.sub(pattern, r"\1\n\2", text, flags=re.IGNORECASE)

    sections = {}
    section_order = []
    lines = text.split("\n")
    current_section = None

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if "@" in stripped_line and "." in stripped_line:
            continue
        if stripped_line.startswith("+") and any(
            c.isdigit() for c in stripped_line
        ):
            continue

        normalized = normalize_heading(stripped_line)
        canonical_section = None

        if normalized in EXPECTED_HEADINGS:
            canonical_section = EXPECTED_HEADINGS[normalized]
        else:
            for key, canonical_value in EXPECTED_HEADINGS.items():
                if normalized.endswith(" " + key):
                    canonical_section = canonical_value
                    break

        if canonical_section is None and is_probable_heading(stripped_line):
            condensed = normalized.replace(" ", "")
            if len(condensed) >= 5 or " " in normalized:
                canonical_section = " ".join(stripped_line.split())

        if canonical_section:
            current_section = canonical_section
            if canonical_section not in sections:
                sections[canonical_section] = []
                section_order.append(canonical_section)
            continue

        if current_section:
            sections[current_section].append(stripped_line)

    cleaned_sections = {}
    for section_name in section_order:
        content = "\n".join(sections.get(section_name, [])).strip()
        if content:
            cleaned_sections[section_name] = content

    if "KENNTNISSE" in cleaned_sections:
        kenntnisse_lines = cleaned_sections["KENNTNISSE"].split("\n")
        language_lines = []
        other_lines = []

        for line in kenntnisse_lines:
            line_lower = line.lower()
            if any(lang in line_lower for lang in LANGUAGE_PATTERNS):
                language_lines.append(line)
            else:
                other_lines.append(line)

        if other_lines:
            cleaned_sections["KENNTNISSE"] = "\n".join(other_lines)
        else:
            del cleaned_sections["KENNTNISSE"]

        if language_lines:
            if "SPRACHKENNTNISSE" in cleaned_sections:
                cleaned_sections["SPRACHKENNTNISSE"] = (
                    cleaned_sections["SPRACHKENNTNISSE"]
                    + "\n"
                    + "\n".join(language_lines)
                )
            else:
                cleaned_sections["SPRACHKENNTNISSE"] = "\n".join(
                    language_lines
                )
                if "SPRACHKENNTNISSE" not in section_order:
                    section_order.append("SPRACHKENNTNISSE")

    return cleaned_sections
