import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from app.utils.neo4j_client import Neo4jClient
c = Neo4jClient()
r = c.query("MATCH (n) RETURN count(n) AS total")
print("Nodes in Neo4j:", r[0]["total"])
c.close()
