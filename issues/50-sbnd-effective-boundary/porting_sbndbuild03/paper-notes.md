# arXiv 2101.05076 (MicroBooNE Wire-Cell cosmic-ray rejection): the effective boundary, verbatim extracts

Source: the arXiv PDF, text via `pdftotext -raw` (2026-11-17). Section V.

## V.A Effective boundary and fiducial volume
- Why: "the reconstructed TPC boundary from trajectories of charged particles deviate from the physical boundary because of the space charge effect … the reconstructed position along the wire plane appears to be closer to the detector center compared to its true position, making the effective detector boundary smaller than the actual active TPC boundary. … the deviation of the effective boundary from the physical boundary is larger for longer drift distances."
- How it is mapped: "The detector boundary is mapped out from the observed distribution of entry and exit points of cosmic muons. … small, non-muon like clusters, and clusters at the beginning or end of the TPC readout window, which are likely incompletely recorded, are removed."
- Sample: "approximately 1700 events from MicroBooNE data, each containing 20-30 cosmic muons".
- Projections: "The reconstructed 3D image points of the drift-time–corrected clusters are projected onto the X-Y (end view) and the X-Z (top view) planes. Figure 10 shows the zoomed-in views of the four corners at large drift distances, i.e. near the cathode plane at ≈256 cm in the X-direction, where the space charge effect is largest."
- Z dependence: "The projection of the effective detector boundary on the X-Y plane (end view) has a slight Z-dependence. This is studied by dividing the active TPC volume into 10 sub-volumes along the Z-axis. … the proposed detector boundary in Fig. 10 is conservatively estimated to be the inner boundary of all Z-slices. The effective boundary is also checked for different time periods during MicroBooNE data taking, and no clear time-dependence is observed."
- FV: "The fiducial volume is defined as the inner volume at 3 cm away from all sides of the effective detector boundary. The total fiducial mass of liquid argon is 80 tons, which is 94.2% of the full TPC active volume."
- Figures: Fig. 10 "The effective detector boundary (black lines) at the four corners on the cathode side of the detector" (panels: Bottom, Top in X-Y; Upstream, Downstream in X-Z). Fig. 11 "Effective detector boundaries in the Y-X plane for the sub-volume at different Z-slices."
- Not in the paper: the boundary's vertex coordinates. These are in the prototype's ToyFiducial (see the prototype survey).

## V.B TGM
- Extreme points: "the highest and lowest points in all three directions … and the highest and lowest points in the vertical direction along the principle axis, determined by … PCA".
- "If two of the extreme points are outside the fiducial volume boundary, this cluster is identified as a TGM … an event is tagged as fully contained if all extreme points are inside the fiducial volume."
- Special care: gaps from nonfunctional channels or inefficient signal processing ("re-examining test points along the principle axis of the cluster against the known locations of the nonfunctional channels, and against the deconvolved signals"); and two separate exiting tracks of a neutrino interaction (large-angle deflection check).

## V.C STM
- "the first stage of the STM tagging requires exactly one extreme point of the corresponding TPC cluster to be outside the fiducial volume." Then trajectory + dQ/dx fit, a kink search for the Michel electron, and KS tests over the last 35 cm.

## V.D LMM (light mismatch)
- "This check relies on the precise knowledge of the effective boundary that is distorted by the space charge effect, and so the Z-dependent effective boundary as shown in Fig. 11 is used." The cluster is re-placed in drift for another flash: two end points on the effective boundary give a TGM; only the entering point gives a possible STM (to the STM tagger); "moved along the drift direction such that both end points exactly touch the effective boundary" gives a TGM.
