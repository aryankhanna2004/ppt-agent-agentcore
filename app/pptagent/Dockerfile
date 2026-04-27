# AgentCore harness requires linux/arm64
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    NODE_MAJOR=20

RUN apt-get update && apt-get install -y --no-install-recommends \
      bash curl ca-certificates git \
      libreoffice poppler-utils \
      fonts-liberation fonts-dejavu \
      build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      "markitdown[pptx,docx,pdf]" \
      "python-pptx" \
      "Pillow" \
      "openpyxl" \
      "lxml"

RUN npm install -g pptxgenjs

RUN mkdir -p /mnt/data /mnt/data/decks /mnt/data/templates /opt/templates /opt/scripts

COPY skills /opt/skills
COPY scripts /opt/scripts
RUN chmod +x /opt/scripts/*.py

# Generate the neutral default template at build time and bake it into the
# image. Users can override per-session by dropping any .pptx into
# /mnt/data/templates/ — see /opt/scripts/inspect_template.py and the
# harness system prompt for how the agent picks the active template.
RUN python3 /opt/scripts/build_default_template.py /opt/templates/default-template.pptx

ENV SKILLS_PATH=/opt/skills \
    TEMPLATES_PATH=/opt/templates \
    USER_TEMPLATES_PATH=/mnt/data/templates \
    DEFAULT_TEMPLATE=/opt/templates/default-template.pptx
