"""Stand-in entry point for the login service until integration adds the app.

It does nothing but stay alive, so launchd's restart-on-crash can be tested.
Integration replaces it with ``hark.app``.
"""

import time

if __name__ == "__main__":
    while True:
        time.sleep(3600)
