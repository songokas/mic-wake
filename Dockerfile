FROM python:3.11-slim
WORKDIR /app/
RUN apt update && apt install -y build-essential portaudio19-dev && apt clean
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt && mkdir -p /usr/local/lib/python3.11/site-packages/openwakeword/resources/models
COPY models/ /usr/local/lib/python3.11/site-packages/openwakeword/resources/models/
COPY mic.py /app/
ENTRYPOINT ["python", "mic.py"]
