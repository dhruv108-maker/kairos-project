"""Griffin integration boundary.

The repository currently contains no verified Griffin endpoint, authentication, or payload
contract. This adapter intentionally fails closed rather than fabricating a successful job.
Replace it only after the real integration contract has been confirmed.
"""


class GriffinIntegrationUnavailable(RuntimeError):
    pass


class GriffinAdapter:
    async def dispatch(self, *, project_id: str, report_id: str, evaluation_id: str, attempt_id: str) -> dict:
        raise GriffinIntegrationUnavailable(
            "Griffin dispatch is blocked: the base URL, authentication scheme, and request contract are not configured."
        )
