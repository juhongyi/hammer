import json

import httpx2
import pytest

from app.providers import ModelError, Models
from app.schemas import Outline
from app.settings import Settings
from tests.fake_models import ModelFixture


@pytest.mark.parametrize("envelope", ["response", "chat", "completion"])
async def test_workers_ai_response_and_live_granite_completion_envelopes(envelope):
    outline = ModelFixture().outline()
    response = json.dumps(outline, ensure_ascii=False)
    result = {
        "response": {"response": response},
        "chat": {"choices": [{"finish_reason": "stop", "message": {"content": response}}]},
        "completion": {"choices": [{"finish_reason": "stop", "text": response}]},
    }[envelope]
    async with httpx2.AsyncClient(
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(200, json={"success": True, "result": result})
        )
    ) as client:
        models = Models(
            Settings(_env_file=None, cloudflare_account_id="account", cloudflare_api_token="test"),
            client,
        )
        generated = await models.generate("instruction", {}, Outline, 100)
        assert generated.model_dump() == outline


async def test_provider_failures_do_not_echo_tokens_or_fake_success():
    async with httpx2.AsyncClient(
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(401, json={"detail": "secret-token"})
        )
    ) as client:
        models = Models(
            Settings(
                _env_file=None, cloudflare_account_id="account", cloudflare_api_token="secret-token"
            ),
            client,
        )
        with pytest.raises(ModelError, match="HTTP 401") as error:
            await models.generate("instruction", {}, Outline, 100)
        assert "secret-token" not in str(error.value)


async def test_invalid_choice_distribution_is_a_failure():
    response = {
        "model": "jev-1.13.0",
        "usage": {},
        "answers": {
            "decision": {
                "type": "choice",
                "choice": "outside",
                "probabilities": {"outside": 1},
                "confidence": 1,
            }
        },
    }
    async with httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(200, json=response))
    ) as client:
        models = Models(Settings(_env_file=None, typesafe_api_key="test"), client)
        with pytest.raises(ModelError, match="유효한 선택"):
            await models.choose({}, "choose", {"allowed": "description"})


async def test_malformed_llm_json_is_not_automatically_rewritten():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx2.Response(200, json={"success": True, "result": {"response": "invalid JSON"}})

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        models = Models(
            Settings(_env_file=None, cloudflare_account_id="account", cloudflare_api_token="test"),
            client,
        )
        with pytest.raises(ModelError, match="LLM 응답"):
            await models.generate("instruction", {}, Outline, 100)
        assert len(calls) == 1
