"""The output budget must come from the model's real window, not the input clamp.

`config.max_model_tokens` bounds how much diff is sent, and `improve` lowers it further to
`pr_code_suggestions.max_context_tokens` while it runs. Deriving the output budget from that
clamp silently starves the response: on a 240k-context model clamped to 40k for input, a 22k
prompt left only ~17.5k tokens to answer in, which a reasoning model spends before it writes
anything.
"""

from pr_agent.algo.utils import get_max_tokens, get_model_context_window
from pr_agent.config_loader import get_settings

MODEL = "openai/some-self-hosted-model"


def _configure(max_model_tokens):
    get_settings().set("config.custom_model_max_tokens", 240000)
    get_settings().set("config.max_model_tokens", max_model_tokens)


def test_context_window_ignores_the_input_clamp():
    _configure(max_model_tokens=40000)
    assert get_max_tokens(MODEL) == 40000, "input budget stays clamped"
    assert get_model_context_window(MODEL) == 240000, "output budget uses the real window"


def test_context_window_matches_when_nothing_is_clamped():
    _configure(max_model_tokens=240000)
    assert get_model_context_window(MODEL) == get_max_tokens(MODEL) == 240000


def test_known_models_use_their_declared_window():
    _configure(max_model_tokens=1000)
    assert get_model_context_window("gpt-3.5-turbo") == 16000
