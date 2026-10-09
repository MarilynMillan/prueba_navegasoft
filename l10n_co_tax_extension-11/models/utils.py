# -*- coding: utf-8 -*-


def nav_unique_tax_recordset(taxes):
    """Normalize taxes by origin id to avoid NewId/_origin duplicates in onchange."""
    env = taxes.env
    unique_ids = set()
    for tax in taxes:
        tid = tax._origin.id or tax.id
        if isinstance(tid, int):
            unique_ids.add(tid)
    return env['account.tax'].browse(sorted(unique_ids))


def nav_merge_preserving_non_threshold(
    previous_taxes,
    computed_taxes,
    threshold_tax_ids,
    include_computed_non_threshold=False,
):
    manual_keep = previous_taxes.filtered(lambda t: t.id not in threshold_tax_ids)
    if include_computed_non_threshold:
        manual_keep |= computed_taxes.filtered(lambda t: t.id not in threshold_tax_ids)
    threshold_now = computed_taxes.filtered(lambda t: t.id in threshold_tax_ids)
    return nav_unique_tax_recordset(manual_keep | threshold_now)


def nav_line_stable_key(line):
    """Stable key across onchange/compute cycles for new and persisted lines."""
    return line._origin.id or line.id or id(line)


def nav_get_threshold_tax_ids(env, company):
    if not company:
        return set()
    return set(
        env['account.tax'].search([
            ('company_id', '=', company.id),
            ('base_taxes', '!=', False),
        ]).ids
    )
