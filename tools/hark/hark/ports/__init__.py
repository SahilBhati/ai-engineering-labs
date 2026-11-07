"""Ports: the interfaces every lane builds against. No implementations here."""

from hark.ports.actions import Action, ActionRegistry
from hark.ports.brain import Brain, BrainReply, BrainRequest
from hark.ports.event_bus import EventBus, Handler
from hark.ports.router import FastAction, Route, Router, ToBrain
from hark.ports.safety_gate import GateDecision, SafetyGate, ToolCall
from hark.ports.speech_to_text import SpeechToText, Transcript
from hark.ports.text_to_speech import TextToSpeech
from hark.ports.wake_word import Wake, WakeWord

__all__ = [
    "Action",
    "ActionRegistry",
    "Brain",
    "BrainReply",
    "BrainRequest",
    "EventBus",
    "FastAction",
    "GateDecision",
    "Handler",
    "Route",
    "Router",
    "SafetyGate",
    "SpeechToText",
    "TextToSpeech",
    "ToBrain",
    "ToolCall",
    "Transcript",
    "Wake",
    "WakeWord",
]
