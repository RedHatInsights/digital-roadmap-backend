class CachedResult:
    """Wraps a list of row mappings to mimic AsyncResult.yield_per().mappings().

    This is needed to be able to cache response from HBI and reuse it in `systems_by_app_stream`
    and `get_relevant_systems`. Those functions expect a stream from the database and since reuse
    of those was chosen, we need to duck-type the result.
    """

    def __init__(self, rows):
        self._rows = rows

    def yield_per(self, _n):
        return self

    def mappings(self):
        return self

    def __aiter__(self):
        return self._async_iter()

    async def _async_iter(self):
        for row in self._rows:
            yield row
