"""Hark: voice control for the Mac.

Layout (ports and adapters / hexagonal architecture):
- ``hark.ports``  — the interfaces every lane builds against.
- ``hark.events`` — turn events published on the event bus.
- ``hark.turn``   — runs one turn through the ports and times each stage.
- ``hark.stubs``  — fake adapters for tests.
"""
