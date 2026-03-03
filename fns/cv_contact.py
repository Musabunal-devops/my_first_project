"""Contact information extraction from CV text."""


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
