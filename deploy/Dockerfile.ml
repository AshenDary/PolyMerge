FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app/ml_engine
COPY ml_engine/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app
COPY ml_engine/main.py ./main.py
COPY ml_engine/app ./app
COPY data/rules /app/data/rules
COPY data/interim/sprint3/ddinter_hetionet_mapping.csv /app/data/interim/sprint3/ddinter_hetionet_mapping.csv
COPY data/interim/sprint3/ddinter_pubchem_mapping.csv /app/data/interim/sprint3/ddinter_pubchem_mapping.csv
COPY data/processed/fragment_edges.csv /app/data/processed/fragment_edges.csv
COPY data/interim/sprint4/feature_contract.json /app/data/interim/sprint4/feature_contract.json
COPY data/interim/sprint5/final_model_evaluation.json /app/data/interim/sprint5/final_model_evaluation.json
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ['PORT']+'/health',timeout=8)"
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port \"$PORT\" --workers 1"]
