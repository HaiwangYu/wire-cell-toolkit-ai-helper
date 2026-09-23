"""Decode art ROOT baskets of vector<recob::Wire> (member-wise streamed) and
art::EventAuxiliary without ROOT dictionaries (uproot gives the bytes)."""
import struct
import numpy as np

def _bc(d, o):
    """ROOT byte count at o (kByteCountMask stripped); returns (nbytes_after, o+4)."""
    v = struct.unpack_from(">I", d, o)[0]
    assert v & 0x40000000, f"no bytecount at {o}: {v:#x}"
    return v & 0x3fffffff, o + 4

def decode_wires(d):
    """d: bytes of one basket (= one event) of recob::Wires_*.obj.
    Returns (channels uint32[n], views uint32[n], nominal_size int, rois)
    where rois[i] = list of (offset, float32 array)."""
    d = bytes(d)
    bc, o = _bc(d, 0)
    assert bc + 4 == len(d), (bc, len(d))
    ver = struct.unpack_from(">H", d, o)[0]; o += 2
    assert ver & 0x4000, f"vector<recob::Wire> not member-wise (ver={ver:#x})"
    o += 2  # recob::Wire class version
    n = struct.unpack_from(">I", d, o)[0]; o += 4
    ch = np.frombuffer(d, dtype=">u4", count=n, offset=o).astype(np.uint32); o += 4 * n
    vw = np.frombuffer(d, dtype=">u4", count=n, offset=o).astype(np.uint32); o += 4 * n
    rois = []
    nominal = None
    for i in range(n):
        bc, o = _bc(d, o); end = o + bc
        o += 2 + 4                       # sparse_vector version 0 + checksum
        nom = struct.unpack_from(">Q", d, o)[0]; o += 8
        if nominal is None: nominal = nom
        bc2, o = _bc(d, o)
        ver2 = struct.unpack_from(">H", d, o)[0]; o += 2
        o += 2 + 4                       # datarange_t version 0 + checksum
        nr = struct.unpack_from(">I", d, o)[0]; o += 4
        r = []
        if nr:
            assert ver2 & 0x4000
            # member-wise base class range_t: all offsets, then all lasts
            ol = np.frombuffer(d, dtype=">u8", count=2 * nr, offset=o); o += 16 * nr
            offs, lasts = ol[:nr], ol[nr:]
            # member-wise `values`: one header for all ranges, then n + floats each
            bc3, o = _bc(d, o); o += 2
            for k in range(nr):
                nv = struct.unpack_from(">I", d, o)[0]; o += 4
                vals = np.frombuffer(d, dtype=">f4", count=nv, offset=o).astype(np.float32); o += 4 * nv
                off, last = int(offs[k]), int(lasts[k])
                assert last - off == nv, (i, k, off, last, nv)
                r.append((off, vals))
        assert o == end, (i, o, end)
        rois.append(r)
    assert o == len(d), (o, len(d))
    return ch, vw, nominal, rois

def dense_wires(d, nch=None):
    """(channel x tick) float32 dense array from one basket."""
    ch, vw, nominal, rois = decode_wires(d)
    nch = nch or int(ch.max()) + 1
    arr = np.zeros((nch, nominal), dtype=np.float32)
    for c, r in zip(ch, rois):
        for off, vals in r:
            arr[c, off:off + vals.size] = vals
    return arr

def decode_rse(d):
    """(run, subrun, event) from one EventAuxiliary basket (one entry)."""
    d = bytes(d)
    bc, o = _bc(d, 0); o += bc               # processHistoryID_ (skipped)
    bc, o = _bc(d, o); o += 2                # EventID
    bc, o = _bc(d, o); o += 2                # SubRunID
    bc, o = _bc(d, o); o += 2                # RunID
    run, subrun, event = struct.unpack_from(">III", d, o)
    return run, subrun, event

if __name__ == "__main__":
    import sys, uproot
    t = uproot.open(sys.argv[1])["Events"]
    br = sys.argv[2] if len(sys.argv) > 2 else "recob::Wires_simtpc2d_dnnsp_DetSim.obj"
    ea = t["EventAuxiliary"]
    for i in range(t.num_entries):
        print("entry", i, "RSE", decode_rse(ea.basket(i).data))
        ch, vw, nom, rois = decode_wires(t[br].basket(i).data)
        nr = [len(r) for r in rois]
        nsamp = sum(v.size for r in rois for _, v in r)
        multi = [k for k, r in enumerate(rois) if len(r) >= 2][:3]
        print(f"  n={len(ch)} nominal={nom} ranges={sum(nr)} samples={nsamp} wires>=2 ranges: {sum(1 for x in nr if x>=2)} e.g. {[(int(ch[k]), [(o, v.size) for o,v in rois[k]]) for k in multi]}")
        a = dense_wires(t[br].basket(i).data)
        print("  dense", a.shape, "sum", float(a.sum()), "nonzero", int((a != 0).sum()))
