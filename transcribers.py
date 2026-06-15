import os
import queue
import time
import re
import threading
import json

import pyaudio
import websockets.sync.client
from dotenv import load_dotenv

from config import LISTENING_ON_STARTUP

import speech_recognition as sr

from deepgram import DeepgramClient

load_dotenv()

from config import VOICE_LABELS, GRAMMAR_KEYWORDS
keyterms=VOICE_LABELS + GRAMMAR_KEYWORDS

class DeepgramStreamingTranscriber:
    """
    Streams raw audio directly to Deepgram over WebSocket.
    Uses raw websockets rather than the SDK streaming client
    to avoid SDK version compatibility issues.
    Public interface: start(text_queue)
    """

    def __init__(self):
        self.listening = LISTENING_ON_STARTUP
        self._keyterms = keyterms
        self._api_key = os.getenv("DEEPGRAM", "")

    def start(self, text_queue: queue.Queue) -> None:
        # build url with query params
        params = "&".join([
            "model=nova-3",
            "language=en",
            "numerals=true",
            "interim_results=false",
            "endpointing=300",
            "punctuate=false",
            "encoding=linear16",
            "sample_rate=16000",
        ])
        if self._keyterms:
            for term in self._keyterms:
                params += f"&keyterm={term}"

        url = f"wss://api.deepgram.com/v1/listen?{params}"
        headers = {"Authorization": f"Token {self._api_key}"}

        with websockets.sync.client.connect(url, additional_headers=headers) as ws:

            # receive transcripts in background thread
            def receive():
                for raw in ws:
                    try:
                        data = json.loads(raw)
                        transcript = (
                            data.get("channel", {})
                            .get("alternatives", [{}])[0]
                            .get("transcript", "")
                            .strip()
                        )
                        if len(transcript) >= 2:
                            transcript = self._collapse_digit_sequences(transcript)
                            print(f'\ntranscription: "{transcript}"')
                            text_queue.put(transcript)
                    except Exception:
                        pass

            threading.Thread(target=receive, daemon=True).start()

            # send audio in main loop
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024,
            )

            print("microphone ready")
            try:
                while True:
                    if self.listening:
                        chunk = stream.read(1024, exception_on_overflow=False)
                        ws.send(chunk)
                    else:
                        time.sleep(0.05)
            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()

    def set_listening(self, value: bool):
        self.listening = value

    def set_keyterms(self, keyterms: list[str]) -> None:
        # note: only takes effect on next connection
        self._keyterms = keyterms

    def _collapse_digit_sequences(self, text: str) -> str:
        return re.sub(r"\b(\d)( \d)+\b", lambda m: m.group(0).replace(" ", ""), text)
    

class DeepgramTranscriber:
    """
    Records complete phrases from the microphone and sends to Deepgram
    as pre-recorded audio. More reliable phrase detection than streaming
    for short command-and-control input.
    Public interface: start(text_queue)
    """

    def __init__(self):
        self.listening = LISTENING_ON_STARTUP
        self._keyterms = keyterms
        self._client = DeepgramClient(api_key=os.getenv("DEEPGRAM", ""))
        self._audio_queue = queue.Queue()

    def start(self, text_queue: queue.Queue) -> None:
        threading.Thread(target=self._record, daemon=True).start()
        self._transcribe(text_queue)

    def set_listening(self, value: bool):
        self.listening = value

    def set_keyterms(self, keyterms: list[str]) -> None:
        self._keyterms = keyterms

    def _record(self) -> None:
        r = sr.Recognizer()
        r.energy_threshold = 150
        r.dynamic_energy_threshold = False

        with sr.Microphone() as source:
            print("microphone ready")
            while True:
                if not self.listening:
                    time.sleep(0.05)
                    continue
                try:
                    audio = r.listen(source, phrase_time_limit=8)
                    self._audio_queue.put(audio)
                except sr.WaitTimeoutError:
                    continue

    def _transcribe(self, text_queue: queue.Queue) -> None:
        while True:
            try:
                audio = self._audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            wav_bytes = audio.get_wav_data()

            try:
                response = self._client.listen.v1.media.transcribe_file(
                    request=wav_bytes,
                    model="nova-3",
                    language="en",
                    keyterm=self._keyterms,
                    numerals=True,
                    punctuate=False,
                )
                text = response.results.channels[0].alternatives[0].transcript.strip()
            except Exception as e:
                print(f"deepgram error: {e}")
                continue

            text = self._collapse_digit_sequences(text)

            if len(text) >= 2:
                print(f'\ntranscription: "{text}"')
                text_queue.put(text)

    def _collapse_digit_sequences(self, text: str) -> str:
        return re.sub(r"\b(\d)( \d)+\b", lambda m: m.group(0).replace(" ", ""), text)