"""Phase 0: reconcile the AHP survey scoring workbook against activities.csv.

Standalone, read-only, no DB writes. Prints a match report; the same loader
(``app.services.survey_ahp``) feeds the Phase 2 importer, so a clean report here
means the importer will match the same rows.
"""

from app.services.survey_ahp import MATCH_TOLERANCE_M, load_records


def _print_list(title: str, items: list, formatter) -> None:
    print(f"\n{title}: {len(items)}")
    for item in items:
        print(f"  - {formatter(item)}")


def main() -> dict:
    records, report = load_records()
    distances = [record["match_distance_m"] for record in records if record["match_distance_m"] is not None]

    print("Survey scoring reconciliation")
    print("=============================")
    print(f"scored halte (geojson) : {report['geojson_stops']}")
    print(f"activities.csv rows    : {report['activities_rows']}")
    print(f"matched                : {report['matched']}")
    print(f"tolerance              : {MATCH_TOLERANCE_M:.0f} m")
    if distances:
        print(f"coordinate match dist   : max {max(distances):.3f} m, exact {sum(1 for d in distances if d == 0)}/{len(distances)}")

    _print_list("Unmatched in xlsx (scored halte with no activities.csv source)", report["unmatched_geo"],
                lambda item: f"{item['title']!r} ({item['reason']})")
    _print_list("Unmatched in activities.csv (left on keyword fallback)", report["unmatched_csv"],
                lambda item: f"{item['source_id']} {item['title']!r} (nearest scored {item['nearest_scored_m']} m)")
    _print_list("Coordinate matches needing review (ambiguous within tolerance)", report["ambiguous_matches"],
                lambda item: f"{item['title']!r} -> {item['source_id']} + {item['second_source_id']} "
                             f"({item['second_distance_m']} m)")
    _print_list("Beyond tolerance", report["beyond_tolerance"],
                lambda item: f"{item.get('title')!r} nearest={item.get('nearest_source_id')} "
                             f"{item.get('distance_m')} m ({item.get('reason', 'over_tolerance')})")

    clean = not report["unmatched_geo"] and not report["beyond_tolerance"]
    print(f"\nresult: {'CLEAN' if clean else 'REVIEW REQUIRED'} "
          f"(unmatched_csv={len(report['unmatched_csv'])} left on keyword fallback by design)")
    return report


if __name__ == "__main__":
    main()
