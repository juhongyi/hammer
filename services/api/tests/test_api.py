from copy import deepcopy

from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import Pipeline
from test_pipeline import FakeModels, FakeRenderer


def test_http_flow_and_structure_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api.sqlite3"))
    with TestClient(app) as client:
        app.state.pipeline = Pipeline(app.state.store, FakeModels(), FakeRenderer)
        assert client.post("/runs", json={"text": "   "}).status_code == 422
        id_ = client.post("/runs", json={"text": "한국어 발표 요청"}).json()["id"]
        run = client.get(f"/runs/{id_}").json()
        assert run["status"] == "outline_ready"
        assert client.get(f"/runs/{id_}/slides/0").status_code == 409
        changed = deepcopy(run["outline"])
        changed["pages"].reverse()
        assert client.post(f"/runs/{id_}/confirm", json={"outline": changed}).status_code == 422
        changed = deepcopy(run["outline"])
        changed["chapters"][0]["page_ids"].append(changed["chapters"][1]["page_ids"].pop(0))
        assert client.post(f"/runs/{id_}/confirm", json={"outline": changed}).status_code == 422
        assert client.post(f"/runs/{id_}/confirm", json={"outline": run["outline"]}).status_code == 202
        assert client.get(f"/runs/{id_}").json()["status"] == "completed"
        assert client.post(f"/runs/{id_}/confirm", json={"outline": run["outline"]}).status_code == 409
        assert client.get(f"/runs/{id_}/slides/0").status_code == 200
        assert client.get(f"/runs/{id_}/slides/99").status_code == 404
        assert client.get("/runs/missing").status_code == 404
        ontology = client.get("/ontology").json()
        ontology["layouts"][2]["enabled"] = False
        assert client.post("/ontology/validate", json=ontology).json() == {"valid": True}
        assert client.put("/ontology", json=ontology).status_code == 200
        assert not client.get("/ontology").json()["layouts"][2]["enabled"]
        ontology["layouts"][2]["slots"][0]["max_length"] = 600
        assert client.put("/ontology", json=ontology).status_code == 422
