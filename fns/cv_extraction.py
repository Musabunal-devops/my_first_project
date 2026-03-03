"""Text and image extraction utilities for CV files."""
import io
import os

import docx
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image


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
