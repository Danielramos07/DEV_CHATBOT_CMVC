"""Placeholder TTS helper.

The original project used Coqui TTS here, but this cleaned core version does
not depend on any TTS backend. This module remains only as a stub to avoid
import errors if something accidentally references TTSTalker.
"""


class TTSTalker:
    def __init__(self, *_, **__):
        raise RuntimeError(
            "TTSTalker (text2speech) is not available in this cleaned SadTalker core. "
            "Provide your own TTS pipeline in the parent project instead."
        )

    def test(self, text, language="en"):
        raise RuntimeError(
            "TTSTalker.test() is not implemented in this core build. "
            "Use an external TTS service/pipeline."
        )
