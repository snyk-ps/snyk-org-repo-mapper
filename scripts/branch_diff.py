import json
import sys


def main():
    if len(sys.argv) != 3:
        print(
            f"Usage: {sys.argv[0]} <discovery.json> <output.json>"
        )
        sys.exit(1)

    discovery_file = sys.argv[1]
    output_file = sys.argv[2]
    diff_file = "diff.json"

    # Load output.json
    with open(output_file, "r", encoding="utf-8") as f:
        output_data = json.load(f)

    # Load discovery.json
    with open(discovery_file, "r", encoding="utf-8") as f:
        discovery_data = json.load(f)

    # Build lookup by repository_name
    output_lookup = {
        row["repository_name"]: row
        for row in output_data
    }

    diffs = []

    for row in discovery_data.get("rows", []):
        repository_name = f'BB/{row["repository_name"]}'

        output_row = output_lookup.get(repository_name)

        # Repository not found in output.json
        if not output_row:
            continue

        production_branch = row.get("production_branch")
        target_reference = output_row.get("target_reference")

        if production_branch != target_reference:
            diffs.append(
                {
                    "apm_code": output_row.get("apm_code"),
                    "repository_name": repository_name,
                    "production_branch": production_branch,
                    "target_reference": target_reference,
                }
            )

    with open(diff_file, "w", encoding="utf-8") as f:
        json.dump(diffs, f, indent=2)

    print(f"Found {len(diffs)} differences")
    print(f"Results written to {diff_file}")


if __name__ == "__main__":
    main()
