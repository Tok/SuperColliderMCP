// SynthDefs used by SuperColliderMCP.
//
// This file is the source of truth. The compiled *.scsyndef files next to it
// are what the MCP server sends to scsynth (via /d_recv) when it connects.
// After editing, rebuild them with:
//
//     python scripts/build_synthdefs.py
//
// Conventions:
//   - every synth writes stereo to `out` and frees itself when it is done,
//     so the Python side never has to free nodes by hand
//   - pitched sources share: freq, amp, pan, attack, sustain, release
//   - percussion shares: freq, amp, pan, decay
//   - only core UGens are used (no sc3-plugins required)
(
var outDir = thisProcess.argv[0];
var linen = { |attack, sustain, release|
    EnvGen.kr(Env.linen(attack, sustain, release, 1, \sin), doneAction: Done.freeSelf)
};
var defs;

if(outDir.isNil) {
    "usage: sclang synthdefs.scd <output-dir>".error;
    1.exit;
};

defs = [

    // ---- pitched sources -------------------------------------------------

    SynthDef(\mcp_sine, { |out = 0, freq = 440, amp = 0.2, pan = 0,
        attack = 0.01, sustain = 1, release = 0.3|
        var sig = SinOsc.ar(freq);
        Out.ar(out, Pan2.ar(sig * amp * linen.(attack, sustain, release), pan));
    }),

    SynthDef(\mcp_saw, { |out = 0, freq = 440, amp = 0.2, pan = 0,
        attack = 0.01, sustain = 1, release = 0.3, cutoff = 3000, rq = 0.5|
        var sig = RLPF.ar(Saw.ar(freq), cutoff.clip(30, 18000), rq.clip(0.05, 2));
        Out.ar(out, Pan2.ar(sig * amp * linen.(attack, sustain, release), pan));
    }),

    SynthDef(\mcp_square, { |out = 0, freq = 440, amp = 0.2, pan = 0,
        attack = 0.01, sustain = 1, release = 0.3, cutoff = 3000, rq = 0.5, width = 0.5|
        var sig = RLPF.ar(Pulse.ar(freq, width.clip(0.01, 0.99)), cutoff.clip(30, 18000), rq.clip(0.05, 2));
        Out.ar(out, Pan2.ar(sig * amp * linen.(attack, sustain, release), pan));
    }),

    // Band-passed noise; `freq` sets the band centre.
    SynthDef(\mcp_noise, { |out = 0, freq = 1000, amp = 0.2, pan = 0,
        attack = 0.01, sustain = 1, release = 0.3, rq = 0.3|
        var sig = BPF.ar(WhiteNoise.ar, freq.clip(30, 18000), rq.clip(0.01, 2)) * 6;
        Out.ar(out, Pan2.ar(sig * amp * linen.(attack, sustain, release), pan));
    }),

    // Two-operator phase modulation; the index decays for a bell/e-piano feel.
    SynthDef(\mcp_fm, { |out = 0, freq = 440, amp = 0.2, pan = 0,
        attack = 0.01, sustain = 1, release = 0.3, ratio = 2, index = 3|
        var idx = index * (0.3 + (0.7 * EnvGen.kr(Env.perc(0.01, sustain + release, 1, -4))));
        var sig = SinOsc.ar(freq, SinOsc.ar(freq * ratio) * idx);
        Out.ar(out, Pan2.ar(sig * amp * linen.(attack, sustain, release), pan));
    }),

    // Detuned saws, slowly moving low-pass, stereo spread.
    SynthDef(\mcp_pad, { |out = 0, freq = 440, amp = 0.2, pan = 0,
        attack = 0.8, sustain = 2, release = 2, cutoff = 2500, spread = 0.6|
        var sig = Saw.ar(freq * [0.996, 1, 1.004, 2.003]) * [1, 1, 1, 0.3];
        var lfo = SinOsc.kr(0.13, Rand(0, 2pi)).range(0.6, 1.2);
        sig = LPF.ar(sig, (cutoff * lfo).clip(40, 18000));
        sig = Splay.ar(sig, spread, 1, pan);
        Out.ar(out, sig * amp * linen.(attack, sustain, release));
    }),

    // Karplus-Strong string.
    SynthDef(\mcp_pluck, { |out = 0, freq = 440, amp = 0.3, pan = 0,
        attack = 0.001, sustain = 1, release = 0.3, decay = 2, cutoff = 6000|
        var sig = Pluck.ar(WhiteNoise.ar(0.8), Impulse.ar(0), 0.05,
            freq.clip(20, 10000).reciprocal, decay, 0.3);
        sig = LPF.ar(LeakDC.ar(sig), cutoff.clip(30, 18000)) * 2.5;
        Out.ar(out, Pan2.ar(sig * amp * linen.(attack, sustain, release), pan));
    }),

    // One grain for granular textures: a sine burst with a smooth window.
    SynthDef(\mcp_grain, { |out = 0, freq = 440, amp = 0.1, pan = 0, sustain = 0.1|
        var sig = SinOsc.ar(freq) * EnvGen.ar(Env.sine(sustain.max(0.002)), doneAction: Done.freeSelf);
        Out.ar(out, Pan2.ar(sig * amp, pan));
    }),

    // ---- percussion ------------------------------------------------------

    SynthDef(\mcp_kick, { |out = 0, freq = 50, amp = 0.5, pan = 0, decay = 0.45, punch = 4|
        var pitch = freq * EnvGen.kr(Env([punch.max(1), 1], [0.06], -6));
        var body = SinOsc.ar(pitch, 0.5pi) * EnvGen.kr(Env.perc(0.002, decay, 1, -4), doneAction: Done.freeSelf);
        var click = LPF.ar(WhiteNoise.ar, 3000) * EnvGen.kr(Env.perc(0.0005, 0.01));
        var sig = ((body + (click * 0.3)) * 1.5).tanh;
        Out.ar(out, Pan2.ar(sig * amp, pan));
    }),

    SynthDef(\mcp_snare, { |out = 0, freq = 180, amp = 0.4, pan = 0, decay = 0.18|
        var tone = SinOsc.ar(freq * [1, 1.6]).sum * 0.4 * EnvGen.kr(Env.perc(0.001, 0.07));
        var noise = BPF.ar(WhiteNoise.ar, 2500, 1.2) * EnvGen.kr(Env.perc(0.001, decay), doneAction: Done.freeSelf);
        var sig = (tone + (noise * 1.2)).tanh;
        Out.ar(out, Pan2.ar(sig * amp, pan));
    }),

    // Closed hat by default; a longer `decay` gives an open hat.
    SynthDef(\mcp_hat, { |out = 0, freq = 8000, amp = 0.25, pan = 0, decay = 0.06|
        var sig = HPF.ar(WhiteNoise.ar, freq.clip(1000, 16000));
        sig = sig * EnvGen.kr(Env.perc(0.001, decay, 1, -6), doneAction: Done.freeSelf);
        Out.ar(out, Pan2.ar(sig * amp, pan));
    }),

    // Short pitched click for accents and glitches.
    SynthDef(\mcp_blip, { |out = 0, freq = 1200, amp = 0.2, pan = 0, decay = 0.08|
        var sig = LPF.ar(Pulse.ar(freq, 0.3), (freq * 4).clip(100, 18000));
        sig = sig * EnvGen.kr(Env.perc(0.001, decay, 1, -8), doneAction: Done.freeSelf);
        Out.ar(out, Pan2.ar(sig * amp, pan));
    }),

    // ---- utilities -------------------------------------------------------

    // Effect chain for one tool call: reads a private stereo bus, applies
    // distortion -> low-pass -> delay -> reverb, writes to `out`.
    // Every amount is 0..1 and 0 means bypass. Lives for `sustain` seconds.
    SynthDef(\mcp_fx, { |in = 512, out = 0, sustain = 10,
        distortion = 0, cutoff = 20000, delay = 0, delaytime = 0.375, decaytime = 3,
        reverb = 0, room = 0.8|
        var sig = In.ar(in, 2);
        var env = EnvGen.kr(Env([1, 1, 0], [sustain, 0.05]), doneAction: Done.freeSelf);
        var driven = (sig * (1 + (distortion * 30))).tanh * (1 - (distortion * 0.4));
        sig = XFade2.ar(sig, driven, (distortion * 2 - 1).clip(-1, 1));
        sig = LPF.ar(sig, cutoff.clip(30, 20000));
        sig = sig + (CombL.ar(sig, 2, delaytime.clip(0.01, 2), decaytime) * delay);
        sig = FreeVerb2.ar(sig[0], sig[1], reverb.clip(0, 1), room.clip(0, 1), 0.5);
        Out.ar(out, sig * env);
    }),

    // Control-rate LFO written to a control bus that a synth control is mapped to.
    // shape: 0 sine, 1 triangle, 2 square, 3 sample & hold. curve: 0 linear, 1 exponential.
    SynthDef(\mcp_lfo, { |out = 0, rate = 1, lo = 0, hi = 1, shape = 0, curve = 0, sustain = 10|
        var lfo = Select.kr(shape.round.clip(0, 3), [
            SinOsc.kr(rate) * 0.5 + 0.5,
            LFTri.kr(rate) * 0.5 + 0.5,
            LFPulse.kr(rate),
            LFNoise0.kr(rate) * 0.5 + 0.5
        ]);
        var value = Select.kr(curve.round.clip(0, 1), [
            lfo.linlin(0, 1, lo, hi),
            lfo.linexp(0, 1, lo.max(0.0001), hi.max(0.0001))
        ]);
        Line.kr(0, 0, sustain, doneAction: Done.freeSelf);
        Out.kr(out, value);
    }),

    // Safety limiter at the end of the MCP group, so stacked voices never clip.
    SynthDef(\mcp_limiter, { |out = 0, level = 0.95|
        ReplaceOut.ar(out, Limiter.ar(In.ar(out, 2), level, 0.01));
    }),
];

defs.do { |def| def.writeDefFile(outDir) };
"wrote % SynthDefs to %".format(defs.size, outDir).postln;
0.exit;
)
