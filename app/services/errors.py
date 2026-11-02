class UpstreamProviderError(Exception):
    """Wraps exceptions from the model/embedding provider SDK."""

    def __init__(self, operation: str, exc: Exception):
        self.operation = operation
        self.exc_type = type(exc).__name__
        super().__init__(f"upstream provider failed during {operation}: {type(exc).__name__}")
