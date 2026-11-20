FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Создаем пользователя с UID 1000 (требование Hugging Face Spaces и облачных платформ)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 7860

CMD ["python", "main.py"]
