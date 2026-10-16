"""Usage: python tools/test_import_genes.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import import_genes  # noqa: E402

G = "/Game/Data/Creatures/RL01/Genes/"
DUMP = "\n".join([
    "# Voidlingpelago gene dump",
    f"{G}Eyes/DA_Gene_Eye_RL01_00.DA_Gene_Eye_RL01_00\tEyeGeneDataAsset\tStarry\tRL01\tKwipeck",
    f"{G}Colors/DA_Gene_Color_RL01_01.DA_Gene_Color_RL01_01\tColorGeneDataAsset\tCrimson\tRL01\tKwipeck",
    f"{G}Colors/DA_Gene_Color_RL01_02.DA_Gene_Color_RL01_02\tColorGeneDataAsset\tCrimson\tRL01\tKwipeck",
    f"{G}Patterns/DA_Gene_Pattern_RL01_00.DA_Gene_Pattern_RL01_00\t\t\tRL01\t",
    f"{G}Eyes/DA_Gene_Eye_RL01_99.DA_Gene_Eye_RL01_99\tEyeGeneDataAsset\tBase\tRL01\tKwipeck\tfalse",
])


class TestImportGenes(unittest.TestCase):
    def import_into(self, genes_json: Path, dump: str) -> list:
        dump_file = genes_json.parent / "genes.txt"
        dump_file.write_text(dump, encoding="utf-8")
        import_genes.main(str(dump_file), genes_json)
        return json.loads(genes_json.read_text(encoding="utf-8"))

    def test_first_import(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            genes = self.import_into(Path(folder) / "genes.json", DUMP)
        by_asset = {gene["asset"]: gene for gene in genes}
        self.assertEqual(sorted(gene["id"] for gene in genes), [845001, 845002, 845003, 845004])
        self.assertNotIn("DA_Gene_Eye_RL01_99", by_asset, "genes that can't be collected are skipped")
        self.assertEqual(by_asset["DA_Gene_Eye_RL01_00"]["name"], "Kwipeck Eye Gene: Starry")
        # Same display name twice gets a suffix
        self.assertEqual({by_asset["DA_Gene_Color_RL01_01"]["name"], by_asset["DA_Gene_Color_RL01_02"]["name"]},
                         {"Kwipeck Color Gene: Crimson", "Kwipeck Color Gene: Crimson (2)"})
        # Unreadable gene: type from the folder, name from the asset, species from the code
        self.assertEqual(by_asset["DA_Gene_Pattern_RL01_00"]["name"], "RL01 Pattern Gene: DA_Gene_Pattern_RL01_00")

    def test_reimport_keeps_ids_and_adds_new_genes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            genes_json = Path(folder) / "genes.json"
            first = {gene["asset"]: gene for gene in self.import_into(genes_json, DUMP)}
            # A later dump: one gene gone, one new gene that sorts before the others
            later = "\n".join(DUMP.splitlines()[2:] + [
                "/Game/Data/Creatures/RL00/Genes/Eyes/DA_Gene_Eye_RL00_00.DA_Gene_Eye_RL00_00\t"
                "EyeGeneDataAsset\tGlow\tRL00\tGwigoon"])
            second = {gene["asset"]: gene for gene in self.import_into(genes_json, later)}
        for asset, gene in first.items():
            self.assertEqual(second[asset], gene, "existing genes keep their ID and name, also when missing")
        self.assertEqual(second["DA_Gene_Eye_RL00_00"]["id"], 845005)


if __name__ == "__main__":
    unittest.main()
