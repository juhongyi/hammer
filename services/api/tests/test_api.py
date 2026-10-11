import asyncio

import pytest


async def wait_for_generation(client, presentation_id):
    for _ in range(400):
        response = await client.get(f"/api/presentations/{presentation_id}")
        data = response.json()
        if data["status"] in {"awaiting_validation", "failed"}:
            return data
        await asyncio.sleep(0.01)
    raise AssertionError("generation timed out")


async def create_and_generate(client, text="한국어 발표"):
    created = await client.post("/api/presentations", json={"text": text})
    assert created.status_code == 201, created.text
    data = created.json()
    started = await client.post(f"/api/presentations/{data['id']}/generate")
    assert started.status_code == 200, started.text
    return await wait_for_generation(client, data["id"])


@pytest.mark.parametrize("count", [6, 30])
async def test_confirmed_count_order_and_edits_survive_generation(api_client, count):
    client, fixture, _ = api_client
    created = (
        await client.post(
            "/api/presentations", json={"text": "test:30" if count == 30 else "한국어"}
        )
    ).json()
    outline = created["outline"]
    outline["pages"][1]["key_message"] = "수정된 목표: 고객 이탈률 12% 감소"
    saved = await client.put(f"/api/presentations/{created['id']}/outline", json=outline)
    assert saved.status_code == 200
    await client.post(f"/api/presentations/{created['id']}/generate")
    data = await wait_for_generation(client, created["id"])
    assert data["status"] == "awaiting_validation", data["error"]
    assert len(data["slides"]) == count
    assert all(slide["trace"]["planning"]["model"] == "jev-1.13.0" for slide in data["slides"])
    assert all(slide["trace"]["faithfulness"]["choice"] == "faithful" for slide in data["slides"])
    properties = data["slides"][0]["trace"]["writing_schema"]["properties"]
    assert properties["blocks"]["maxItems"] == 1
    assert [slide["index"] for slide in data["slides"]] == list(range(count))
    assert data["slides"][1]["content"]["key_message"] == outline["pages"][1]["key_message"]
    assert any(
        "수정된 목표" in str(request["payload"].get("messages", [])) for request in fixture.requests
    )


async def test_latest_ontology_is_sent_to_jev_and_existing_result_is_immutable(api_client):
    client, _, _ = api_client
    first = await create_and_generate(client)
    document = (await client.get("/api/ontology")).json()
    for layout in document["layouts"]:
        if layout["id"] == "comparison":
            layout["enabled"] = False
        if layout["id"] == "list":
            layout["purpose"] = "운영자가 수정한 최신 비교 목적"
    saved = await client.put("/api/ontology", json=document)
    assert saved.status_code == 200
    assert (await client.put("/api/ontology", json=document)).status_code == 409
    second = await create_and_generate(client)
    assert second["snapshot"]["version"] == 2
    comparison = second["slides"][3]
    criteria = comparison["trace"]["selection_request"]["questions"]["decision"]["criteria"]
    assert set(criteria) == {"list"}
    assert criteria["list"]["purpose"] == "운영자가 수정한 최신 비교 목적"
    original = (await client.get(f"/api/presentations/{first['id']}")).json()
    assert original["snapshot"] == first["snapshot"]
    assert original["slides"] == first["slides"]


async def test_completion_requires_every_page_and_successful_render_report(api_client):
    client, _, _ = api_client
    data = await create_and_generate(client)
    path = f"/api/presentations/{data['id']}/validation"
    report = {"run_id": data["run_id"], "font_loaded": True, "pages": []}
    assert (await client.post(path, json=report)).status_code == 422
    report["pages"] = [{"index": i, "issues": []} for i in range(6)]
    report["run_id"] = "stale"
    assert (await client.post(path, json=report)).status_code == 409
    report["run_id"] = data["run_id"]
    report["pages"][2]["issues"] = ["내용이 잘립니다."]
    failed = (await client.post(path, json=report)).json()
    assert failed["status"] == "failed"
    assert failed["outline"] == data["outline"]
    await client.post(f"/api/presentations/{data['id']}/generate")
    retry = await wait_for_generation(client, data["id"])
    report["run_id"] = retry["run_id"]
    report["pages"][2]["issues"] = []
    completed = (await client.post(path, json=report)).json()
    assert completed["status"] == "completed"
    assert (
        await client.put(f"/api/presentations/{data['id']}/outline", json=data["outline"])
    ).status_code == 409


async def test_model_failure_and_no_candidate_preserve_outline(api_client):
    client, fixture, _ = api_client
    data = (await client.post("/api/presentations", json={"text": "한국어"})).json()
    fixture.fail = True
    await client.post(f"/api/presentations/{data['id']}/generate")
    failed = await wait_for_generation(client, data["id"])
    assert failed["status"] == "failed"
    assert "HTTP 529" in failed["error"]
    assert failed["outline"] == data["outline"]
    fixture.fail = False
    document = (await client.get("/api/ontology")).json()
    document["layouts"][0]["enabled"] = False
    await client.put("/api/ontology", json=document)
    await client.post(f"/api/presentations/{data['id']}/generate")
    no_candidate = await wait_for_generation(client, data["id"])
    assert no_candidate["status"] == "failed"
    assert "디자인이 없습니다" in no_candidate["error"]
    assert no_candidate["outline"] == data["outline"]


async def test_outline_page_count_is_protected_and_invalid_data_is_rejected(api_client):
    client, _, _ = api_client
    data = (await client.post("/api/presentations", json={"text": "한국어"})).json()
    pages = data["outline"]["pages"]
    pages.append(pages[-1])
    assert (
        await client.put(f"/api/presentations/{data['id']}/outline", json={"pages": pages})
    ).status_code == 422
    document = (await client.get("/api/ontology")).json()
    document["layouts"][0]["supports"] = []
    assert (await client.put("/api/ontology", json=document)).status_code == 422


async def test_unfaithful_model_copy_is_never_completed_or_sent_to_layout_selection(api_client):
    client, fixture, _ = api_client
    created = (await client.post("/api/presentations", json={"text": "한국어"})).json()
    fixture.unfaithful = True
    await client.post(f"/api/presentations/{created['id']}/generate")
    data = await wait_for_generation(client, created["id"])
    assert data["status"] == "failed"
    assert "새로운 사실" in data["error"]
    assert data["outline"] == created["outline"]
    assert data["slides"] == []
    assert not any("content" in request["payload"].get("state", {}) for request in fixture.requests)
