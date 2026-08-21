#!/usr/bin/env python3
"""Merge the sp (space-point) nodes of SEVERAL single-event nugraph HDF5 files
into ONE multi-event Bee point-cloud zip.

Same per-event payload as sbnd/TensorSetLabeler/h5_sp_to_bee.py -- this only
adds the outer loop over files, because this campaign writes one h5 per event
(nugraph_r<run>_s<sub>_e<evt>.h5) rather than one h5 per job with many events.

  usage: nugraph_to_bee.py out.zip in0.h5 in1.h5 ...
"""
import sys, json, zipfile
import numpy as np
import h5py

out, ins = sys.argv[1], sys.argv[2:]
zf = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
idx = 0
for path in ins:
    f = h5py.File(path, "r")
    for key in f["dataset"].keys():
        r = f["dataset"][key][()]
        run = int(np.asarray(r["metadata/run"]))
        sub = int(np.asarray(r["metadata/subrun"]))
        evt = int(np.asarray(r["metadata/event"]))
        pos = np.asarray(r["sp/pos"], dtype=float)          # mm
        sem = np.asarray(r["sp/y_semantic"]).astype(int)
        inst = np.asarray(r["sp/y_instance"]).astype(int)
        feat = np.asarray(r["sp/features"], dtype=float)    # [charge, reco_cluster_id, ...]
        # Truth present -> colour by trackid, q = nu(1)/cosmic(0)/ghost(-1).
        # Truth absent  -> colour by reco_cluster_id, q = charge.
        if not bool(np.all(inst == -1)):
            q = np.where(sem == 0, 1.0, np.where(sem == 1, 0.0, -1.0))
            cid = inst
            mode = "truth nu=%d cosmic=%d ghost=%d" % (
                int((sem == 0).sum()), int((sem == 1).sum()), int((sem == -1).sum()))
        else:
            q = feat[:, 0]
            cid = feat[:, 1].astype(int)
            mode = "input-only, %d reco clusters" % len(set(cid.tolist()))
        obj = {"runNo": str(run), "subRunNo": str(sub), "eventNo": str(evt),
               "geom": "sbnd", "type": "nugraph_sp",
               "x": (pos[:, 0] / 10.0).tolist(),   # mm -> cm, Bee wants cm
               "y": (pos[:, 1] / 10.0).tolist(),
               "z": (pos[:, 2] / 10.0).tolist(),
               "q": q.tolist(),
               "cluster_id": cid.tolist(), "real_cluster_id": cid.tolist()}
        zf.writestr("data/%d/%d-nugraph_sp.json" % (idx, idx), json.dumps(obj))
        print("  [%d] rse=(%d,%d,%d) %d sp  %s" % (idx, run, sub, evt, len(sem), mode))
        idx += 1
zf.close()
print("wrote %s : %d event(s)" % (out, idx))
