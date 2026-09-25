from fastapi import HTTPException

from app.engines.tile_math import tile_count
from app.repositories import history, rooms, settings_repo, tiles


def run_estimate(room_id: int, tile_id: int, waste_pct: float | None, save: bool, note: str):
    room = rooms.get_room(room_id)
    if not room:
        raise HTTPException(404, "room not found")
    tile = tiles.get_tile(tile_id)
    if not tile:
        raise HTTPException(404, "tile not found")
    if room.get("data_quality") == "dirty":
        raise HTTPException(422, "room marked dirty; fix dimensions before estimate")

    waste = float(waste_pct) if waste_pct is not None else settings_repo.get_waste_pct()
    calc = tile_count(room["length"], room["width"], tile["tile_l"], tile["tile_w"], waste)

    run_id = None
    if save:
        payload = {**calc, "room_id": room_id, "tile_id": tile_id}
        run_id = history.insert_run(room_id, tile_id, waste, payload, note)

    return {
        "room_id": room_id,
        "tile_id": tile_id,
        "room": room,
        "tile": tile,
        "run_id": run_id,
        **calc,
    }


def run_batch_estimate(
    room_ids: list[int], tile_id: int, waste_pct: float | None, save: bool, note: str
):
    """One tile + one waste across many rooms: per-room orders plus a grand total.

    Saved as a single calc_runs row (room_id NULL) whose result_json snapshots
    every room's numbers, so later room edits never rewrite history.
    """
    if not room_ids:
        raise HTTPException(422, "room_ids must not be empty")
    if len(set(room_ids)) != len(room_ids):
        raise HTTPException(422, "duplicate room_ids")
    tile = tiles.get_tile(tile_id)
    if not tile:
        raise HTTPException(404, "tile not found")

    waste = float(waste_pct) if waste_pct is not None else settings_repo.get_waste_pct()

    per_room = []
    for room_id in room_ids:
        room = rooms.get_room(room_id)
        if not room:
            raise HTTPException(404, f"room not found: {room_id}")
        if room.get("data_quality") == "dirty":
            raise HTTPException(
                422, f"room '{room['name']}' marked dirty; fix dimensions before estimate"
            )
        calc = tile_count(room["length"], room["width"], tile["tile_l"], tile["tile_w"], waste)
        per_room.append({"room_id": room_id, "room_name": room["name"], **calc})

    totals = {
        "total_area_m2": round(sum(r["area_m2"] for r in per_room), 3),
        "total_raw_count": sum(r["raw_count"] for r in per_room),
        "total_order_count": sum(r["order_count"] for r in per_room),
    }

    run_id = None
    if save:
        payload = {
            "kind": "batch",
            "tile_id": tile_id,
            "room_ids": list(room_ids),
            "waste_pct": waste,
            "rooms": per_room,
            **totals,
        }
        run_id = history.insert_run(None, tile_id, waste, payload, note)

    return {
        "tile_id": tile_id,
        "tile": tile,
        "waste_pct": waste,
        "rooms": per_room,
        **totals,
        "run_id": run_id,
    }
