# Deck: data vertexing, Xin r2 vs `original` vs `aurora_space`, against Xin's round-2 hand scan

`deck.pdf` (73 pages): setup, links, the hand-scan reference, vertex performance, predictions, then one page per event (67).

Rebuild (Polaris login node, read-only network access to Bee):

    S=<scratch>; P=<this repo>/issues/47-dv2max-aurora-space-model/prod_polaris
    python3 $P/slides/scripts/fetch_bee.py $P $P/../porting_sbndbuild03/tables $S/beecache      # Bee layers -> cache
    PYTHONPATH=<matplotlib> python3 scripts/make_deck.py $P $P/../porting_sbndbuild03/tables $S/beecache .
    tectonic -X compile deck.tex

Inputs:
- `../tables/handscan-xin-r2-{nuecc,ncpi0}.csv`: the scan sheet tabs;
- `../tables/handscan-vs-arms.csv`;
- `../tables/xin-r2-prod0811.csv`: Xin r2 exact vertices and setup, from `production-prep_wcgpu1`;
- `../../porting_sbndbuild03/tables/data-orig-vs-aur-*.csv`.
