# Draft: Slack message to Sne (from Haiwang)

Status: **DRAFT, not sent.** The PR #547 review is posted (pullrequestreview-5914254473).

---

Hi Sne, thanks for #547, and congrats on the aurora model! While you were away we tested your `dv2max-aurora-space` branch on sbndbuild03 and Aurora. It reproduces your hold-out exactly in-chain (all 0.9232, νe CC 0.956, νμ CC 0.959, NC 0.709 on 4,494 calls). On 141 independent MC events it gives 0.957 within 1 cm, against 0.837 for r7_cloud. Details in my review on the PR (https://github.com/WireCell/wire-cell-toolkit/pull/547#pullrequestreview-5914254473) and in https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/47.

One thing blocks the merge: the `aurora_space` bundle is on your wire-cell-data fork branch (`dv2max-sbnd-aurora-space`, e3c3a6c, the same bundle.json 51588842… we tested), but there's no PR into WireCell/wire-cell-data yet. #547 makes it the SBND default, so default jobs would fail at configure without it. Could you open that PR (like your #7), so the two can merge together?

Two small things:
- #544 and #547 conflict on one line of `sbnd-pr-stage.jsonnet`. I'd merge #544 first and resolve that line in yours, if that's OK with you.
- The `dl_vtx_dump_space` writer your README mentions is still on our fork. We'll send it as a follow-up PR on top of your `BeeClusterPoints`.

No rush this weekend. Thanks!
