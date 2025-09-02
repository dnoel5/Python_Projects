import os
import pdfplumber
import google.generativeai as genai
import time
from fpdf import FPDF
import genanki  # <-- NEW: Import genanki
import random  # <-- NEW: For generating unique IDs

# --- Configuration ---
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("API Key not found. Please set the GOOGLE_API_KEY environment variable.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


# --- Helper Functions ---

def extract_text_from_pdf(pdf_path):
    """Extracts all text from a given PDF file."""
    print(f"📚 Extracting text from {pdf_path}...")
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        print("✅ Text extraction complete.")
        return full_text
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        return None


def generate_study_content(text_chunk, prompt_style):
    """Sends text to Gemini with a specific prompt to generate a study guide section."""
    prompts = {
        "summary": "Provide a high-level summary of the following text in one or two clear paragraphs. Focus on the core argument and conclusions.",
        "feynman": "Explain the core concepts in the following text using the Feynman Technique. Break it down and explain it in simple, clear language, using analogies, as if teaching a beginner. Define any essential jargon that cannot be avoided.",
        "fill_in_blank": "Transform the following text into a 'fill-in-the-blank' study format. Pull out the most important keywords or phrases and replace them with '____'. After the sentences, create an 'Answers:' list with the removed words.",
        # This prompt is optimized for easy parsing into Q&A pairs
        "flashcards": "Generate a set of flashcards from the text. Each flashcard must strictly follow this format: 'Q: [question text]\nA: [answer text]'. Do not add any other text or numbering."
    }
    prompt = prompts.get(prompt_style)
    full_prompt = f"{prompt}\n\n--- TEXT ---\n{text_chunk}"
    try:
        response = model.generate_content(full_prompt)
        time.sleep(1)
        # We don't clean the text for Anki parsing to preserve the Q: and A: markers
        if prompt_style == "flashcards":
            return response.text
        return response.text.encode('latin-1', 'replace').decode('latin-1')
    except Exception as e:
        return f"Error generating content: {e}"


def create_anki_package(flashcard_text, deck_name):
    """Parses Gemini's output and creates an Anki .apkg file."""
    print(f"📇 Creating Anki deck '{deck_name}.apkg'...")
    try:
        # Define the Anki card model (Front/Back)
        anki_model = genanki.Model(
            random.randrange(1 << 30, 1 << 31),
            'Simple Model',
            fields=[{'name': 'Question'}, {'name': 'Answer'}],
            templates=[{
                'name': 'Card 1',
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
            }]
        )

        # Create the Anki Deck
        anki_deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), deck_name)

        # Parse the text and create notes
        lines = flashcard_text.strip().split('\n')
        question = ""
        for line in lines:
            if line.startswith('Q:'):
                question = line[3:].strip()
            elif line.startswith('A:') and question:
                answer = line[3:].strip()
                note = genanki.Note(model=anki_model, fields=[question, answer])
                anki_deck.add_note(note)
                question = ""  # Reset question

        # Package and save the deck
        output_filename = f"{deck_name.replace(' ', '_')}.apkg"
        genanki.Package(anki_deck).write_to_file(output_filename)
        print(f"✅ Anki deck saved as '{output_filename}'")
        return output_filename
    except Exception as e:
        print(f"❌ Failed to create Anki package: {e}")
        return None


# --- Main Execution ---
if __name__ == "__main__":
    PDF_FILE_PATH = r"E:\Documents\OneDrive - UT Arlington\Documents\Summer 2025\NURS 4331\Exam 2\Module 4\Oncologic Disorders\Oncological Disorders-Medications.pdf"

    document_text = extract_text_from_pdf(PDF_FILE_PATH)

    if document_text:
        print("\n🤖 Generating your comprehensive study guide with Gemini...")

        # --- Generate Content ---
        summary = generate_study_content(document_text, "summary")
        feynman_explanation = generate_study_content(document_text, "feynman")
        fill_in_blank = generate_study_content(document_text, "fill_in_blank")
        flashcard_text = generate_study_content(document_text, "flashcards")
        print("✅ All sections generated.")

        # --- Build the PDF ---
        PDF_GUIDE_PATH = "comprehensive_study_guide.pdf"
        print(f"\n💾 Saving comprehensive PDF guide to {PDF_GUIDE_PATH}...")
        pdf = FPDF()


        def write_section(title, content):
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, title, 0, 1, 'C')
            pdf.ln(10)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 5, content.encode('latin-1', 'replace').decode('latin-1'))


        write_section("Section 1: High-Level Summary", summary)
        write_section("Section 2: Feynman Technique Explanations", feynman_explanation)
        write_section("Section 3: In-Depth Fill-in-the-Blanks", fill_in_blank)
        write_section("Section 4: Flashcards Text", flashcard_text)
        pdf.output(PDF_GUIDE_PATH)
        print(f"✅ PDF guide saved.")

        # --- Create the Anki Package ---
        deck_name = os.path.basename(PDF_FILE_PATH).replace('.pdf', '')
        create_anki_package(flashcard_text, deck_name)

        print(f"\n✨ All done!")