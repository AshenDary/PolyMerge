"""Read-only model and graph validation in the isolated ML interpreter."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ml_engine'))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--without-graph', action='store_true')
    args = parser.parse_args()
    stage = 'Python dependencies missing or incompatible. Run the documented first-time setup.'
    try:
        from dotenv import load_dotenv
        import sklearn
        import numpy
        import rdkit
        import fastapi
        import uvicorn
        load_dotenv(ROOT / '.env')
        if sklearn.__version__ != '1.4.0' or numpy.__version__ != '1.26.4':
            raise ValueError('frozen runtime')
        stage = 'Frozen model artifact missing or checksum differs. Obtain the original artifact from the project owner.'
        from app.services.model_serving import DDIModelService
        service = DDIModelService()
        if not service.artifact_path.is_file():
            raise ValueError('artifact missing')
        with service.artifact_path.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        if checksum != '2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d':
            raise ValueError('checksum')
        service._validate_metadata(service._read_json(service.metadata_path, 'metadata'),
                                   service._read_json(service.feature_contract_path, 'contract'))
        stage = 'Local Neo4j configuration is missing. Configure a loopback NEO4J_URI and credentials in .env.'
        uri = urlsplit(os.getenv('NEO4J_URI', ''))
        if uri.hostname not in {'localhost', '127.0.0.1', '::1'} or uri.scheme not in {'bolt', 'neo4j', 'bolt+s', 'neo4j+s'}:
            raise ValueError('local only')
        if not (os.getenv('NEO4J_USER') or os.getenv('NEO4J_USERNAME')) or not os.getenv('NEO4J_PASSWORD'):
            raise ValueError('credentials')
        if not args.without_graph:
            stage = 'Neo4j is not ready or credentials are incorrect. Start your existing database; no graph was created.'
            from app.utils.neo4j_client import Neo4jClient
            from migrate_aura import source_data, validate_existing
            client = Neo4jClient()
            try:
                actual_nodes = client.query('MATCH (n) RETURN n.id AS id, n.name AS name, n.kind AS kind')
                actual_edges = client.query('MATCH (s)-[r]->(t) RETURN s.id AS source, type(r) AS metaedge, t.id AS target')
                stage = 'Graph identity differs from the reviewed fragment. Restore the verified graph manually; no data was changed.'
                nodes, edges, _ = source_data()
                validate_existing(nodes, edges, actual_nodes, actual_edges, complete=True)
            finally:
                client.close()
        sys.stdout.write(json.dumps({'status': 'ready', 'model_sha256': checksum, 'graph_checked': not args.without_graph}) + '\n')
        return 0
    except Exception:
        sys.stdout.write(json.dumps({'error': stage}) + '\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
