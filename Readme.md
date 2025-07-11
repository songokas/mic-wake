# Howto

Run docker image

```bash
docker run -p 8080:8080 --name local-ai --rm -d -ti -v localai-models:/models localai/localai:latest-aio-cpu --models-path /models
```

Setup script

```bash
cd mic-wake

python3 -m venv .

sudo apt install portaudio19-dev
bin/pip3 install -r requirements.txt

mkdir -p ./lib/python3.11/site-packages/openwakeword/resources/models/
# copy models
cp models/* lib/python3.11/site-packages/openwakeword/resources/models/
# or download it
bin/python3 mic.py --download-models

# use alexa model from default location
bin/python3 mic.py --verbosity debug --wake-model alexa
# use all models from default location using various input settings use 80ms interval for wake word (44100 * 0.08 = 3528) (48000 * 0.08 = 3840)
bin/python3 mic.py --verbosity debug --input-rate 44100 --input-frame-size 3528 --mic-index 7 --input-channels 1
# list microphones
bin/python3 mic.py --mic-index -1

# list input devices
arecord -l
# dump input params
arecord -D hw:2 --dump-hw-params
# record sample
arecord -D hw:2,0 -c 1 -f S16_LE -r 48000 test.wav

# full example
./bin/python3 mic.py --verbosity debug --mic-index 2 --input-rate 48000 --input-frame-size 3840 --input-channels 1 --wake-model models/alexa_v0.1.onnx --mqtt-topic audio/commands --mqtt-host localhost --mqtt-user audio --mqtt-pass pass --transcription-url http://localhost:8080/v1/audio/transcriptions
```
