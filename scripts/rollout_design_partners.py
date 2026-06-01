import argparse
import csv

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Enroll and promote design partners from CSV")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--csv", default="docs/design-partners-template.csv")
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.token}"}

    with open(args.csv, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            tenant_slug = row["tenant_slug"]
            owner_email = row["owner_email"]
            company_name = row["company_name"]
            cohort = row["cohort"]
            rollout_percentage = int(row["rollout_percentage"])

            provision = requests.post(
                f"{args.base_url}/v1/admin/provision",
                json={
                    "name": company_name,
                    "slug": tenant_slug,
                    "owner_email": owner_email,
                    "plan": "starter",
                },
                headers=headers,
                timeout=10,
            )
            if provision.status_code not in {200, 400}:
                print(f"Provision failed for {tenant_slug}: {provision.status_code}")
                return 1

            body = provision.json() if provision.status_code == 200 else {}
            tenant_id = body.get("tenant_id")
            if not tenant_id:
                print(f"Tenant likely exists for {tenant_slug}; skipping rollout update")
                continue

            enroll = requests.post(
                f"{args.base_url}/v1/admin/design-partners/{tenant_id}/enroll",
                json={"cohort": cohort, "launch_notes": "automated rollout tool"},
                headers=headers,
                timeout=10,
            )
            if enroll.status_code != 200:
                print(f"Enroll failed for {tenant_slug}: {enroll.status_code}")
                return 1

            promote = requests.post(
                f"{args.base_url}/v1/admin/design-partners/{tenant_id}/promote",
                json={"rollout_percentage": rollout_percentage},
                headers=headers,
                timeout=10,
            )
            if promote.status_code != 200:
                print(f"Promote failed for {tenant_slug}: {promote.status_code}")
                return 1

            print(f"Processed {tenant_slug} at {rollout_percentage}% rollout")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
