"""Batch estimate: many rooms, one tile + one waste, one saved run.

Runs against a throwaway DB (DATA_DIR is set before any app import).
Seed data: rooms 1=客餐厅(clean), 2=狭长走廊(clean), 3=脏数据-负宽(dirty);
tiles 1=600x600, 2=800x800, 3=脏数据-零面积(dirty).
"""

import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="floortile-test-")

import pytest
from fastapi import HTTPException

from app import seed
from app.db import connect
from app.repositories import history
from app.services import estimate_service

seed.init_db()


def _run_count() -> int:
    conn = connect()
    try:
        return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]
    finally:
        conn.close()


def test_batch_totals_are_sum_of_per_room_orders():
    batch = estimate_service.run_batch_estimate([1, 2], 1, None, False, "")
    single1 = estimate_service.run_estimate(1, 1, None, False, "")
    single2 = estimate_service.run_estimate(2, 1, None, False, "")

    assert [r["room_id"] for r in batch["rooms"]] == [1, 2]
    by_id = {r["room_id"]: r for r in batch["rooms"]}
    assert by_id[1]["order_count"] == single1["order_count"]
    assert by_id[2]["order_count"] == single2["order_count"]
    assert batch["total_raw_count"] == single1["raw_count"] + single2["raw_count"]
    assert batch["total_order_count"] == single1["order_count"] + single2["order_count"]
    assert batch["run_id"] is None  # preview does not save


def test_single_room_batch_equals_individual_estimate():
    batch = estimate_service.run_batch_estimate([1], 1, None, False, "")
    single = estimate_service.run_estimate(1, 1, None, False, "")
    assert batch["rooms"][0]["order_count"] == single["order_count"]
    assert batch["total_raw_count"] == single["raw_count"]
    assert batch["total_order_count"] == single["order_count"]


def test_unified_waste_override_applies_to_every_room():
    batch = estimate_service.run_batch_estimate([1, 2], 1, 10.0, False, "")
    assert batch["waste_pct"] == 10.0
    assert all(r["waste_pct"] == 10.0 for r in batch["rooms"])


@pytest.mark.parametrize(
    "room_ids,status",
    [([], 422), ([1, 1], 422), ([1, 999], 404), ([1, 3], 422)],
    ids=["empty", "duplicate", "missing", "dirty"],
)
def test_invalid_batches_fail_and_history_does_not_grow(room_ids, status):
    before = _run_count()
    with pytest.raises(HTTPException) as excinfo:
        estimate_service.run_batch_estimate(room_ids, 1, None, True, "")
    assert excinfo.value.status_code == status
    assert _run_count() == before


def test_unknown_tile_fails_and_history_does_not_grow():
    before = _run_count()
    with pytest.raises(HTTPException) as excinfo:
        estimate_service.run_batch_estimate([1], 999, None, True, "")
    assert excinfo.value.status_code == 404
    assert _run_count() == before


def test_save_adds_exactly_one_run_with_per_room_breakdown():
    before = _run_count()
    res = estimate_service.run_batch_estimate([1, 2], 1, None, True, "合并下单")
    assert _run_count() == before + 1

    run = history.get_run(res["run_id"])
    assert run["room_id"] is None  # merged run is not tied to one room
    assert run["result"]["kind"] == "batch"
    assert [r["room_id"] for r in run["result"]["rooms"]] == [1, 2]
    assert run["result"]["total_order_count"] == res["total_order_count"]
    assert run["result"]["total_order_count"] == sum(
        r["order_count"] for r in run["result"]["rooms"]
    )

    listed = [r for r in history.list_runs() if r["id"] == res["run_id"]][0]
    assert listed["result"]["total_order_count"] == res["total_order_count"]


def test_saved_batch_snapshot_survives_later_room_edits():
    res = estimate_service.run_batch_estimate([1, 2], 1, None, True, "")
    before_run = history.get_run(res["run_id"])
    before_orders = {r["room_id"]: r["order_count"] for r in before_run["result"]["rooms"]}

    conn = connect()
    try:
        conn.execute("UPDATE rooms SET length=?, width=? WHERE id=?", (99.0, 99.0, 1))
        conn.commit()
        after_run = history.get_run(res["run_id"])
        after_orders = {r["room_id"]: r["order_count"] for r in after_run["result"]["rooms"]}
        assert after_orders == before_orders
        assert after_run["result"]["total_order_count"] == before_run["result"]["total_order_count"]
    finally:
        conn.execute("UPDATE rooms SET length=?, width=? WHERE id=?", (6.0, 4.5, 1))
        conn.commit()
        conn.close()
