import queue
import threading
import speech_recognition as sr

import time

# Microphone not listening during transcription - threading fixes this


class GoogleTranscriber:
    """
    Records from the microphone and transcribes via Google Speech API.

    Internally manages its own audio queue and two threads:
      - one for recording
      - one for transcription

    Only public interface is start(text_queue) — same as every other transcriber.
    """

    def __init__(self):
        self._audio_queue = queue.Queue()
        self.listening = False  # off by default

    def start(self, text_queue: queue.Queue) -> None:
        # start recording in background, run transcription on this thread
        threading.Thread(target=self._record, daemon=True).start()
        self._transcribe(text_queue)

    def set_listening(self, value: bool):
        self.listening = value

    def _record(self) -> None:
        # records audio phrases and puts them onto the internal audio queue
        r = sr.Recognizer()
        r.energy_threshold = 150
        r.dynamic_energy_threshold = False

        with sr.Microphone() as source:
            print("microphone ready")
            while True:
                if not self.listening:
                    time.sleep(0.05)  # kind of questioning this pattern
                    continue
                try:
                    audio = r.listen(source, phrase_time_limit=8)
                    self._audio_queue.put(audio)
                except sr.WaitTimeoutError:
                    continue

    def _transcribe(self, text_queue: queue.Queue) -> None:
        # pulls audio off the internal queue, transcribes, puts text onto text_queue
        r = sr.Recognizer()

        while True:
            try:
                audio = self._audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                text = r.recognize_google(audio)
                print(f'\ntranscription: "{text}"')
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"speech recognition error: {e}")
                continue

            if len(text.strip()) >= 2:
                text_queue.put(text.strip())
