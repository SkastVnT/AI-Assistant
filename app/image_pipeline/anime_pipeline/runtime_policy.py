"""Runtime network and content policy for the LOCAL anime pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit


class DeploymentProfile(str, Enum):
    LAPTOP_6GB = "laptop_6gb"
    PC_12GB = "pc_12gb"
    VPS_96GB = "vps_96gb"


class ContentMode(str, Enum):
    SFW = "sfw"
    ADULT_ONLY = "adult_only"


class ValidatorMode(str, Enum):
    LOCAL = "local"
    EXTERNAL_SFW_OPT_IN = "external_sfw_opt_in"
    OFF = "off"


class PolicyViolation(ValueError):
    """Raised when a request would violate a deployment policy."""


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_EXTERNAL_VALIDATOR_HOSTS = frozenset(
    {
        "api.openai.com",
        "generativelanguage.googleapis.com",
    }
)


def _profile(value: str | DeploymentProfile | None) -> DeploymentProfile:
    if isinstance(value, DeploymentProfile):
        return value
    try:
        return DeploymentProfile(str(value or DeploymentProfile.LAPTOP_6GB.value))
    except ValueError as exc:
        raise PolicyViolation(f"Unknown deployment profile: {value}") from exc


def _mode(value: str | ContentMode | None) -> ContentMode:
    if isinstance(value, ContentMode):
        return value
    try:
        return ContentMode(str(value or ContentMode.SFW.value))
    except ValueError as exc:
        raise PolicyViolation(f"Unknown content mode: {value}") from exc


def _validator(value: str | ValidatorMode | None) -> ValidatorMode:
    if isinstance(value, ValidatorMode):
        return value
    try:
        return ValidatorMode(str(value or ValidatorMode.LOCAL.value))
    except ValueError as exc:
        raise PolicyViolation(f"Unknown validator mode: {value}") from exc


def _origin_host(origin: str) -> str:
    parsed = urlsplit(origin if "://" in origin else f"http://{origin}")
    return (parsed.hostname or "").lower()


@dataclass(frozen=True)
class RuntimePolicy:
    """Fail-closed network policy for one standalone deployment."""

    profile: DeploymentProfile = DeploymentProfile.LAPTOP_6GB
    internal_hosts: frozenset[str] = field(default_factory=lambda: _LOOPBACK_HOSTS)
    external_validator_hosts: frozenset[str] = field(
        default_factory=lambda: _EXTERNAL_VALIDATOR_HOSTS
    )
    allow_external_sfw_validation: bool = False
    allow_web_research: bool = False
    allow_runtime_downloads: bool = False

    @classmethod
    def from_profile(
        cls,
        profile: str | DeploymentProfile,
        *,
        internal_origins: list[str] | tuple[str, ...] | None = None,
    ) -> "RuntimePolicy":
        selected = _profile(profile)
        configured_hosts = {
            _origin_host(origin) for origin in (internal_origins or ()) if origin
        }
        env_hosts = {
            _origin_host(host)
            for host in os.getenv("ANIME_PIPELINE_INTERNAL_HOSTS", "").split(",")
            if host.strip()
        }
        return cls(
            profile=selected,
            internal_hosts=frozenset(_LOOPBACK_HOSTS | configured_hosts | env_hosts),
            allow_external_sfw_validation=selected is DeploymentProfile.LAPTOP_6GB,
        )

    @classmethod
    def from_env(cls) -> "RuntimePolicy":
        return cls.from_profile(
            os.getenv("ANIME_PIPELINE_PROFILE", DeploymentProfile.LAPTOP_6GB.value)
        )

    @classmethod
    def from_config(cls, config: object) -> "RuntimePolicy":
        return cls.from_profile(
            getattr(config, "deployment_profile", DeploymentProfile.LAPTOP_6GB.value),
            internal_origins=list(getattr(config, "allowed_internal_origins", []) or []),
        )

    @property
    def offline_only(self) -> bool:
        return self.profile is not DeploymentProfile.LAPTOP_6GB

    def validate_request(
        self,
        *,
        content_mode: str | ContentMode = ContentMode.SFW,
        validator_mode: str | ValidatorMode = ValidatorMode.LOCAL,
        adult_verified: bool = False,
    ) -> None:
        content = _mode(content_mode)
        validator = _validator(validator_mode)

        if content is ContentMode.ADULT_ONLY:
            if self.profile is DeploymentProfile.LAPTOP_6GB:
                raise PolicyViolation("adult_only is disabled on laptop_6gb")
            if not adult_verified:
                raise PolicyViolation(
                    "adult_only requires explicit verification that every subject is an adult"
                )
            if validator is ValidatorMode.EXTERNAL_SFW_OPT_IN:
                raise PolicyViolation("adult_only content must never use an external validator")

        if validator is ValidatorMode.EXTERNAL_SFW_OPT_IN:
            if not self.allow_external_sfw_validation:
                raise PolicyViolation(
                    "external_sfw_opt_in is available only on laptop_6gb"
                )
            if content is not ContentMode.SFW:
                raise PolicyViolation("external validators are restricted to SFW requests")

    def assert_url(
        self,
        url: str,
        *,
        purpose: str,
        content_mode: str | ContentMode = ContentMode.SFW,
        validator_mode: str | ValidatorMode = ValidatorMode.LOCAL,
    ) -> None:
        """Raise when an HTTP endpoint is outside the request allowlist."""

        host = _origin_host(url)
        if not host:
            raise PolicyViolation(f"Invalid URL for {purpose}: {url!r}")
        if host in self.internal_hosts:
            return

        content = _mode(content_mode)
        validator = _validator(validator_mode)
        if (
            purpose == "external_validation"
            and host in self.external_validator_hosts
            and self.allow_external_sfw_validation
            and content is ContentMode.SFW
            and validator is ValidatorMode.EXTERNAL_SFW_OPT_IN
        ):
            return
        raise PolicyViolation(
            f"Outbound request blocked by {self.profile.value} policy: "
            f"purpose={purpose}, host={host}"
        )

    def allows_provider(
        self,
        provider: str,
        *,
        purpose: str,
        content_mode: str | ContentMode = ContentMode.SFW,
        validator_mode: str | ValidatorMode = ValidatorMode.LOCAL,
    ) -> bool:
        name = (provider or "").lower()
        if name.startswith(("local", "comfyui", "llama-server")):
            return True
        if name.startswith(("gpt", "openai", "gemini")):
            return (
                purpose == "external_validation"
                and self.allow_external_sfw_validation
                and _mode(content_mode) is ContentMode.SFW
                and _validator(validator_mode) is ValidatorMode.EXTERNAL_SFW_OPT_IN
            )
        return False

    def allows_location(self, location: str) -> bool:
        """Return whether a routed generation backend is part of this deployment."""

        return (location or "").lower() == "local"

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.value,
            "offline_only": self.offline_only,
            "allow_external_sfw_validation": self.allow_external_sfw_validation,
            "allow_web_research": self.allow_web_research,
            "allow_runtime_downloads": self.allow_runtime_downloads,
            "internal_hosts": sorted(self.internal_hosts),
        }
