FROM python:3.11-slim-trixie@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app/ml_engine
RUN apt-get update && apt-get install -y --no-install-recommends liblzma5=5.8.1-1+deb13u2 \
    && rm -rf /var/lib/apt/lists/*
COPY ml_engine/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir --require-hashes -r requirements.lock && useradd --uid 10001 --create-home app
RUN pip uninstall -y setuptools wheel pip
RUN find / -xdev -type f -perm /6000 -exec chmod a-s {} +
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
CMD ["sh", "-c", "python -m app.artifact_bootstrap && exec uvicorn main:app --host 0.0.0.0 --port \"$PORT\" --workers 1 --limit-concurrency 16 --timeout-keep-alive 5"]
