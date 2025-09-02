import os
import io
import fitz  # PyMuPDF
import json
from fpdf import FPDF
from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfMerger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load OpenAI API Key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paths
PDF_FOLDER = r"E:\Documents\OneDrive - UT Arlington\Documents\Summer 2025\NURS 4331\Exam 2"
PEDIATRIC_BOOK = r"E:\Documents\OneDrive - UT Arlington\Documents\Summer 2025\NURS 4331\Pediatric Nursing Care - A Concept-Based Approach\Pediatric Nursing Care - A Concept-Based Approach (gnv64).pdf"
QBANK_FOLDER = os.path.join(PDF_FOLDER, "qbank")
MERGED_OUTPUT = os.path.join(QBANK_FOLDER, "NCLEX_Complete_Question_Bank.pdf")
PREPROCESSED_BOOK_PATH = "pediatric_book_text.json"

# Ensure qbank folder exists
os.makedirs(QBANK_FOLDER, exist_ok=True)

def get_preprocessed_book_text():
    """Loads or creates cached pediatric textbook pages."""
    if os.path.exists(PREPROCESSED_BOOK_PATH):
        with open(PREPROCESSED_BOOK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    print("Pre-processing pediatric textbook...")
    doc = fitz.open(PEDIATRIC_BOOK)
    pages = [page.get_text() for page in doc]
    with open(PREPROCESSED_BOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(pages, f)
    return pages

def extract_text_from_pdf(path):
    doc = fitz.open(path)
    return "".join(page.get_text() for page in doc).strip()

def extract_relevant_pediatric_sections(note_text, book_pages, threshold=0.1):
    """Find pages from the pediatric textbook that match class notes."""
    corpus = [note_text] + book_pages
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(corpus)
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    relevant_pages = [book_pages[i] for i, score in enumerate(similarities[0]) if score > threshold]
    return "\n".join(relevant_pages)

def generate_nclex_questions(notes, pediatric_context):
    prompt = f"""
You are an NCLEX tutor. Write many NCLEX-style questions (SATA, meds, safety, prioritization) using both notes and pediatric references.

Format:
Q: ...
A: ...

Class Notes:
{notes}

Pediatric Textbook:
{pediatric_context}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=4000
    )
    return response.choices[0].message.content.strip()

def write_questions_to_pdf(text, output_path):
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    encoded_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, encoded_text)
    pdf.output(output_path)

# === Main Workflow ===
book_pages = get_preprocessed_book_text()
created_files = []

for fname in os.listdir(PDF_FOLDER):
    if fname.endswith(".pdf") and "Study_Guide" not in fname and "Question_Bank" not in fname:
        base = os.path.splitext(fname)[0]
        input_path = os.path.join(PDF_FOLDER, fname)
        output_path = os.path.join(QBANK_FOLDER, f"{base}_Question_Bank.pdf")

        print(f"🔍 Processing: {fname}")
        notes_text = extract_text_from_pdf(input_path)
        pediatric_text = extract_relevant_pediatric_sections(notes_text, book_pages)

        if not pediatric_text.strip():
            print(f"⚠️ Skipped {fname} – No pediatric content found.")
            continue

        question_text = generate_nclex_questions(notes_text, pediatric_text)
        write_questions_to_pdf(question_text, output_path)
        created_files.append((output_path, base.replace("_", " ")))

# === Merge All Question Banks ===
if created_files:
    merger = PdfMerger()
    for pdf_path, title in sorted(created_files):
        merger.append(pdf_path, bookmark=title)
    merger.write(MERGED_OUTPUT)
    merger.close()
    print(f"\n✅ Final merged NCLEX Question Bank created at:\n{MERGED_OUTPUT}")
else:
    print("\n⚠️ No NCLEX question banks were generated.")
