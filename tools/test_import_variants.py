"""Usage: python tools/test_import_variants.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import import_variants  # noqa: E402

E = "/Game/Data/Creatures/PK01/Evolutions/"
DUMP = "\n".join([
    "# Voidlingpelago variant dump",
    f"{E}DA_Evolution_PK01_Base.DA_Evolution_PK01_Base\tBase\tKwipeck\tPK01\tKwipeck\t0\t0",
    f"{E}DA_Evolution_PK01_Qwebek.DA_Evolution_PK01_Qwebek\tQwebek\tQwebek Kwipeck\tPK01\tKwipeck\t1\t5",
    f"{E}DA_Evolution_PK01_Prowler.DA_Evolution_PK01_Prowler\tProwler’s\t\tPK01\tKwipeck\t2\t8",
])


class TestImportVariants(unittest.TestCase):
    def import_into(self, variants_json: Path, dump: str) -> dict:
        dump_file = variants_json.parent / "variants.txt"
        dump_file.write_text(dump, encoding="utf-8")
        import_variants.main(str(dump_file), variants_json)
        return {entry["asset"]: entry for entry in json.loads(variants_json.read_text(encoding="utf-8"))}

    def test_names_and_ids(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            variants = self.import_into(Path(folder) / "variants.json", DUMP)
        self.assertEqual(variants["DA_Evolution_PK01_Base"]["name"], "Variant: Kwipeck")
        self.assertEqual(variants["DA_Evolution_PK01_Qwebek"]["name"], "Variant: Qwebek Kwipeck")
        # No creature name from the game: evolution and species name, curly quote straightened
        self.assertEqual(variants["DA_Evolution_PK01_Prowler"]["name"], "Variant: Prowler's Kwipeck")
        self.assertEqual(sorted(v["id"] for v in variants.values()), [847001, 847002, 847003])

    def test_reimport_keeps_ids(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            variants_json = Path(folder) / "variants.json"
            first = self.import_into(variants_json, DUMP)
            later = DUMP + f"\n{E}DA_Evolution_PK01_Aaa.DA_Evolution_PK01_Aaa\tAaa\tAaa Kwipeck\tPK01\tKwipeck\t1\t3"
            second = self.import_into(variants_json, later)
        for asset, entry in first.items():
            self.assertEqual(second[asset], entry)
        self.assertEqual(second["DA_Evolution_PK01_Aaa"]["id"], 847004)


if __name__ == "__main__":
    unittest.main()
