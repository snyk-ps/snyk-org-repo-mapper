"""Predefined Bitbucket Server integration settings for Stage 2.3."""

from __future__ import annotations

from typing import Any

SETTINGS_PROFILE_ID = "bitbucket-server-default-v1"

BITBUCKET_SERVER_INTEGRATION_SETTINGS: dict[str, Any] = {
    "autoDepUpgradeLimit": 2,
    "autoDepUpgradeIgnoredDependencies": [],
    "autoDepUpgradeEnabled": False,
    "autoDepUpgradeMinAge": 21,
    "pullRequestTestCodeEnabled": False,
    "pullRequestTestCodeSeverity": "high",
    "pullRequestTestEnabled": False,
    "pullRequestFailOnAnyVulns": False,
    "pullRequestFailOnlyForHighSeverity": True,
    "autoRemediationPrs": {
        "backlogPrsEnabled": False,
        "backlogPrStrategy": "vuln",
        "freshPrsEnabled": False,
        "usePatchRemediation": False,
    },
    "manualRemediationPrs": {
        "useManualPatchRemediation": False,
    },
    "dockerfileSCMEnabled": True,
}
