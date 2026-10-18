import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("migration", Path(__file__).resolve().parents[1] / "migrate_aura.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class MigrationTests(unittest.TestCase):
    def test_real_source_manifest(self):
        nodes, edges, manifest = migration.source_data()
        self.assertEqual(manifest["nodes"]["Compound"], 299)
        self.assertEqual(manifest["relationships"]["CtD"], 142)
        migration.validate_existing(nodes, edges, nodes, edges, complete=True)

    def test_partial_retry_is_additive(self):
        nodes, edges, _ = migration.source_data()
        migration.validate_existing(nodes, edges, nodes[:1], [], complete=False)
        with self.assertRaises(ValueError):
            migration.validate_existing(nodes, edges, nodes[:1], [], complete=True)

    def test_unrelated_target_or_duplicates_are_rejected(self):
        nodes, edges, _ = migration.source_data()
        for target in [[{"id": "foreign", "name": "foreign", "kind": "Compound"}], nodes + nodes[:1]]:
            with self.assertRaises(ValueError):
                migration.validate_existing(nodes, edges, target, [], complete=False)
