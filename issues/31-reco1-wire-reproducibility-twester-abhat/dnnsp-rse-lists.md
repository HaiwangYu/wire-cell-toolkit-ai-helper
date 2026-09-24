## dnnsp RSE lists (Thomas vs Avinay, byte comparison of `recob::Wires_simtpc2d_dnnsp_DetSim`, reco1 files; identical verdicts in detsim)

### Non-identical dnnsp: 12 events

| RSE | g4 file (uuid) | entry | largest abs(A-B) | samples differing | sum Thomas | sum Avinay |
|---|---|---|---|---|---|---|
| 1/0/11 | 1726-908d-e4eb-b537 | 6 | 4.92 | 65 | 6664617 | 6664629 |
| 1/7/3 | 1e25-2b5b-7a6e-7dbb | 0 | 8.22 | 71 | 1.653651e+07 | 1.653635e+07 |
| 1/9/14 | 04cb-888a-ffaf-5808 | 7 | 1.89 | 105 | 4968439 | 4968434 |
| 1/9/15 | 04cb-888a-ffaf-5808 | 8 | 0.0513 | 26 | 8938158 | 8938157 |
| 1/10/5 | f356-90c1-0215-e140 | 1 | 2.77 | 75 | 6487970 | 6488052 |
| 1/10/6 | f356-90c1-0215-e140 | 2 | 11.6 | 187 | 1.127665e+07 | 1.127615e+07 |
| 1/12/10 | a964-b5d5-bad6-e3ac | 1 | 1.49 | 37 | 1.136329e+07 | 1.136328e+07 |
| 1/13/10 | 8b63-0aca-23d7-0ab0 | 2 | 1.38 | 26 | 8663352 | 8663333 |
| 1/16/2 | 006f-92f1-9cdf-bb8c | 1 | 2.28 | 33 | 1.295964e+07 | 1.295968e+07 |
| 1/17/7 | 3047-6e4e-6694-57cc | 2 | 1.7 | 81 | 7870654 | 7870636 |
| 1/17/12 | 3047-6e4e-6694-57cc | 3 | 1.95 | 26 | 9207455 | 9207426 |
| 1/19/8 | 199e-ec8c-cfaf-a30e | 2 | 2.84 | 125 | 7182780 | 7182709 |

One per line: 1/0/11 1/7/3 1/9/14 1/9/15 1/10/5 1/10/6 1/12/10 1/13/10 1/16/2 1/17/7 1/17/12 1/19/8

### Identical dnnsp: 76 events

