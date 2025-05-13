import pyaudio
import numpy as np
import webrtcvad
import collections
import time
import sys
import io
from faster_whisper import WhisperModel

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DEVICE_INDEX = 1
SAMPLE_RATE = 16000
FRAME_DURATION = 30  # ms
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)
BUFFER_DURATION = 8  # 秒上限
SILENCE_TIMEOUT = 1  # 無音と判定する時間（秒）

model = WhisperModel("large-v2", device="cuda", compute_type="float16")
vad = webrtcvad.Vad(2)  # 感度（0:保守的, 3:積極的）

print("READY", flush=True)

def frame_generator(stream):
    while True:
        yield stream.read(FRAME_SIZE, exception_on_overflow=False)

def vad_collector(stream):
    ring_buffer = collections.deque(maxlen=int(SILENCE_TIMEOUT * 1000 / FRAME_DURATION))
    voiced_frames = []
    triggered = False
    start_time = time.time()

    for frame in frame_generator(stream):
        is_speech = vad.is_speech(frame, SAMPLE_RATE)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                voiced_frames.extend(f for f, s in ring_buffer)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.8 * ring_buffer.maxlen:
                yield b''.join(voiced_frames)
                triggered = False
                voiced_frames = []
                ring_buffer.clear()
                start_time = time.time()

        if time.time() - start_time > BUFFER_DURATION:
            if voiced_frames:
                yield b''.join(voiced_frames)
                voiced_frames = []
            triggered = False
            ring_buffer.clear()
            start_time = time.time()

def start_stream():
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=DEVICE_INDEX,
        frames_per_buffer=FRAME_SIZE
    )

    try:
        buffer_text = ""
        buffer_time = time.time()

        for segment in vad_collector(stream):
            audio_np = np.frombuffer(segment, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(audio_np, language="ja", vad_filter=True)

            for seg in segments:
                text = seg.text.strip()
                now = time.time()

                if not text:
                    continue

                if len(text) <= 4:
                    if buffer_text and len(buffer_text) <= 4:
                        buffer_text += text
                    else:
                        buffer_text = text
                else:
                    if buffer_text:
                        if len(buffer_text) < 5:
                            text = buffer_text + text
                            buffer_text = ""
                    print(text, flush=True)

        if buffer_text:
            print(buffer_text, flush=True)

    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


if __name__ == "__main__":
    start_stream()
