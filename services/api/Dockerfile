FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install --with-deps chromium
RUN apt-get update && apt-get install -y --no-install-recommends fonts-nanum && rm -rf /var/lib/apt/lists/*
# Drop optional VTT source tables rejected by Chromium's OpenType sanitizer.
RUN python -c "from fontTools.ttLib import TTFont; p='/usr/share/fonts/truetype/nanum/NanumGothic.ttf'; f=TTFont(p); [f.__delitem__(t) for t in list(f.keys()) if t.startswith('TSI')]; f.save(p)"
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