| RSE | g4 file (uuid) | entry | gauss | wiener |
|---|---|---|---|---|
| 1/0/1 | 1726-908d-e4eb-b537 | 0 | same | same |
| 1/0/2 | 1726-908d-e4eb-b537 | 1 | DIFF | DIFF |
| 1/0/6 | 1726-908d-e4eb-b537 | 2 | same | same |
| 1/0/7 | 1726-908d-e4eb-b537 | 3 | same | same |
| 1/0/9 | 1726-908d-e4eb-b537 | 4 | same | same |
| 1/0/10 | 1726-908d-e4eb-b537 | 5 | same | same |
| 1/1/1 | 17b2-7a19-0173-eaa0 | 0 | same | same |
| 1/1/2 | 17b2-7a19-0173-eaa0 | 1 | same | same |
| 1/1/3 | 17b2-7a19-0173-eaa0 | 2 | same | same |
| 1/1/8 | 17b2-7a19-0173-eaa0 | 3 | DIFF | DIFF |
| 1/1/15 | 17b2-7a19-0173-eaa0 | 4 | DIFF | DIFF |
| 1/2/6 | 867c-fb44-c652-5d54 | 0 | same | same |
| 1/2/9 | 867c-fb44-c652-5d54 | 1 | same | same |
| 1/2/14 | 867c-fb44-c652-5d54 | 2 | same | same |
| 1/3/9 | 7459-87c8-75c1-6f29 | 0 | DIFF | DIFF |
| 1/3/11 | 7459-87c8-75c1-6f29 | 1 | DIFF | DIFF |
| 1/4/1 | 0d52-3071-98aa-b25d | 0 | same | same |
| 1/4/9 | 0d52-3071-98aa-b25d | 1 | same | same |
| 1/4/11 | 0d52-3071-98aa-b25d | 2 | same | same |
| 1/5/6 | 18ed-55fe-aa14-04ee | 0 | DIFF | DIFF |
| 1/5/9 | 18ed-55fe-aa14-04ee | 1 | same | same |
| 1/5/10 | 18ed-55fe-aa14-04ee | 2 | same | same |
| 1/5/13 | 18ed-55fe-aa14-04ee | 3 | same | same |
| 1/5/14 | 18ed-55fe-aa14-04ee | 4 | DIFF | DIFF |
| 1/6/1 | c4c4-468c-d5b6-e032 | 0 | DIFF | DIFF |
| 1/6/4 | c4c4-468c-d5b6-e032 | 1 | same | same |
| 1/6/7 | c4c4-468c-d5b6-e032 | 2 | DIFF | DIFF |
| 1/6/12 | c4c4-468c-d5b6-e032 | 3 | DIFF | DIFF |
| 1/7/8 | 1e25-2b5b-7a6e-7dbb | 1 | same | same |
| 1/7/11 | 1e25-2b5b-7a6e-7dbb | 2 | same | same |
| 1/7/13 | 1e25-2b5b-7a6e-7dbb | 3 | same | same |
| 1/8/1 | 4f08-780d-177d-1e84 | 0 | same | same |
| 1/8/2 | 4f08-780d-177d-1e84 | 1 | DIFF | DIFF |
| 1/8/4 | 4f08-780d-177d-1e84 | 2 | DIFF | DIFF |
| 1/8/9 | 4f08-780d-177d-1e84 | 3 | same | same |
| 1/8/13 | 4f08-780d-177d-1e84 | 4 | DIFF | DIFF |
| 1/8/14 | 4f08-780d-177d-1e84 | 5 | same | same |
| 1/8/15 | 4f08-780d-177d-1e84 | 6 | same | same |
| 1/9/2 | 04cb-888a-ffaf-5808 | 0 | DIFF | DIFF |
| 1/9/4 | 04cb-888a-ffaf-5808 | 1 | same | same |
| 1/9/5 | 04cb-888a-ffaf-5808 | 2 | same | same |
| 1/9/10 | 04cb-888a-ffaf-5808 | 3 | same | same |
| 1/9/11 | 04cb-888a-ffaf-5808 | 4 | DIFF | DIFF |
| 1/9/12 | 04cb-888a-ffaf-5808 | 5 | same | same |
| 1/9/13 | 04cb-888a-ffaf-5808 | 6 | DIFF | DIFF |
| 1/10/2 | f356-90c1-0215-e140 | 0 | same | same |
| 1/10/9 | f356-90c1-0215-e140 | 3 | same | same |
| 1/10/15 | f356-90c1-0215-e140 | 4 | DIFF | DIFF |
| 1/11/12 | 4f85-52bc-5313-6d4b | 0 | same | same |
| 1/11/14 | 4f85-52bc-5313-6d4b | 1 | DIFF | DIFF |
| 1/12/1 | a964-b5d5-bad6-e3ac | 0 | same | same |
| 1/12/11 | a964-b5d5-bad6-e3ac | 2 | same | same |
| 1/13/2 | 8b63-0aca-23d7-0ab0 | 0 | DIFF | DIFF |
| 1/13/3 | 8b63-0aca-23d7-0ab0 | 1 | DIFF | DIFF |
| 1/13/14 | 8b63-0aca-23d7-0ab0 | 3 | same | same |
| 1/13/15 | 8b63-0aca-23d7-0ab0 | 4 | same | same |
| 1/14/3 | 1846-ed4b-b660-a83f | 0 | same | same |
| 1/14/12 | 1846-ed4b-b660-a83f | 1 | DIFF | DIFF |
| 1/14/15 | 1846-ed4b-b660-a83f | 2 | same | same |
| 1/15/2 | 5bae-dbac-c685-fc52 | 0 | DIFF | DIFF |
| 1/15/3 | 5bae-dbac-c685-fc52 | 1 | DIFF | DIFF |
| 1/15/11 | 5bae-dbac-c685-fc52 | 2 | DIFF | DIFF |
| 1/15/15 | 5bae-dbac-c685-fc52 | 3 | DIFF | DIFF |
| 1/16/1 | 006f-92f1-9cdf-bb8c | 0 | DIFF | DIFF |
| 1/16/6 | 006f-92f1-9cdf-bb8c | 2 | same | same |
| 1/16/10 | 006f-92f1-9cdf-bb8c | 3 | same | same |
| 1/16/13 | 006f-92f1-9cdf-bb8c | 4 | same | same |
| 1/17/1 | 3047-6e4e-6694-57cc | 0 | DIFF | DIFF |
| 1/17/6 | 3047-6e4e-6694-57cc | 1 | DIFF | DIFF |
| 1/17/14 | 3047-6e4e-6694-57cc | 4 | DIFF | DIFF |
| 1/18/1 | a580-6d02-29fd-d041 | 0 | same | same |
| 1/19/3 | 199e-ec8c-cfaf-a30e | 0 | DIFF | DIFF |
| 1/19/5 | 199e-ec8c-cfaf-a30e | 1 | same | same |
| 1/19/9 | 199e-ec8c-cfaf-a30e | 3 | DIFF | DIFF |
| 1/19/10 | 199e-ec8c-cfaf-a30e | 4 | same | same |
| 1/19/15 | 199e-ec8c-cfaf-a30e | 5 | same | same |

One per line: 1/0/1 1/0/2 1/0/6 1/0/7 1/0/9 1/0/10 1/1/1 1/1/2 1/1/3 1/1/8 1/1/15 1/2/6 1/2/9 1/2/14 1/3/9 1/3/11 1/4/1 1/4/9 1/4/11 1/5/6 1/5/9 1/5/10 1/5/13 1/5/14 1/6/1 1/6/4 1/6/7 1/6/12 1/7/8 1/7/11 1/7/13 1/8/1 1/8/2 1/8/4 1/8/9 1/8/13 1/8/14 1/8/15 1/9/2 1/9/4 1/9/5 1/9/10 1/9/11 1/9/12 1/9/13 1/10/2 1/10/9 1/10/15 1/11/12 1/11/14 1/12/1 1/12/11 1/13/2 1/13/3 1/13/14 1/13/15 1/14/3 1/14/12 1/14/15 1/15/2 1/15/3 1/15/11 1/15/15 1/16/1 1/16/6 1/16/10 1/16/13 1/17/1 1/17/6 1/17/14 1/18/1 1/19/3 1/19/5 1/19/9 1/19/10 1/19/15
