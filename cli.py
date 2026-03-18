#!/usr/bin/env python3
"""
CLI tool to check Singapore market/hawker centre closure status.

Usage:
    python cli.py today              - Show markets closed today
    python cli.py upcoming [days]    - Show upcoming closures (default: 30 days)
    python cli.py search <name>      - Search for a specific market
    python cli.py date <YYYY-MM-DD>  - Check closures on a specific date
"""

import sys
from datetime import date

from sg_market_status.checker import (
    get_closures_on_date,
    get_upcoming_closures,
    search_market,
)


def print_closures(closures, header=""):
    if header:
        print(f"\n{'='*60}")
        print(f"  {header}")
        print(f"{'='*60}")

    if not closures:
        print("\n  No closures found.\n")
        return

    for c in closures:
        closure_label = "Cleaning/Washing" if c["closure_type"] == "cleaning" else "Renovation/Other Works"
        print(f"\n  {c['name']}")
        print(f"    Type:    {closure_label}")
        print(f"    Period:  {c['start_date']} to {c['end_date']}")
        if c.get("remarks"):
            print(f"    Remarks: {c['remarks']}")
    print()


def print_search_results(results, query):
    print(f"\n{'='*60}")
    print(f"  Search results for: '{query}'")
    print(f"{'='*60}")

    if not results:
        print(f"\n  No markets found matching '{query}'.\n")
        return

    for r in results:
        print(f"\n  {r['name']}")
        if r.get("remarks"):
            print(f"    Remarks: {r['remarks']}")
        if not r["closures"]:
            print("    No scheduled closures found.")
        for c in r["closures"]:
            label = "Cleaning/Washing" if c["type"] == "cleaning" else "Renovation/Other Works"
            print(f"    - {label}: {c['start_date']} to {c['end_date']}")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "today":
        closures = get_closures_on_date()
        print_closures(closures, f"Markets closed today ({date.today().isoformat()})")

    elif command == "upcoming":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        closures = get_upcoming_closures(days_ahead=days)
        print_closures(closures, f"Upcoming closures (next {days} days)")

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python cli.py search <market name>")
            sys.exit(1)
        query = " ".join(sys.argv[2:])
        results = search_market(query)
        print_search_results(results, query)

    elif command == "date":
        if len(sys.argv) < 3:
            print("Usage: python cli.py date <YYYY-MM-DD>")
            sys.exit(1)
        closures = get_closures_on_date(sys.argv[2])
        print_closures(closures, f"Markets closed on {sys.argv[2]}")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
