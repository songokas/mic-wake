import pyaudio
import numpy as np
from openwakeword.model import Model
from openwakeword.utils import download_models
import argparse
import wave
import tempfile
import requests
import paho.mqtt.client as mqtt
import logging
from scipy.signal import resample
from threading import Thread
import re
from subprocess import Popen


# Parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "--input-frame-size",
    help="How much audio (in number of samples) to predict on at once for wake word",
    type=int,
    default=1280,
    required=False,
)
parser.add_argument(
    "--input-rate", help="Sample rate", type=int, default=16000, required=False
)
parser.add_argument("--input-channels", type=int, default=1, required=False)
parser.add_argument(
    "--wake-model",
    help="The path or name of a specific model to load",
    type=str,
    default="",
    required=False,
)
parser.add_argument(
    "--vad-threshold",
    help="Specify voice activity detection threshold (0-1.0)",
    type=float,
    default=0.5,
    required=False,
)
parser.add_argument(
    "--download-models",
    help="Download models",
    type=bool,
    action=argparse.BooleanOptionalAction,
    default=False,
    required=False,
)
parser.add_argument(
    "--suppress-noise",
    help="Use noise suppression",
    type=bool,
    action=argparse.BooleanOptionalAction,
    default=True,
    required=False,
)
parser.add_argument(
    "--inference-framework",
    help="The wake word inference framework to use (either 'onnx' or 'tflite')",
    type=str,
    default="onnx",
    required=False,
)
parser.add_argument(
    "--listen-duration",
    help="Once wake word is detected how long to listen to in seconds",
    type=int,
    default=2,
    required=False,
)
parser.add_argument(
    "--mic-index",
    help="Which microphone to use",
    type=int,
    default=None,
    required=False,
)
parser.add_argument(
    "--transcription-model", type=str, default="whisper-base-q5_1", required=False
)
parser.add_argument("--transcription-language", type=str, default="en", required=False)
parser.add_argument(
    "--transcription-url",
    type=str,
    default="http://localhost:8080/v1/audio/transcriptions",
    required=False,
)
parser.add_argument("--mqtt-host", type=str, default="localhost", required=False)
parser.add_argument("--mqtt-port", type=int, default=1883, required=False)
parser.add_argument("--mqtt-user", type=str, required=False)
parser.add_argument("--mqtt-pass", type=str, required=False)
parser.add_argument(
    "--mqtt-topic",
    help="Topic to send transcribed text to",
    default="transcription/text",
    type=str,
    required=False,
)
parser.add_argument("--verbosity", type=str, default="INFO", required=False)
parser.add_argument(
    "--mqtt-payload-normalize",
    help="Lowercase and strip non alphanumeric chars (except space)",
    type=bool,
    action=argparse.BooleanOptionalAction,
    default=False,
    required=False,
)
parser.add_argument(
    "--normalize-pattern",
    help="Pattern to strip chars",
    type=str,
    default=" *[^a-zA-Z0-9 ]+ *",
    required=False,
)

args = parser.parse_args()

FORMAT = pyaudio.paInt16
# 16 = pyaudio.paInt16
AUDIO_SIZE = args.input_rate * 16 * args.listen_duration / 8
WAKE_WORD_SAMPLE_RATE = 16000

if __name__ == "__main__":

    logger = logging.getLogger("mic")

    logging.basicConfig(level=args.verbosity.upper())

    if args.download_models:
        download_models()

    audio = pyaudio.PyAudio()

    if args.mic_index == -1:

        print(
            "Available devices (all APIs, input + output):",
            audio.get_device_count(),
            # audio.get_default_output_device_info(),
            # audio.get_default_input_device_info(),
        )
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] != 0 and device_info["hostApi"] == 0:
                print("Device index " + str(i) + ": " + device_info["name"])
        exit(0)

    mic_stream = audio.open(
        format=FORMAT,
        channels=args.input_channels,
        rate=args.input_rate,
        input=True,
        output=False,
        frames_per_buffer=args.input_frame_size,
        input_device_index=args.mic_index,
    )

    models_to_load = []
    if args.wake_model:
        models_to_load.append(args.wake_model)
    oww_model = Model(
        models_to_load,
        inference_framework=args.inference_framework,
        enable_speex_noise_suppression=args.suppress_noise,
        vad_threshold=args.vad_threshold,
    )

    detected = False

    mqttc = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    mqttc.enable_logger()
    if args.mqtt_user and args.mqtt_pass:
        mqttc.username_pw_set(args.mqtt_user, args.mqtt_pass)
    mqttc.connect(args.mqtt_host, args.mqtt_port, 60)
    mqttc.loop_start()

    normalize_pattern = re.compile(args.normalize_pattern)

    while True:
        # Get audio
        input_raw_data = mic_stream.read(
            args.input_frame_size, exception_on_overflow=False
        )

        if detected:
            obj.writeframesraw(input_raw_data)
            bytes_written += len(input_raw_data)

            logger.debug("Audio bytes read %s", bytes_written)

            if bytes_written >= AUDIO_SIZE:
                obj.close()

                def transcribe():
                    files = {"file": open(temp.name, "rb")}
                    values = {
                        "model": args.transcription_model,
                        "language": args.transcription_language,
                    }

                    try:
                        r = requests.post(
                            args.transcription_url, files=files, data=values
                        )
                        text = r.json()["text"]

                        logger.debug("Text transcribed: %s", text)
                        is_unknown_text = text.startswith(("[", "(")) and text.endswith(
                            ("]", ")")
                        )
                        if not is_unknown_text:
                            if args.mqtt_payload_normalize:
                                text = normalize_pattern.sub("", text.lower())
                                logger.debug("Normalize to %s", text)
                            mqttc.publish(
                                args.mqtt_topic, payload=text, qos=0, retain=False
                            )
                            # TODO use python libraries
                            # you may want to execute few commands on transcription
                            # aplay = Popen(["aplay", "samples/transcribed.wav"])
                            # vup = Popen(["amixer", "set", "Master", "50%"])
                            # vup = Popen(["mpc", "volume", "50%"])
                    except requests.exceptions.RequestException as e:
                        logger.error("Request failed %s", e)

                t = Thread(target=transcribe)
                t.start()
                oww_model.reset()
                detected = False
            continue

        audio_input = np.frombuffer(input_raw_data, dtype=np.int16)

        if args.input_rate != WAKE_WORD_SAMPLE_RATE:
            # logger.debug("Resample from %s to %s data size %s to %s", args.input_rate, 16000, len(audioInput),
            #              int(len(audioInput) / args.input_rate * WAKE_WORD_SAMPLE_RATE))
            audio_input = resample(
                audio_input,
                int(len(audio_input) / args.input_rate * WAKE_WORD_SAMPLE_RATE),
            )

        prediction = oww_model.predict(audio_input.astype(np.int16))

        for mdl in oww_model.prediction_buffer.keys():
            scores = list(oww_model.prediction_buffer[mdl])

            if scores[-1] > 0.5:
                detected = True
                bytes_written = 0
                temp = tempfile.NamedTemporaryFile()
                obj = wave.open(temp, "wb")
                obj.setnchannels(args.input_channels)
                obj.setsampwidth(audio.get_sample_size(FORMAT))
                obj.setframerate(args.input_rate)
                logger.debug("Wake word detected %s", mdl)
                # TODO use python libraries
                # you may want to execute few commands on detection
                # vdown = Popen(["amixer", "set", "Master", "20%"])
                # vdown = Popen(["mpc", "volume", "20%"])
                # aplay = Popen(["aplay", "samples/detected.wav"])
                break
