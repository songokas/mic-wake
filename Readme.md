# Howto

Run docker image

```bash
docker run -p 8080:8080 --name local-ai --rm -d -ti -v localai-models:/models localai/localai:latest-aio-cpu --models-path /models
```

Setup script

```bash
cd mic-wake
python3 -m venv .
bin/pip3 install -r requirements.txt
# copy silero model to an openwakeword expected path
cp models/silero_vad.onnx /lib/python3.11/site-packages/openwakeword/resources/models/silero_vad.onnx

# use alexa model from default location
bin/python3 mic.py --verbosity debug --wake-model alexa
# use all models from default location using various input settings
bin/python3 mic.py --verbosity debug --input-rate 44100 --input-frame-size 3528 --mic-index 7 --input-channels 1
# list microphones
bin/python3 mic.py --mic-index -1
```
