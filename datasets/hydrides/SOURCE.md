# Source and provenance

## Citation

Sanna, A., Cerqueira, T. F. T., Cubuk, E. D., Errea, I. & Fang, Y.-W.
*Search for thermodynamically stable ambient-pressure superconducting hydrides
in the GNoME database.* **Communications Physics** (2026).

- Journal: https://www.nature.com/articles/s42005-026-02552-4
- Preprint (used for this transcription): https://arxiv.org/html/2508.19781v1
- Open access via PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC12992110/

## What this file contains

`gnome_hydride_candidates.csv` is a **verbatim transcription of Table 1 and
Table 2** of that paper: 18 vacancy-ordered double perovskites and 4
fluorite-like hydrides whose Allen-Dynes Tc exceeds 4.2 K.

Columns transcribed directly from the paper:

| Column | Source |
|---|---|
| `mat_id` | GNoME material id, as printed |
| `formula` | as printed |
| `structure_family` | from the table caption |
| `lambda_ep` | electron-phonon coupling constant λ |
| `omega_log_k` | logarithmic average phonon frequency ω_log, in K |
| `tc_allen_dynes_k` | T_c computed with the Allen-Dynes formula, in K |
| `tc_refined_k` | beyond-Allen-Dynes estimate — **only LiZrH6Ru has one** |

## What this file does NOT contain

**No score, weight, ranking, confidence or feasibility value in this repository
comes from the paper.** The authors did not publish any such quantity.

Everything beyond the columns above is computed by `triage/` from these
published values using rules that are written down and versioned:

- `tc_confidence` — derived in `triage/derive.py` from the coupling regime and
  whether a beyond-Allen-Dynes calculation exists.
- `synthesis_feasibility` — derived from elemental composition using the rule
  table in `configs/triage/element_feasibility.yaml`. This is **analyst
  judgment encoded as an auditable rule**, not data.
- `information_value` — derived from the two above.

The boundary is deliberate: this CSV holds only what was published, so the line
between measurement and judgment is a file boundary rather than a convention.

## Known ambiguity — read before quoting the refined Tc

The paper reports several beyond-Allen-Dynes estimates for LiZrH6Ru:
**30.7 K** (improved harmonic), **32.0 K** (with quantum/anharmonic effects via
SSCHA), **17 K** (multiband Eliashberg), and **14.2 K** (Eliashberg with
ab initio Coulomb interactions). The abstract's headline figure — "a maximum
critical temperature of 17 K" — is what `tc_refined_k` records.

This transcription was made from the preprint HTML. **Verify against the
published PDF before using any of these numbers in anything consequential.**
The authors' own caveat is the important one: for this compound the careful
treatment landed at roughly half the Allen-Dynes value, which they call
"an uncommon deviation". That disagreement is signal, and the triage layer
treats it as such rather than averaging it away.
