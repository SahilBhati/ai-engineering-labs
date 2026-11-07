"""Stub adapters, one per port, for tests and the fake end-to-end turn."""

from hark.stubs.actions import StubAction, StubActionRegistry
from hark.stubs.brain import StubBrain
from hark.stubs.event_bus import InMemoryEventBus
from hark.stubs.router import StubRouter
from hark.stubs.safety_gate import StubSafetyGate
from hark.stubs.speech_to_text import StubSpeechToText
from hark.stubs.text_to_speech import StubTextToSpeech
from hark.stubs.wake_word import StubWakeWord

__all__ = [
    "InMemoryEventBus",
    "StubAction",
    "StubActionRegistry",
    "StubBrain",
    "StubRouter",
    "StubSafetyGate",
    "StubSpeechToText",
    "StubTextToSpeech",
    "StubWakeWord",
]
