# Issue 37 rerun summary (mix 0, mix 1, mix 2, mix 500, sol 0, sol 1, sol 2, sol 3)

## Gates

| event | stock == stored (wf, DivRec) | legacy == stored (wf, DivRec) | default: DivRec == stored | default: wf == stored | default: dup hits | track: Xe DivRec == stored |
|---|---|---|---|---|---|---|
| mix 0 | yes, yes | yes, yes | yes | no (expected where legacy overlapped) | 0 | yes |
| mix 1 | yes, yes | yes, yes | yes | no (expected where legacy overlapped) | 0 | yes |
| mix 2 | yes, yes | yes, yes | yes | no (expected where legacy overlapped) | 0 | yes |
| mix 500 | yes, yes | yes, yes | yes | no (expected where legacy overlapped) | 1 | yes |
| sol 0 | yes, yes | yes, yes | yes | yes | 0 | yes |
| sol 1 | yes, yes | yes, yes | yes | yes | 0 | yes |
| sol 2 | yes, yes | yes, yes | yes | yes | 0 | yes |
| sol 3 | yes, yes | yes, yes | yes | yes | 0 | yes |

## mix (4 events: 0, 1, 2, 500)

| build | snippets | samples | stored again (frac) | of which differ | same-start snippets | hits | dup hits (frac) | hit PE | dup PE (frac) | pre-trigger RMS (median) | MARLEY Ar PE / Ar photon | MARLEY Ar+ArExt PE | MARLEY total PE | all PE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stock (4) | 889893 | 376557784 | 59202403 (0.1572) | 0 | 126710 | 51978 | 6396 (0.1231) | 1348666 | 212537 (0.1576) | 2.740 | 0.1319 | 402 | 2067 | 4717371 |
| legacy (4) | 889893 | 376557784 | 59202403 (0.1572) | 0 | 126710 | 51978 | 6396 (0.1231) | 1348666 | 212537 (0.1576) | 2.740 | 0.1319 | 402 | 2067 | 4717371 |
| default (4) | 697270 | 290027392 | 210681 (0.0007) | 0 | 0 | 43806 | 1 (0.0000) | 1083572 | 9 (0.0000) | 2.496 | 0.1319 | 402 | 2067 | 4717371 |
| track (4) | 769694 | 335689074 | 276237 (0.0008) | 0 | 0 | 53900 | 0 (0.0000) | 1330030 | 0 (0.0000) | 2.497 | 0.2028 | 618 | 2283 | 5690757 |

## sol (4 events: 0, 1, 2, 3)

| build | snippets | samples | stored again (frac) | of which differ | same-start snippets | hits | dup hits (frac) | hit PE | dup PE (frac) | pre-trigger RMS (median) | MARLEY Ar PE / Ar photon | MARLEY Ar+ArExt PE | MARLEY total PE | all PE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stock (4) | 369 | 135408 | 0 (0.0000) | 0 | 0 | 39 | 0 (0.0000) | 889 | 0 (0.0000) | 2.544 | 0.1845 | 721 | 2374 | 2453 |
| legacy (4) | 369 | 135408 | 0 (0.0000) | 0 | 0 | 39 | 0 (0.0000) | 889 | 0 (0.0000) | 2.544 | 0.1845 | 721 | 2374 | 2453 |
| default (4) | 369 | 135408 | 0 (0.0000) | 0 | 0 | 39 | 0 (0.0000) | 889 | 0 (0.0000) | 2.544 | 0.1845 | 721 | 2374 | 2453 |
| track (4) | 374 | 138446 | 15 (0.0001) | 0 | 0 | 44 | 0 (0.0000) | 952 | 0 (0.0000) | 2.462 | 0.2250 | 855 | 2508 | 2587 |
