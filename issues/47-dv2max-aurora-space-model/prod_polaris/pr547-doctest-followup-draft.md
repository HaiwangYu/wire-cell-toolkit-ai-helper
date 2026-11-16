# Draft: follow-up comment on PR #547 (the doctest counts promised in the review)

Status: **DRAFT, not posted.** Source: porting_sbndbuild03, issue 47 comment 6905426354 (commit b52d99f).

---

Doctests on this PR's head, as promised. Build: master `7710c43b` + `c9f61962` (merges cleanly), on sbndbuild03 (SL7, Python 3.9.15):

| suite | result |
|---|---|
| clus doctest | 508/508 |
| pyutil doctest | 17/17 |
| root doctest | 11/11 |
| `test_dv2max.py` | 33 OK |
| `test_dv2max_space.py` | 20 OK |

- **Leak test (`c9f61962`):** 30/30 runs pass (20 unpinned, 10 pinned to one core). Batch growth is 34, 0, 0, 0 in every run, so the smallest batch is 0, well under the limit of 500. The previous version also passed 20/20 here, so the Polaris failures don't reproduce with Python 3.9. We did not check that the new limit still catches an injected leak.
- **Bundle:** the hash pinned in `clus.jsonnet` (`51588842…8a74`) equals the bundle on your `dv2max-sbnd-aurora-space` branch; all files and `SHA256SUMS` verify.

So the only open item from the review is the wire-cell-data PR.
