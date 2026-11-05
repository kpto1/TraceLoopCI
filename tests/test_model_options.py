import pytest

from app.services.evaluators.llm_judge import _parse_judge_output
from app.services.model_options import evaluation_options


@pytest.mark.parametrize(
    "value",
    [
        '{"score":true,"reason":"ok"}',
        '{"score":7.5,"reason":"ok"}',
        '{"score":99,"reason":"ok"}',
        "Attempt 9 failed",
        "[]",
    ],
)
def test_judge_rejects_ambiguous_scores(value):
    with pytest.raises(ValueError):
        _parse_judge_output(value)


def test_vendor_options_and_output_limits():
    assert evaluation_options("https://api.deepseek.com/v1/chat/completions", 512)["thinking"] == {
        "type": "disabled"
    }
    assert evaluation_options("https://example.com", 512) == {"max_tokens": 512}
    with pytest.raises(ValueError):
        evaluation_options("https://api.deepseek.com", 0)
