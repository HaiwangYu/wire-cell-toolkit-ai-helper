local wc = import "wirecell.jsonnet";
local g = import "pgraph.jsonnet";
local f = import "pgrapher/common/funcs.jsonnet";
local sim_maker = import "pgrapher/common/sim/nodes.jsonnet";


// return some nodes, includes base sim nodes.
// YZ-KIT (issue 46): copy of sbndcode v10_14_02_03 pgrapher/experiment/sbnd/sim.jsonnet.
// The only change: an optional yzmap argument (an IYZMap config object).  When
// it is null (the default) everything is exactly as in sbndcode.  When it is
// given, the depo-to-signal transforms are DepoTransformYZ (WCT branch
// sbnd-yz-depo-scaling), which scale each plane's depo charge by that plane's
// map value at the depo (y, z).  The map keys are the anode type:names.
function(params, tools, yzmap=null) {
    local sim = sim_maker(params, tools),

    local nanodes = std.length(tools.anodes),

    // I rue the day that we must have an (anode) X (field) cross product!
    local ductors = sim.make_detector_ductors("nominal", tools.anodes, tools.pirs[0]),


    local zippers = [sim.make_depozipper("depozipper-"+tools.anodes[n].name, tools.anodes[n], tools.pirs[0])
                     for n in std.range(0, nanodes-1)],
    // YZ-KIT begin.  make_depotransform_yz is the toolkit branch's
    // pgrapher/common/sim/nodes.jsonnet function, copied here verbatim because
    // sbndcode ships its own pgrapher/common/sim/nodes.jsonnet, which shadows
    // the toolkit's and does not have it.
    local make_depotransform_yz = function(name, anode, pirs, yzmap, yzmap_key="") g.pnode({
        type:'DepoTransformYZ',
        name:name,
        data: {
            rng: wc.tn(tools.random),
            dft: wc.tn(tools.dft),
            anode: wc.tn(anode),
            pirs: std.map(function(pir) wc.tn(pir), pirs),
            fluctuate: params.sim.fluctuate,
            drift_speed: params.lar.drift_speed,
            first_frame_number: params.daq.first_frame_number,
            readout_time: params.sim.ductor.readout_time,
            start_time: params.sim.ductor.start_time,
            tick: params.daq.tick,
            nsigma: 3,
            yzmap: wc.tn(yzmap),
            yzmap_key: yzmap_key,
        },
    }, nin=1, nout=1, uses=[anode, tools.random, tools.dft, yzmap] + pirs),
    local transforms = [
        if yzmap == null
        then sim.make_depotransform("depotransform-"+tools.anodes[n].name, tools.anodes[n], tools.pirs[0])
        else make_depotransform_yz("depotransformyz-"+tools.anodes[n].name, tools.anodes[n], tools.pirs[0], yzmap)
        for n in std.range(0, nanodes-1)],
    // YZ-KIT end
    local depos2traces = transforms,
    //local depos2traces = zippers,

    local digitizers = [
        sim.digitizer(tools.anodes[n], name="digitizer-" + tools.anodes[n].name, tag="orig%d"%n)
        for n in std.range(0,nanodes-1)],

    local reframers = [
        g.pnode({
            type: 'Reframer',
            name: 'reframer-'+tools.anodes[n].name,
            data: {
                anode: wc.tn(tools.anodes[n]),
                tags: [],           // ?? what do?
                fill: 0.0,
                tbin: params.sim.reframer.tbin,
                toffset: 0,
                nticks: params.sim.reframer.nticks,
            },
        }, nin=1, nout=1) for n in std.range(0, nanodes-1)],


    // fixme: see https://github.com/WireCell/wire-cell-gen/issues/29
    local make_noise_model = function(anode, csdb=null) {
        type: "EmpiricalNoiseModel",
        name: "empericalnoise-" + anode.name,
        data: {
            anode: wc.tn(anode),
            dft: wc.tn(tools.dft),
            chanstat: if std.type(csdb) == "null" then "" else wc.tn(csdb),
            spectra_file: params.files.noise,
            nsamples: params.daq.nticks,
            period: params.daq.tick,
            wire_length_scale: 1.0*wc.cm, // optimization binning
        },
        uses: [anode, tools.dft] + if std.type(csdb) == "null" then [] else [csdb],
    },
    local noise_models = [make_noise_model(anode) for anode in tools.anodes],


    local add_noise = function(model) g.pnode({
        type: "AddNoise",
        name: "addnoise-" + model.name,
        data: {
            rng: wc.tn(tools.random),
            dft: wc.tn(tools.dft),
            model: wc.tn(model),
	    nsamples: params.daq.nticks,
            replacement_percentage: 0.02, // random optimization
        }}, nin=1, nout=1, uses=[tools.random, tools.dft, model]),

    local noises = [add_noise(model) for model in noise_models],
    
    local outtags = ["orig%d"%n for n in std.range(0, nanodes-1)],

    ret : {

        signal_pipelines: [g.pipeline([depos2traces[n], reframers[n],  digitizers[n]],
                                      name="simsigpipe-" + tools.anodes[n].name) for n in std.range(0, nanodes-1)],

        splusn_pipelines:  [g.pipeline([depos2traces[n], reframers[n], noises[n], digitizers[n]],
                                       name="simsignoipipe-" + tools.anodes[n].name) for n in std.range(0, nanodes-1)],
    
        signal: f.fanpipe('DepoSetFanout', self.signal_pipelines, 'FrameFanin', "simsignalgraph", outtags),
        splusn: f.fanpipe('DepoSetFanout', self.splusn_pipelines, 'FrameFanin', "simsplusngraph", outtags),

    } + sim,                    // tack on base for user sugar.
}.ret
