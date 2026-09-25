import pytest
from fastapi import HTTPException

from app import seed
from app.db import connect
from app.repositories import history
from app.services import estimate_service


@pytest.fixture(autouse=True)
def fresh_db():
    """Every test gets a pristine seeded DB (rooms 1/2 clean, 3 dirty)."""
    seed.init_db()
    conn = connect()
    try:
        for table in ("calc_runs", "rooms", "tiles", "settings"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()
    seed.init_db()


def run_count() -> int:
    conn = connect()
    try:
        return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]
    finally:
        conn.close()


def test_batch_total_is_sum_of_per_room_orders():
    res = estimate_service.run_batch_estimate([1, 2], 1, 8.0, False, "")
    singles = [estimate_service.run_estimate(rid, 1, 8.0, False, "") for rid in (1, 2)]
    assert [r["order_count"] for r in res["rooms"]] == [s["order_count"] for s in singles]
    assert res["total"]["order_count"] == sum(s["order_count"] for s in singles)
    assert res["total"]["raw_count"] == sum(s["raw_count"] for s in singles)
    assert res["total"]["area_m2"] == round(sum(s["area_m2"] for s in singles), 3)


def test_single_room_batch_matches_single_estimate():
    batch = estimate_service.run_batch_estimate([1], 1, None, False, "")
    single = estimate_service.run_estimate(1, 1, None, False, "")
    assert batch["rooms"][0]["order_count"] == single["order_count"]
    assert batch["total"]["order_count"] == single["order_count"]
    assert batch["total"]["raw_count"] == single["raw_count"]


@pytest.mark.parametrize(
    "room_ids,status",
    [
        ([], 422),        # empty list
        ([1, 1], 422),    # duplicate ids
        ([1, 999], 404),  # unknown id
        ([1, 3], 422),    # room 3 is dirty
    ],
)
def test_invalid_batches_fail_without_growing_history(room_ids, status):
    before = run_count()
    with pytest.raises(HTTPException) as exc:
        estimate_service.run_batch_estimate(room_ids, 1, None, True, "")
    assert exc.value.status_code == status
    assert run_count() == before


def test_save_inserts_exactly_one_run_with_breakdown():
    before = run_count()
    res = estimate_service.run_batch_estimate([1, 2], 1, 8.0, True, "合并下单")
    assert run_count() == before + 1
    run = history.get_run(res["run_id"])
    assert run["room_id"] is None
    assert run["result"]["kind"] == "batch"
    assert [r["room_id"] for r in run["result"]["rooms"]] == [1, 2]
    assert run["result"]["total"]["order_count"] == res["total"]["order_count"]


def test_saved_run_is_snapshot_immune_to_room_resize():
    res = estimate_service.run_batch_estimate([1, 2], 1, 8.0, True, "")
    original = [r["order_count"] for r in res["rooms"]]

    conn = connect()
    try:
        conn.execute("UPDATE rooms SET length=99.0 WHERE id=1")
        conn.commit()
    finally:
        conn.close()

    run = history.get_run(res["run_id"])
    assert [r["order_count"] for r in run["result"]["rooms"]] == original
    assert run["result"]["rooms"][0]["length"] == 6.0
    assert run["result"]["total"]["order_count"] == res["total"]["order_count"]
