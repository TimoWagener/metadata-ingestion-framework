import argparse
import json
from pathlib import Path
import sys

# Ensure src directory is in sys.path for direct script execution
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from metadata_ingestion_framework.compiler import MetadataCompiler


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile declarative metadata into an executable ingestion manifest."
    )
    parser.add_argument("--source", "-s", required=True, help="Source system name (e.g. m3, thinkwise)")
    parser.add_argument("--table", "-t", required=True, help="Table name (e.g. mitmas, osbstd, agreement)")
    parser.add_argument("--out", "-o", help="Optional output file path to write JSON manifest")
    args = parser.parse_args()

    compiler = MetadataCompiler()
    try:
        manifest = compiler.compile(args.source, args.table)
    except (FileNotFoundError, ValueError) as e:
        parser.error(str(e))
    json_output = json.dumps(manifest.to_dict(), indent=2)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_output, encoding="utf-8")
        print(f"Manifest written to {out_path}")
    else:
        print(json_output)


if __name__ == "__main__":
    main()
