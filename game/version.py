"""Single source of truth for the application version.

This one string drives everything: the release tag the CI publishes, the
installer version, and what the running app reports and compares against when
checking for updates. Bump it here and push to `main` to cut a release.
"""

VERSION = "1.1.0"
