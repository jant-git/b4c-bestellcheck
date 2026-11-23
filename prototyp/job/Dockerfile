FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py regeln.py qualitaet.py ./
# dbt-Projekt (SW11): Bereinigung R1–R5 und Sternschema als SQL, Prüfungen Q01–Q14
COPY transform ./transform

# ENTRYPOINT statt CMD: der Workflow übergibt Modus und Parameter als args (laden | transformieren | entwurf | freigabe).
ENTRYPOINT ["python", "main.py"]
CMD ["entwurf"]
