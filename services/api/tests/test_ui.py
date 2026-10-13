"""Real Next.js + FastAPI + Chromium flow; only external models are fixtures."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from playwright.sync_api import sync_playwright
import pytest


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for(url, process, log_path):
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(log_path.read_text())
        try:
            if httpx.get(url, timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Server did not become ready: {url}\n{log_path.read_text()}")


@pytest.fixture
def servers(tmp_path):
    api_dir = Path(__file__).resolve().parents[1]
    root = api_dir.parent.parent
    web_dir = root / "apps/web"
    if not (web_dir / "node_modules").exists():
        pytest.skip("UI tests require npm ci in apps/web")
    api_port, web_port = unused_port(), unused_port()
    api_url, web_url = f"http://127.0.0.1:{api_port}", f"http://localhost:{web_port}"
    api_log, web_log = tmp_path / "api.log", tmp_path / "web.log"
    processes = []
    with api_log.open("w") as api_output, web_log.open("w") as web_output:
        try:
            env = {**os.environ, "DATABASE_PATH": str(tmp_path / "browser.sqlite3"),
                   "PYTHONPATH": f"{api_dir}{os.pathsep}{api_dir / 'tests'}"}
            backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "browser_server:app", "--port", str(api_port)],
                                       cwd=api_dir, env=env, stdout=api_output, stderr=subprocess.STDOUT)
            processes.append(backend)
            wait_for(api_url + "/health", backend, api_log)
            web = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(web_port)], cwd=web_dir,
                env={**os.environ, "API_URL": api_url, "NEXT_TELEMETRY_DISABLED": "1"},
                stdout=web_output, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(web)
            wait_for(web_url, web, web_log)
            yield api_url, web_url
        finally:
            for process in reversed(processes):
                if process is not backend:
                    import signal
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
                process.wait(timeout=15)


def test_browser_edit_render_ontology_and_failed_candidate_flow(servers):
    api_url, web_url = servers
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # The first client-side history request confirms hydration has attached
        # the controlled form handlers before typing into the server HTML.
        with page.expect_response(lambda response: response.url.endswith("/api/runs")):
            page.goto(web_url)
        page.get_by_label("발표 주제·요청·원고").fill("한국어 고객 만족도 개선 발표")
        page.get_by_role("button", name="개요 생성", exact=True).click()
        confirm = page.get_by_role("button", name="개요 확정 및 슬라이드 생성")
        confirm.wait_for(timeout=20000)
        page.get_by_label("표지 제목", exact=True).fill("사용자 수정 표지")
        page.get_by_label("핵심 메시지").first.fill("사용자가 확정한 중요 내용")
        confirm.click()
        page.get_by_role("heading", name="3. 전체 슬라이드 · 6장").wait_for(timeout=30000)
        assert page.locator("iframe").count() == 6
        assert page.frame_locator("iframe").nth(0).locator(".title").inner_text() == "사용자 수정 표지"
        assert page.frame_locator("iframe").nth(1).locator(".message").inner_text() == "사용자가 확정한 중요 내용"
        run = httpx.get(api_url + "/runs").json()[0]
        before = httpx.get(api_url + f"/runs/{run['id']}").json()
        page.get_by_role("button", name="온톨로지 관리", exact=True).click()
        editor = page.get_by_label("온톨로지 JSON")
        import json
        page.wait_for_function("document.querySelector('.json-editor').value.length > 0")
        ontology = json.loads(editor.input_value())
        ontology["layouts"][2]["enabled"] = False
        ontology["types"][2]["purpose"] = "변경한 표현 목적"
        editor.fill(json.dumps(ontology, ensure_ascii=False))
        save = page.get_by_role("button", name="검수한 정의·사용 여부 적용")
        assert save.is_disabled()
        page.get_by_role("button", name="수정 내용 검수", exact=True).click()
        page.get_by_text("검수 통과.", exact=False).wait_for()
        save.click()
        page.get_by_text("적용 완료.", exact=False).wait_for()
        assert httpx.get(api_url + f"/runs/{run['id']}").json() == before
        page.get_by_role("button", name="프레젠테이션", exact=True).click()
        page.get_by_role("button", name="개요 생성", exact=True).click()
        confirm.wait_for(timeout=20000)
        confirm.click()
        page.get_by_role("alert").filter(has_text="후보가 없습니다").wait_for(timeout=30000)
        assert page.locator("iframe").count() == 0
        assert page.get_by_label("표지 제목", exact=True).is_visible()
        page.reload()
        page.get_by_label("저장된 실행").select_option(run["id"])
        page.get_by_role("heading", name="3. 전체 슬라이드 · 6장").wait_for()
        assert not errors
        browser.close()
