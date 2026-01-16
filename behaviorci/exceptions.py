"""Custom exceptions for BehaviorCI."""


class BehaviorCIError(Exception):
    """Base exception for BehaviorCI."""

    pass


class BundleError(BehaviorCIError):
    """Error loading or validating a bundle."""

    pass


class BundleNotFoundError(BundleError):
    """Bundle file not found."""

    pass


class BundleValidationError(BundleError):
    """Bundle configuration is invalid."""

    pass


class DatasetError(BehaviorCIError):
    """Error loading or parsing dataset."""

    pass


class ProviderError(BehaviorCIError):
    """Error with LLM provider."""

    pass


class ProviderConfigError(ProviderError):
    """Provider configuration error (e.g., missing API key)."""

    pass


class ProviderAPIError(ProviderError):
    """Error calling provider API."""

    pass


class ContractError(BehaviorCIError):
    """Error evaluating output contract."""

    pass


class SchemaValidationError(ContractError):
    """Output failed schema validation."""

    pass


class InvariantError(ContractError):
    """Output failed invariant check."""

    pass


class ThresholdError(BehaviorCIError):
    """Threshold evaluation failed."""

    pass
