"""CV parsing and extraction utilities for the CV Profile Builder."""
import io
import os
import re

import docx
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image


def has_year(text):
    """Check if text contains a 4-digit year (1900-2099)"""
    for i in range(len(text) - 3):
        if text[i : i + 4].isdigit():
            year = int(text[i : i + 4])
            if 1900 <= year <= 2099:
                return True
    return False


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


LANGUAGE_PATTERNS = [
    "türkisch", "deutsch", "englisch", "französisch", "spanisch",
    "italienisch", "russisch", "arabisch", "chinesisch", "japanisch",
    "muttersprache", "niveau", "a1", "a2", "b1", "b2", "c1", "c2",
]


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


def extract_text_from_cv(filepath):
    """Extract text from the specified file path."""
    try:
        file_ext = os.path.splitext(filepath)[1].lower()
        text = ""
        if file_ext == ".pdf":
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        elif file_ext in [".doc", ".docx"]:
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        return text
    except (OSError, ValueError) as exc:
        print(f"Text extraction error: {exc}")
        return None


def extract_and_save_images_from_pdf(filepath, output_folder):
    """Extract and save images from the specified PDF file."""
    found_images = []
    try:
        doc = fitz.open(filepath)
        for i in range(len(doc)):
            images = doc.get_page_images(i)
            if not images:
                continue

            for _idx, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_data = base_image["image"]

                if not image_data or len(image_data) < 100:
                    continue

                filename = os.path.basename(filepath)
                try:
                    img_stream = io.BytesIO(image_data)
                    pil_img = Image.open(img_stream)
                    if pil_img.width > 100 and pil_img.height > 100:
                        image_filename = (
                            f"{os.path.splitext(filename)[0]}"
                            f"_profile_photo.png"
                        )
                        image_path = os.path.join(
                            output_folder, image_filename
                        )

                        with open(image_path, "wb") as f_out:
                            f_out.write(image_data)

                        found_images.append(image_filename)
                        return [image_filename]

                except (OSError, ValueError) as exc:
                    print(f"Image size check error: {exc}")
                    continue

    except (OSError, RuntimeError) as exc:
        print(f"Error extracting image from PDF: {exc}")

    print("A profile photo could not be extracted from the CV.")
    return found_images


def extract_contact_info(text):
    """Extract contact information (email, phone, address) from CV text."""
    contact_info = {}
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if "@" in line and "." in line and "email" not in contact_info:
            words = line.split()
            for word in words:
                if "@" in word and "." in word:
                    contact_info["email"] = word
                    break

        elif line.startswith("+") and "phone" not in contact_info:
            digit_count = sum(1 for c in line if c.isdigit())
            if digit_count >= 8:
                contact_info["phone"] = line

        elif "address" not in contact_info:
            has_letters = any(c.isalpha() for c in line)
            has_numbers = any(c.isdigit() for c in line)

            if has_letters and has_numbers and len(line) > 10 and not line.isupper():
                words = line.split()
                has_postal = False
                for word in words:
                    clean_word = word.replace(",", "").replace(".", "")
                    if clean_word.isdigit() and len(clean_word) in [4, 5]:
                        has_postal = True
                        break

                if has_postal:
                    address = line
                    section_words = [
                        "PROFIL", "KENNTNISSE",
                        "BERUFSERFAHRUNG", "AUSBILDUNG",
                    ]
                    for section_word in section_words:
                        if address.upper().endswith(section_word):
                            address = address[: -(len(section_word))].strip()

                    contact_info["address"] = address

    return contact_info


def looks_like_name(label):
    """Check if a section label looks like a person's name."""
    if not label:
        return False
    if label != label.upper():
        return False
    words = [w for w in label.split() if w]
    if len(words) < 2 or len(words) > 5:
        return False
    return all(any(ch.isalpha() for ch in word) for word in words)


_UNWANTED_NAME_TOKENS = {
    "BEWERBUNG", "BEWERBUNGS",
    "ENGLISCHLEHRERIN", "ENGLISCH LEHRERIN",
    "ENGILISCHLEHRERIN", "ENGLISHLEHRERIN",
    "ENGLISH LEHRERIN", "LEHRERIN", "ESL", "TEACHER",
}


def clean_applicant_label(label):
    """Remove unwanted job-title tokens from the end of a name label."""
    tokens = [t for t in label.split() if t]
    while tokens and tokens[-1] in _UNWANTED_NAME_TOKENS:
        tokens.pop()
    return " ".join(tokens) if tokens else label


_UNWANTED_BLOCK_TEXTS = {
    "BEWERBUNG", "ENGLISCHLEHRERIN", "ENGLISCH LEHRERIN",
    "ENGILISCHLEHRERIN", "ENGLISHLEHRERIN",
    "ENGLISH LEHRERIN", "LEHRERIN", "ESL",
}


def filter_name_blocks(blocks):
    """Remove unwanted text entries from name-section blocks."""
    filtered = []
    for block in blocks or []:
        details = []
        for detail in block.get("details", []):
            text = (
                detail.get("text") if isinstance(detail, dict) else str(detail)
            )
            if text and text.upper().strip() in _UNWANTED_BLOCK_TEXTS:
                continue
            details.append(detail)
        block["details"] = details
        if (
            block.get("title")
            or block.get("date")
            or block.get("org")
            or details
        ):
            filtered.append(block)
    return filtered
