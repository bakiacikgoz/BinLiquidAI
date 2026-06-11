from __future__ import annotations

from binliquid.model_providers.models import DataClass, ProviderPolicy
from binliquid.model_providers.native.types import (
    ProviderRequestedTool,
    ProviderRequestedToolType,
    ProviderToolPolicyDecision,
    ProviderToolPolicyStatus,
)

DENY_REASON_BY_TOOL_TYPE = {
    ProviderRequestedToolType.BUILTIN_WEB_SEARCH: "BUILTIN_WEB_SEARCH_DEFAULT_DENY",
    ProviderRequestedToolType.BUILTIN_FILE_SEARCH: "BUILTIN_FILE_SEARCH_DEFAULT_DENY",
    ProviderRequestedToolType.BUILTIN_COMPUTER_USE: "BUILTIN_COMPUTER_USE_DEFAULT_DENY",
    ProviderRequestedToolType.MCP: "MCP_TOOL_DEFAULT_DENY",
    ProviderRequestedToolType.SERVER_TOOL: "SERVER_TOOL_DEFAULT_DENY",
    ProviderRequestedToolType.UNKNOWN: "UNKNOWN_TOOL_DEFAULT_DENY",
}


def evaluate_provider_tool_policy(
    *,
    requested_tool: ProviderRequestedTool,
    provider_policy: ProviderPolicy,
    data_class: DataClass,
    execution_surface: str = "provider_native_adapter",
) -> ProviderToolPolicyDecision:
    _ = data_class, execution_surface
    if requested_tool.tool_type != ProviderRequestedToolType.CUSTOM_FUNCTION:
        return ProviderToolPolicyDecision(
            status=ProviderToolPolicyStatus.DENY,
            requested_tool_type=requested_tool.tool_type,
            reason_code=DENY_REASON_BY_TOOL_TYPE.get(
                requested_tool.tool_type,
                "UNKNOWN_TOOL_DEFAULT_DENY",
            ),
            execution_allowed=False,
            proposal_allowed=False,
            approval_required=False,
            tool_name=requested_tool.name,
        )

    if not provider_policy.allow_tool_calls:
        return ProviderToolPolicyDecision(
            status=ProviderToolPolicyStatus.DENY,
            requested_tool_type=requested_tool.tool_type,
            reason_code="CUSTOM_TOOL_POLICY_DENY",
            execution_allowed=False,
            proposal_allowed=False,
            approval_required=False,
            tool_name=requested_tool.name,
        )

    approval_required = provider_policy.requires_approval_for_tool_calls or requested_tool.mutating
    return ProviderToolPolicyDecision(
        status=ProviderToolPolicyStatus.REQUIRES_APPROVAL
        if approval_required
        else ProviderToolPolicyStatus.ALLOW_PROPOSAL,
        requested_tool_type=requested_tool.tool_type,
        reason_code="CUSTOM_TOOL_PROPOSAL_REQUIRES_APPROVAL"
        if approval_required
        else "CUSTOM_TOOL_PROPOSAL_ONLY",
        execution_allowed=False,
        proposal_allowed=True,
        approval_required=approval_required,
        tool_name=requested_tool.name,
    )
