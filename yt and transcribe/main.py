import os
import time
from pytube import YouTube
from pydub import AudioSegment
from fpdf import FPDF
import whisper

# Load Whisper model once (choose: "tiny", "base", "small", "medium", or "large")
whisper_model = whisper.load_model("base")

OUTPUT_DIR = 'downloads'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_audio(url):
    yt = YouTube(url)
    title = yt.title
    print(f"\n📥 Downloading: {title}")
    stream = yt.streams.filter(only_audio=True).first()
    audio_path = stream.download(output_path=OUTPUT_DIR)
    base, _ = os.path.splitext(audio_path)
    mp3_path = base + ".mp3"
    AudioSegment.from_file(audio_path).export(mp3_path, format="mp3")
    os.remove(audio_path)
    print(f"🎵 Audio converted to MP3: {mp3_path}")
    return mp3_path, title

def compress_audio(input_path):
    compressed_path = input_path.replace(".mp3", "_compressed.mp3")
    audio = AudioSegment.from_file(input_path)

    # Downsample to reduce size
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(compressed_path, format="mp3", bitrate="48k")

    size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
    print(f"🗜️ Compressed audio saved: {compressed_path} ({size_mb:.2f} MB)")
    return compressed_path

def transcribe_audio_local(mp3_path):
    print("🧠 Transcribing locally with Whisper...")
    result = whisper_model.transcribe(mp3_path)
    return result["text"]

def save_pdf(text, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)
    clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_")).strip()
    filename = os.path.join(OUTPUT_DIR, f"{clean_title[:50]}.pdf")
    pdf.output(filename)
    print(f"📄 Transcript saved as PDF: {filename}")

def process_link(url):
    try:
        mp3_path, title = download_audio(url)
        compressed_path = compress_audio(mp3_path)
        transcript = transcribe_audio_local(compressed_path)
        save_pdf(transcript, title)
        os.remove(mp3_path)
        os.remove(compressed_path)
    except Exception as e:
        print(f"⚠️ Failed to process {url}: {e}")

def main():
    try:
        with open("youtube_links.txt", "r") as file:
            links = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("❌ 'youtube_links.txt' not found. Create it with one YouTube URL per line.")
        return

    for idx, url in enumerate(links, 1):
        print(f"\n--- Processing {idx}/{len(links)} ---")
        process_link(url)
        time.sleep(1)

if __name__ == "__main__":
    main()
