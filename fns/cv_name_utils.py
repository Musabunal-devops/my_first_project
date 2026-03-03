"""Name detection and cleaning utilities for CV section labels."""


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
