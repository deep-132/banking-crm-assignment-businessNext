"""Explainability tool: renders why a specific customer was selected/scored.

Reads from already-computed state (scored_records) rather than re-querying
the DB or re-scoring — this is what lets the "why was X picked" follow-up be
served instantly, using the agent's cached session state.
"""


def explain_selection(customer_id: str, scored_records: list[dict]) -> str:
    match = next((r for r in scored_records if r["customer_id"] == customer_id), None)
    if match is None:
        return (
            f"I don't have {customer_id} in the current result set — run a search first, "
            "or check the customer ID."
        )

    hvc = match.get("hvc_breakdown", {})
    conv = match.get("conversion_breakdown", {})

    lines = [
        f"{match.get('name', customer_id)} ({customer_id}) — "
        f"HVC score {match.get('hvc_score')}/100, conversion score {match.get('conversion_score')}/100.",
        "",
        "High-value drivers:",
        f"  - Balance percentile: {hvc.get('balance_percentile')}",
        f"  - Income percentile: {hvc.get('income_percentile')}",
        f"  - Tenure percentile: {hvc.get('tenure_percentile')}",
        f"  - Product depth percentile: {hvc.get('product_depth_percentile')} "
        f"({hvc.get('active_product_count')} active products)",
        "",
        "Conversion signals:",
    ]
    for key, detail in conv.items():
        label = key.replace("_", " ")
        if "met" in detail:
            status = "yes" if detail["met"] else "no"
            lines.append(f"  - {label}: {status} (+{detail['points']} pts)")
        else:
            lines.append(f"  - {label}: {detail}")

    if match.get("recommended_product"):
        lines.append("")
        lines.append(f"Recommended: {match['recommended_product']} — {match.get('eligibility_reason', '')}")

    return "\n".join(lines)
