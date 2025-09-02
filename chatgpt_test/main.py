import os
from pytube import YouTube
from pydub import AudioSegment
from fpdf import FPDF
import openai
from dotenv import load_dotenv
import time

# Load OpenAI API Key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

OUTPUT_DIR = 'downloads'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def download_audio(url):
    yt = YouTube(url)
    title = yt.title
    stream = yt.streams.filter(only_audio=True).first()
    audio_path = stream.download(output_path=OUTPUT_DIR)
    base, _ = os.path.splitext(audio_path)
    mp3_path = base + ".mp3"
    AudioSegment.from_file(audio_path).export(mp3_path, format="mp3")
    os.remove(audio_path)
    print(f"Downloaded and converted: {title}")
    return mp3_path, title


def transcribe_audio(mp3_path):
    with open(mp3_path, "rb") as f:
        response = openai.Audio.transcribe("whisper-1", f)
    return response['text']


def save_pdf(text, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)
    clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_")).strip()
    filename = os.path.join(OUTPUT_DIR, f"{clean_title[:50]}.pdf")
    pdf.output(filename)
    print(f"Saved PDF: {filename}")


def process_link(url):
    try:
        mp3_path, title = download_audio(url)
        print("Transcribing...")
        text = transcribe_audio(mp3_path)
        save_pdf(text, title)
        os.remove(mp3_path)
    except Exception as e:
        print(f"Failed on {url}: {e}")


def main():
    with open("youtube_links.txt", "r") as file:
        links = [line.strip() for line in file if line.strip()]

    for idx, url in enumerate(links, 1):
        print(f"\n--- Processing {idx}/{len(links)} ---")
        process_link(url)
        time.sleep(2)  # slight delay to be polite with rate limits


if __name__ == "__main__":
    main()
