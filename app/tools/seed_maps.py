import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.build_db import (
    create_map,
    get_db,
    init_db,
    create_user,
)

def seed_maps(maps_dir: str = "data/maps"):
    maps_path = Path(maps_dir)
    if not maps_path.exists():
        return

    # Ensure database and tables exist
    init_db()

    json_files = list(maps_path.glob("*.json"))
    if not json_files:
        return

    for json_file in json_files:
        with open(json_file, 'r') as f:
            map_data = json.load(f)

        name = map_data.get("name", json_file.stem)
        width = map_data.get("width")
        height = map_data.get("height")
        if not width or not height:
            continue

        existing = None
        with get_db() as conn:
            cur = conn.execute("SELECT id FROM maps WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                continue

        # Insert map
        map_json = json.dumps(map_data)
        map_id = create_map(name, width, height, map_json, author_id=None)

if __name__ == "__main__":
    seed_maps()