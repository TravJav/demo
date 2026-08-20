from dataclasses import dataclass


class ProcessorNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class ProcessorOperation:
    name: str
    request_format: str
    success_statuses: tuple[str, ...]
    failure_statuses: tuple[str, ...]


@dataclass(frozen=True)
class ProcessorProfile:
    name: str
    display_name: str
    protocol: str
    sandbox_url: str
    local_mock_url: str
    auth_model: str
    supported_currencies: tuple[str, ...]
    amount_unit: str
    token_prefix: str
    idempotency_supported: bool
    refund_supported: bool
    status_lookup_supported: bool
    pricing: str
    retry_notes: str
    soft_decline_codes: tuple[str, ...]
    hard_decline_codes: tuple[str, ...]
    system_error_codes: tuple[str, ...]
    operations: tuple[ProcessorOperation, ...]
    source_documents: tuple[str, ...]


class KnowledgeBaseService:
    def __init__(self) -> None:
        self._processors = {
            profile.name: profile
            for profile in (
                self._stripely_profile(),
                self._adyenta_profile(),
            )
        }

    def list_processors(self, currency: str | None = None) -> list[ProcessorProfile]:
        processors = list(self._processors.values())
        if currency is None:
            return processors

        target = currency.upper()
        return [
            processor
            for processor in processors
            if target in {code.upper() for code in processor.supported_currencies}
        ]

    def get_processor(self, name: str) -> ProcessorProfile:
        processor = self._processors.get(name.lower())
        if processor is None:
            raise ProcessorNotFoundError
        return processor

    def _stripely_profile(self) -> ProcessorProfile:
        return ProcessorProfile(
            name="stripely",
            display_name="Stripely",
            protocol="json_https",
            sandbox_url="https://api.stripely.test/v1",
            local_mock_url="http://localhost:4001/v1",
            auth_model="Authorization bearer token",
            supported_currencies=("USD", "GBP"),
            amount_unit="minor",
            token_prefix="tok_st_",
            idempotency_supported=True,
            refund_supported=True,
            status_lookup_supported=True,
            pricing="2.9% + $0.30 per successful charge",
            retry_notes=(
                "Native charge idempotency is available for 24 hours. "
                "Do not retry hard declines such as stolen_card."
            ),
            soft_decline_codes=("insufficient_funds",),
            hard_decline_codes=("stolen_card",),
            system_error_codes=("api_error",),
            operations=(
                ProcessorOperation(
                    name="create_token",
                    request_format="POST /tokens JSON",
                    success_statuses=("201",),
                    failure_statuses=("400", "401"),
                ),
                ProcessorOperation(
                    name="create_charge",
                    request_format="POST /charges JSON",
                    success_statuses=("201",),
                    failure_statuses=("400", "401", "402", "500"),
                ),
                ProcessorOperation(
                    name="retrieve_charge",
                    request_format="GET /charges/{id} JSON",
                    success_statuses=("200",),
                    failure_statuses=("404",),
                ),
                ProcessorOperation(
                    name="create_refund",
                    request_format="POST /refunds JSON",
                    success_statuses=("201",),
                    failure_statuses=("400", "401"),
                ),
            ),
            source_documents=(
                "Processor Integrations (2)/STRIPELY.md",
                "Processor Integrations (2)/stripely.openapi.yaml",
            ),
        )

    def _adyenta_profile(self) -> ProcessorProfile:
        return ProcessorProfile(
            name="adyenta",
            display_name="Adyenta",
            protocol="soap_1_1",
            sandbox_url="https://pal.adyenta.test/soap/Payment/v12",
            local_mock_url="http://localhost:4002/soap/Payment/v12",
            auth_model="Username and password in SOAP header",
            supported_currencies=("USD", "EUR"),
            amount_unit="major",
            token_prefix="ADYC-",
            idempotency_supported=False,
            refund_supported=True,
            status_lookup_supported=True,
            pricing="1.8% + EUR 0.12 per successful charge",
            retry_notes=(
                "AuthoriseAndCapture has no processor idempotency. "
                "The gateway must prevent duplicate submissions."
            ),
            soft_decline_codes=("51", "05"),
            hard_decline_codes=("43",),
            system_error_codes=("905",),
            operations=(
                ProcessorOperation(
                    name="create_card_token",
                    request_format="SOAPAction CreateCardToken",
                    success_statuses=("200",),
                    failure_statuses=("500 Fault 010", "500 Fault 702"),
                ),
                ProcessorOperation(
                    name="authorise_and_capture",
                    request_format="SOAPAction AuthoriseAndCapture",
                    success_statuses=("200 AUTHORISED",),
                    failure_statuses=("200 REFUSED", "500 Fault 905"),
                ),
                ProcessorOperation(
                    name="refund_transaction",
                    request_format="SOAPAction RefundTransaction",
                    success_statuses=("200 REFUNDED",),
                    failure_statuses=("500 Fault 702",),
                ),
                ProcessorOperation(
                    name="get_transaction_status",
                    request_format="SOAPAction GetTransactionStatus",
                    success_statuses=("200",),
                    failure_statuses=("500 Fault 702",),
                ),
            ),
            source_documents=(
                "Processor Integrations (2)/ADYENTA.md",
                "Processor Integrations (2)/adyenta.wsdl",
            ),
        )
