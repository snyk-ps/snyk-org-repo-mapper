import json
import os
import urllib.request
from urllib.parse import urljoin

GROUP_ID = os.environ["SNYK_GROUP_ID"]
API_TOKEN = os.environ["SNYK_API_KEY"]

BASE_URL = "https://api.scotiabank.my.snyk.io"

HEADERS = {
    "Authorization": API_TOKEN,
    "Accept": "*/*"
}


def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


results = []

# Get all organizations in the group
orgs_url = (
    f"{BASE_URL}/rest/groups/{GROUP_ID}/orgs"
    "?version=2026-03-25&limit=100"
)

while orgs_url:
    print(f"Fetching organizations: {orgs_url}")

    orgs_response = get_json(orgs_url)

    for org in orgs_response.get("data", []):
        org_id = org["id"]
        org_name = org["attributes"]["name"]

        print(f"Processing org: {org_name}")

        #
        # Build a map of:
        # target_id -> target_reference
        #
        # Only include projects whose origin is
        # "bitbucket-server"
        #
        target_reference_map = {}

        projects_url = (
            f"{BASE_URL}/rest/orgs/{org_id}/projects"
            "?version=2026-03-25&limit=100"
        )

        while projects_url:
            projects_response = get_json(projects_url)

            for project in projects_response.get("data", []):
                try:
                    origin = project["attributes"].get("origin")

                    if origin != "bitbucket-server":
                        continue

                    target_id = (
                        project["relationships"]["target"]["data"]["id"]
                    )

                    target_reference = (
                        project["attributes"].get("target_reference")
                    )

                    # Keep first matching project only
                    if target_id not in target_reference_map:
                        target_reference_map[target_id] = target_reference

                except KeyError:
                    continue

            next_projects = (
                projects_response.get("links", {}).get("next")
            )

            projects_url = (
                urljoin(BASE_URL, next_projects)
                if next_projects
                else None
            )

        print(
            f"  Found {len(target_reference_map)} "
            f"Bitbucket Server targets"
        )

        #
        # Get targets for the organization
        #
        targets_url = (
            f"{BASE_URL}/rest/orgs/{org_id}/targets"
            "?version=2026-03-25&limit=100&exclude_empty=false"
        )

        while targets_url:
            targets_response = get_json(targets_url)

            for target in targets_response.get("data", []):
                target_id = target["id"]

                # Skip targets that do not have a
                # Bitbucket Server project
                if target_id not in target_reference_map:
                    continue

                results.append(
                    {
                        "apm_code": org_name,
                        "repository_name": target["attributes"]["display_name"],
                        "target_reference": target_reference_map[target_id]
                    }
                )

            next_targets = (
                targets_response.get("links", {}).get("next")
            )

            targets_url = (
                urljoin(BASE_URL, next_targets)
                if next_targets
                else None
            )

        print(f"  Completed {org_name}")

    next_orgs = orgs_response.get("links", {}).get("next")

    orgs_url = (
        urljoin(BASE_URL, next_orgs)
        if next_orgs
        else None
    )

with open("output.json", "w", encoding="utf-8") as fp:
    json.dump(results, fp, indent=2)

print(f"Created output.json with {len(results)} entries")
