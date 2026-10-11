FROM nikolaik/python-nodejs:python3.10-nodejs20

RUN curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    -o ffmpeg.tar.xz && \
    tar -xJf ffmpeg.tar.xz && \
    mv ffmpeg-*-static/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*-static/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg*

COPY . /app/
WORKDIR /app/

RUN pip3 install --no-cache-dir -r requirements.txt

# ntgcalls 1.2.x exposes enum members in uppercase, while PyTgCalls 1.2.9
# uses the older title-case spellings. Normalize those references at build time.
RUN python3 - <<'PY'
from pathlib import Path
root = Path('/usr/local/lib/python3.10/site-packages/pytgcalls')
replacements = {
    'StreamStatus.Playing': 'StreamStatus.PLAYING',
    'StreamStatus.Paused': 'StreamStatus.PAUSED',
    'StreamStatus.Idling': 'StreamStatus.IDLING',
    'InputMode.Shell': 'InputMode.SHELL',
    'InputMode.File': 'InputMode.FILE',
}
for path in root.rglob('*.py'):
    text = path.read_text()
    updated = text
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    if updated != text:
        path.write_text(updated)
PY

CMD ["bash", "start"]
