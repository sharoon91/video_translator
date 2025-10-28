from flask import Flask, render_template, request, send_file
import os, asyncio
from moviepy.editor import VideoFileClip, AudioFileClip
from pydub import AudioSegment, silence
from tempfile import NamedTemporaryFile
import whisper
from googletrans import Translator
import edge_tts

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/translate', methods=['POST'])
def translate():
    file = request.files.get('video')
    if not file:
        return "❌ No video uploaded", 400

    video_path = "uploaded_video.mp4"
    file.save(video_path)

    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile("audio.wav")

    model = whisper.load_model("small")
    print("⏳ Transcribing audio...")
    result = model.transcribe("audio.wav", task="transcribe")

    translator = Translator()
    segments = result["segments"]

    translated_segments = []
    for i, seg in enumerate(segments):
        start = seg["start"]
        end = seg["end"]
        original_text = seg["text"]

        # Translate each small segment
        translated_text = translator.translate(original_text, dest='hi').text
        segment_filename = f"segment_{i}.mp3"
        asyncio.run(generate_tts(translated_text, segment_filename, "hi-IN-SwaraNeural"))

        translated_segments.append({
            "file": segment_filename,
            "start": start,
            "end": end
        })

    # Combine segments based on timestamps
    combined = AudioSegment.silent(duration=int(clip.duration * 1000))
    for seg in translated_segments:
        audio = AudioSegment.from_file(seg["file"])
        combined = combined.overlay(audio, position=int(seg["start"] * 1000))

    translated_audio_path = "translated_audio_full.mp3"
    combined.export(translated_audio_path, format="mp3")

    # Merge back with video
    final_video_path = "translated_video.mp4"
    new_audio = AudioFileClip(translated_audio_path)
    final_video = clip.set_audio(new_audio)
    final_video.write_videofile(final_video_path, codec='libx264', audio_codec='aac')

    return send_file(final_video_path, as_attachment=True)


# 🔊 Edge TTS helper
async def generate_tts(text, filename, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)


if __name__ == "__main__":
    app.run(debug=True)
