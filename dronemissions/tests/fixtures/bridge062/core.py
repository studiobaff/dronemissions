"""Test-only dependencies for the unchanged 0.6.2 archive client."""
import hashlib
class BridgeError(Exception): pass
def digest(data): return hashlib.sha256(data).hexdigest()
