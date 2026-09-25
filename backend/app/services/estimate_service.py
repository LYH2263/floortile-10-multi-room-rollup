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
    room_ids: list[int],
    tile_id: int,
    waste_pct: float | None,
    save: bool,
    note: str,
):
    """One tile + one waste across many rooms: per-room orders, then a grand total.

    Saved as a single run whose payload snapshots every room's numbers, so later
    room edits never rewrite history.
    """
    if not room_ids:
        raise HTTPException(422, "room_ids must not be empty")
    if len(set(room_ids)) != len(room_ids):
        raise HTTPException(422, "duplicate room ids")
    tile = tiles.get_tile(tile_id)
    if not tile:
        raise HTTPException(404, "tile not found")

    waste = float(waste_pct) if waste_pct is not None else settings_repo.get_waste_pct()

    per_room = []
    for room_id in room_ids:
        room = rooms.get_room(room_id)
        if not room:
            raise HTTPException(404, f"room {room_id} not found")
        if room.get("data_quality") == "dirty":
            raise HTTPException(
                422, f"room {room_id} marked dirty; fix dimensions before estimate"
            )
        calc = tile_count(room["length"], room["width"], tile["tile_l"], tile["tile_w"], waste)
        per_room.append(
            {
                "room_id": room_id,
                "room_name": room["name"],
                "length": room["length"],
                "width": room["width"],
                **calc,
            }
        )

    total = {
        "area_m2": round(sum(r["area_m2"] for r in per_room), 3),
        "raw_count": sum(r["raw_count"] for r in per_room),
        "order_count": sum(r["order_count"] for r in per_room),
        "waste_pct": waste,
    }

    run_id = None
    if save:
        payload = {
            "kind": "batch",
            "tile_id": tile_id,
            "tile_name": tile["name"],
            "waste_pct": waste,
            "rooms": per_room,
            "total": total,
        }
        run_id = history.insert_run(None, tile_id, waste, payload, note)

    return {
        "tile_id": tile_id,
        "tile": tile,
        "run_id": run_id,
        "rooms": per_room,
        "total": total,
    }
