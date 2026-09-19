#!/usr/bin/env python3
"""dump_truth.py <out.tsv> <reco1.root> [reco1.root ...]
Event-level GENIE truth from SBND reco1 artROOT files, read with bare PyROOT (no LArSoft framework needed;
only the nusimdata dictionary library must be loadable -- on FNAL `source sbnd/setup-local-opt.sh` provides it).
One row per (event, true neutrino).  Columns:
  run subrun event n_nu inu nu_pdg ccnc mode interaction_type E_nu_MeV vtx_x_cm vtx_y_cm vtx_z_cm t_ns lepton_pdg target_pdg n_genie_particles in_active_tpc
in_active_tpc: 1 if the true vertex is inside the SBND active volume (|x|<200, |y|<200, 0<z<500 cm); rockbox events carry dirt/cryostat interactions too.
ccnc: 0=CC 1=NC.  mode: GENIE simb::int_type_ (0 QE, 1 Res, 2 DIS, 3 Coh, 10 MEC, ...).  interaction_type: simb::int_type_ full code.
Branch: simb::MCTruths_generator__GenieGen.  (the corsika MCTruth is the cosmic overlay; not dumped)."""
import sys, ROOT; ROOT.gErrorIgnoreLevel = ROOT.kError
out = open(sys.argv[1], 'w'); BR = 'simb::MCTruths_generator__GenieGen.'
out.write('run\tsubrun\tevent\tn_nu\tinu\tnu_pdg\tccnc\tmode\tinteraction_type\tE_nu_MeV\tvtx_x_cm\tvtx_y_cm\tvtx_z_cm\tt_ns\tlepton_pdg\ttarget_pdg\tn_genie_particles\tin_active_tpc\n')
nev = 0
for path in sys.argv[2:]:
    f = ROOT.TFile.Open(path); t = f.Get('Events')
    t.SetBranchStatus('*', 0); t.SetBranchStatus(BR + '*', 1); t.SetBranchStatus('EventAuxiliary*', 1)
    for i in range(t.GetEntries()):
        t.GetEntry(i); a = t.EventAuxiliary.id(); v = getattr(t, BR + 'obj'); nev += 1   # split sub-branch '<wrapper>.obj' is the std::vector<simb::MCTruth>
        if v.size() == 0:
            out.write('%d\t%d\t%d\t0\t-1\t0\t-1\t-1\t-1\t0\t0\t0\t0\t0\t0\t0\t0\t0\n' % (a.run(), a.subRun(), a.event())); continue
        for k, m in enumerate(v):
            nu = m.GetNeutrino(); p = nu.Nu(); lep = nu.Lepton()
            intpc = 1 if (abs(p.Vx()) < 200. and abs(p.Vy()) < 200. and 0. < p.Vz() < 500.) else 0
            out.write('%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%.2f\t%.2f\t%.2f\t%.2f\t%.1f\t%d\t%d\t%d\t%d\n' % (
                a.run(), a.subRun(), a.event(), v.size(), k, p.PdgCode(), nu.CCNC(), nu.Mode(), nu.InteractionType(),
                p.E()*1000., p.Vx(), p.Vy(), p.Vz(), p.T(), lep.PdgCode(), nu.Target(), m.NParticles(), intpc))
    f.Close()
out.close(); print('events', nev, '->', sys.argv[1])
