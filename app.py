import os
from flask import Flask, request, render_template, redirect, url_for
import moviepy.editor as mp
import speech_recognition as sr  # <-- Use SpeechRecognition
from googletrans import Translator

# Initialize the Flask application
app = Flask(__name__)

# Configure the upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- 2. Load Translator model ---
try:
    print("Initializing Translator...")
    translator = Translator()
    print("Translator initialized successfully.")
except Exception as e:
    print(f"Error initializing Translator: {e}")
    translator = None


def transcribe_audio(audio_path, language_code):
    """
    Uses Google's Speech Recognition to transcribe the given audio file
    in the specified language.
    """
    if translator is None:
        return "Error: Translator failed to load. Please check server logs."

    recognizer = sr.Recognizer()
    try:
        # Open the audio file
        with sr.AudioFile(audio_path) as source:
            # Record the audio data
            audio_data = recognizer.record(source)
            # Transcribe using Google's free API, specifying the language
            text = recognizer.recognize_google(audio_data, language=language_code)
            return text

    except sr.UnknownValueError:
        return "Speech Recognition could not understand the audio."
    except sr.RequestError as e:
        return f"Could not request results from Google service; {e}"
    except Exception as e:
        return f"An error occurred during transcription: {e}"


@app.route('/', methods=['GET', 'POST'])
def index():
    transcription = None

    if request.method == 'POST':
        # Check if the 'video' file is part of the request
        if 'video' not in request.files:
            return redirect(request.url)

        file = request.files['video']

        # --- Get the selected language from the form ---
        selected_language = request.form.get('language', 'en-US')  # Default to English

        if file.filename == '':
            return redirect(request.url)

        if file:
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(video_path)

            audio_filename = os.path.splitext(file.filename)[0] + '.wav'
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)

            try:
                # --- Step 1: Extract audio from video ---
                print(f"Extracting audio from {video_path}...")
                video_clip = mp.VideoFileClip(video_path)
                video_clip.audio.write_audiofile(audio_path, codec='pcm_s16le')
                video_clip.close()
                print(f"Audio saved to {audio_path}")

                # --- Step 2: Transcribe audio to original text ---
                print(f"Transcribing audio in {selected_language}...")
                transcription = transcribe_audio(audio_path, selected_language)
                print("Transcription complete.")

            except Exception as e:
                print(f"An error occurred: {e}")
                transcription = f"An error occurred during processing: {e}"

            finally:
                # --- Step 3: Clean up temporary files ---
                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                print("Temporary files cleaned up.")

    # Render the template with the original transcription
    return render_template('index.html', transcription=transcription)


# --- 4. Route for handling translation ---
@app.route('/translate', methods=['POST'])
def translate():
    original_text = request.form['original_text']
    translation = None

    if translator is None:
        translation = "Error: Translator failed to initialize. Please check server logs."
    else:
        try:
            print(f"Translating to English...")
            # Auto-detects source language, translates to 'en'
            translated_obj = translator.translate(original_text, dest='en')
            translation = translated_obj.text
            print("Translation complete.")
        except Exception as e:
            print(f"Error during translation: {e}")
            translation = f"An error occurred during translation: {e}"

    # Re-render the page, this time including all 3 variables
    return render_template(
        'index.html',
        transcription=original_text,
        translation=translation
    )


if __name__ == '__main__':
    app.run(debug=True)

