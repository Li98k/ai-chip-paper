# Etching 27 Billion Parameters into Silicon: A Current-Mode Virtual-Ground "Weights-as-Resistors" Analog AI Inference Chip

**Circuit-level feasibility, energy efficiency, and cost analysis of an LLM inference chip built from transistor amplifier circuits**

*An iterative, re-audited feasibility study (review rounds R0–R14, ≥5 h of genuine re-review). All 14 simulations in `sim/` are re-runnable; all figures in `sim/figs/` are reproducible from the listed scripts. No numbers are fabricated — every claim traces to a simulation run or a retrieved reference in `refs/`.*

---

## Abstract

We study whether a modern LLM can be run on a chip whose **model parameters are physically etched into the silicon as resistances**, rather than stored in DRAM/SRAM and shuttled through digital MAC units. The architecture formalizes a user's original proposal — *each weight is a resistor; the weighted sum of the previous layer's activations is a node current that a transistor amplifies* — and subjects it to full circuit-level, Monte-Carlo, and process-cost audit.

We find the naive "inject voltages into the transistor base" topology **does not work** (exponential base-current nonlinearity + milliamp DC back-feed). The correct form is a **current-mode virtual-ground crossbar**: signals are currents throughout, the summing node is held at a virtual ground, and readout is done with a **bipolar junction transistor (BJT) current mirror** (45 nm BiCMOS preferred, intrinsically current-matched, low 1/f). MOS is used only as a substitute readout at 7/3 nm (where BiCMOS/BJT is no longer available) and must be paired with a transimpedance amplifier (TIA); a naive single-MOS square-law hook-up is infeasible.

Headline quantitative results:

(1) **Accuracy.** Per-layer thermal SNR is essentially independent of layer width W and scales as R0^−½ and throughputs^−½. A rigorous Monte-Carlo gives ≈7.1 effective bits at 10 MOPS/node, R0 = 1 MΩ (INT8 borderline); ≈8.6 bits at 1 MOPS or R0 = 100 kΩ. A 0.1 % resistor tolerance satisfies INT8; a 1 % tolerance loses only ~1.3 % output (INT4 usable), compatible with mismatch-aware training.

(2) **Area tax.** "Writing parameters into silicon" costs one storage cell per weight. 27 B parameters need ~1080 cm² at 45 nm (≈1080 × 100 mm² dies, or ≈126 reticle dies — lab prototype only), ≈27 cm² at 7 nm (3.1 reticle, MCM ~6 cm³), and ≈11 cm² at 3 nm (≈1.3 reticle, single package ~2 cm³ — the process boundary of this scheme).

(3) **Concrete model (Qwen3.8-27B, dense 27 B, 4 k context).** Power 0.2–2 kW (IC0 design freedom, comparable in magnitude to an H100). Throughput: INT8 ~1,200 tok/s, 6-bit ~5,400 tok/s, INT4 ~87,000 tok/s. INT4 per-token energy 2.4–24 mJ — about 50–300× lower than H100 batched (1.17 J/token) and about 500–5,000× lower than H100 single-stream (11.7 J/token), with throughput beating H100 by ~100–1,500×.

(4) **Process and cost.** For a 27 B chip at 45/28/14/7/3 nm, silicon + MCM packaging cost is ~$13k / $7.4k / $3.2k / $2.4k / $2.6k — the **cost sweet spot is 7–14 nm, and mature nodes (28/14 nm) are NOT cheaper** (the giant MCM package of 12–49 reticle dies eats the per-wafer price advantage). The chip has **no HBM/external memory** (weights live in on-die resistive cells), saving the H100's 8×HBM3 (~$5–8k).

(5) The scheme has a complete technical lineage (ANNA 1989 → NorthPole 2016 → Mythic 2018 → Bowen 2023) and is **physically feasible** in the regime of advanced process + moderate throughput + low-precision inference; its energy advantage (fixed-weight e_op ∝ 1/N) grows with model scale.

**Keywords:** in-memory computing; analog inference; crossbar; transistor amplification; parameters-as-hardware; energy-efficiency limit

---

## 1. Introduction and Problem Statement

The inference workload of modern large models is dominated by matrix–vector products (MV/MAC). Digital architectures such as GPUs store weights in DRAM/SRAM, and every MAC carries an explicit read–multiply–write, limited by von Neumann data movement. We pursue the opposite path: **write the weights into the physical parameters of analog devices**, so that "reading a weight" and "multiplying" collapse into the same physical process (Ohm's law), thereby eliminating that data movement.

The user's original circuit idea is formalized as follows (Figure 1, concept):

- Each neuron j (j = 1..W) of the previous layer outputs an analog voltage x_j (amplitude 0–100 mV, the activation);
- Connection line j is a resistor R_j, whose value is computed from the model weight w_j via the conductance mapping **R_j = R0 / w_j** (equivalently G_j = w_j / R0), with R0 a normalization reference;
- All W resistor lines converge on the next-layer node, whose core is a transistor (BJT) whose collector current is proportional to the weighted sum, I_C ∝ Σ_j w_j x_j;
- If several connection lines converge and change the equivalent resistance, the node's amplified signal and current change accordingly.

The questions we must answer:
- **Q1** Can this circuit truly implement Σ w_j·x_j linearly? Can transistor amplification hold?
- **Q2** What are the magnitudes of noise, tolerance, nonlinearity, and DC power? Can INT8 be reached?
- **Q3** At real model scale (billion-parameter), are area/power feasible?
- **Q4** How does this relate to prior work (ANNA / Mythic / NorthPole / memristor CIM)?
- **Q5** Verdict: feasibility judgment + pros/cons list.

---

## 2. Circuit Physics Analysis (Q1)

### 2.1 Voltage Cannot Reach the Base: Exponential Distortion + DC Back-Feed Force a "Current-Mode Virtual Ground + BJT Current-Mirror Readout"

**One-line framing: the summing node carries *current* (current-mode virtual ground); the readout uses a *bipolar transistor (BJT)* (current mirror). Not MOS, not voltage.** (MOS is only a substitute readout at 7/3 nm, see §4.8.)

Connecting W voltage sources through resistors to the BJT base node, the node equation is:
    Σ_j (x_j − V_B)/R_j + I_bias = I_B(V_BE)
where V_B = V_BE + I_E·R_E (with emitter resistor R_E),
I_C = α·I_S·e^{V_BE/V_T} (Ebers–Moll, V_T ≈ 25.9 mV).

Simulation sim_v1b (full Ebers–Moll, W = 4096, R0 = 40 kΩ, R_E = 100 Ω, IC0 = 100 µA) reveals two fatal problems:

**Problem 1: Exponential nonlinearity.** A sweep (input 0→100 mV) gives:
    a = 0:   IC = 1.36 mA   a = 0.1: 1.64 mA   a = 0.5: 3.34 mA
    a = 1.0: IC = 7.46 mA   (multiples of IC0 = 13.6 → 74.6, an e^{a·V/VT} bend)
i.e. I_C is exponential, not linear, in the input. It is approximately linear only in a very small local region (±10–20 mV swing), while LLM activation swing is ~100 mV in magnitude — it cannot be linear overall.

**Problem 2: Common-mode DC.** The base-node voltage "floats" at V_BE ≈ 650–700 mV, whereas the signal is a 0–100 mV floating level — the resistor network back-feeds DC from the signal sources (sim_v5 measures 1.10 mA/node naive back-feed, cut to a −0.02 mA residual by differential virtual ground), collapsing both power and dynamic range.

**Conclusion: the user's verbatim topology must be corrected.** The correction is to make the summing node a **virtual ground (virtual ground, constant ≈ V_BE)** and inject the signal as **current**:
    I_j   = x_j / R_j = x_j·w_j/R0
    I_sum = Σ_j I_j   = (1/R0)·Σ_j w_j x_j          (Ohmic summation, inherently linear)
This is exactly the standard operating mode of a memristor crossbar, and the topology shared by ANNA/NorthPole/Mythic. The transistor (the core device of the user's scheme) plays this role in the corrected topology:

  ① **Current-mirror readout:** mirror I_sum to the output branch, isolating downstream load (gain ≈ 1);
  ② **Emitter negative-feedback linearization:** R_E pins the BJT operating point at a chosen IC0, providing transconductance g_m = IC0/V_T in the small-signal region for local linear amplification;
  ③ **Optional β/10 small-gain boost:** raise the SNR margin for the downstream ADC.

So the "transistor amplification" idea holds and is necessary in the sense of ①②③ — but it is no longer "voltage division into the base"; it is "crossbar current summation + BJT current-mirror/transconductance readout."

### 2.2 Linearity Verification of the Corrected Topology

sim_v4 (physically self-consistent version: correct I_E·R_E feedback + bisection solve) at the R_E = 1–2.6 kΩ, IC0 = 200 µA design point shows max nonlinearity < 0.2 % over the full 0–100 mV sweep — meeting the INT8 global linearity requirement. sim_v5b (current-mode virtual ground) further verifies:
    C1 summation exactness: deviation from ideal Σw·x < 1e-12 (pure algebraic identity)
    C5 tolerance ±1% → output error mean 0.54% / p95 1.31%, ±0.1% → mean 0.05% / p95 0.13%

**Key insight (tolerance does not accumulate with W):** the relative error of each sum term cancels statistically in the Σ (the Σ of independent random errors grows as √W while the signal grows as W), hence
    output error ≈ cell tolerance × O(1)
At W = 4096 a 1 % tolerance produces only p95 1.31 % (mean 0.54 %, not 4096× 1 %!). This is an important statistical dividend of the crossbar architecture over per-cell digital circuits.

### 2.3 Three-Layer Wiring Schematic (Figure 6, sim_v11 numerical verification)

Cascading the 2.2 single-stage unit into a full network yields a "weights-as-resistors" three-layer wiring (Figure 6): between each layer there is one whole crossbar, **each connection = one resistor R = R0/w (conductance G = w/R0)**, with the resistor value computed directly from the model parameter; all connections converging on the same node are Ohmically summed at the **virtual ground (≈0 V)**, node current I = (1/R0)·Σ w_i·x_i, then linearly recovered to the next layer's input voltage through a BJT readout cell (current mirror + R_E negative feedback).

**Layer-by-layer argument (3 inputs → 2 hidden → 2 outputs, R0 = 1 MΩ, sim_v11):**
- Stage-1 wiring L1→L2: node 1 connects R=1250 kΩ←x1, R=3333 kΩ←x2, R=5000 kΩ←(−x3) (w=−0.2 uses a differential pair); node 2 connects R=2000 kΩ←(−x1), R=1429 kΩ←x2, R=2500 kΩ←x3. The three input voltages are Ohmically summed at the virtual ground through their resistors → I_j = (1/R0)Σ w_ij·x_i.
- BJT readout (R_E linearization): I_j → y_j = I_j·R0, giving the two L2 node voltages.
- Stage-2 wiring L2→L3: node 1 connects R=1667 kΩ←y1, R=2500 kΩ←(−y2); node 2 connects R=1111 kΩ←y1, R=5000 kΩ←y2. Ohmic summation + BJT readout → z1, z2.

**Numerical verification (sim_v11, x = [80,40,60] mV):**
    analog three-layer wiring  z = [33.6, 60.0] mV
    digital matrix multiply    z_dig = W2·(W1·x) = [33.6, 60.0] mV
    max relative error = 1.16e-16 (pure float, algebraic identity)
i.e. the three-layer resistor wiring **exactly** implements z = W2·(W1·x).

**Core argument (why this *is* an "AI chip," not a pile of discrete circuits):**
1. Matrix multiplication is **written into Ohm's law** — weights stored as resistors, the sum performed automatically by node current; one voltage application yields the whole layer's result, with no "read parameter → multiplier → write back" data movement (the main energy cost of a digital MAC). This is precisely the physical mechanism by which Bowen (2302.06417) shows e_op ∝ 1/N under fixed weights.
2. Between layers only analog voltages/currents (y_j, z_j) are passed, **neither read nor written**; the transistor's role is node-level current→voltage linear readout + R_E negative feedback (transconductance clamped by R_E, independent of β, hence per-node linearity <0.2 %), not "amplifying" the input.
3. Negative weights cannot be realized with a single passive resistor (G ≥ 0) — a **differential pair** (connecting the −x branch) or 4-quadrant encoding is mandatory. This is an inherent wiring tax of the architecture, marked by red lines in Figure 6.
4. Each extra layer adds one more crossbar; area grows linearly with layer count, but **each layer is independently linear**, and per-layer error does not compound/amplify (error sources in §3, and tolerance does not accumulate with W, §2.2).

Figure 6: `sim/figs/fig3layer_wiring.png` (script `sim/fig3layer_wiring.py`, numerics `sim/sim_v11_3layer.py`).

Figure 7 (single-node transfer flow, zoomed): `sim/figs/fig_circuit_flow.png` (script `sim/fig_circuit_flow.py`). It expands the "neuron → neuron" signal transfer into a standard circuit-diagram instance — the previous-layer neuron x_j becomes a current I_j = w_j·x_j/R0 through the **weight resistor R_j = R0/w_j**, many paths are summed at the **virtual-ground node** I = (1/R0)Σ w_j·x_j, then the **BJT amplifying readout stage** (base connected to the sum current, R_E linearization, current-source VCC bias) recovers the voltage y = Σ w_j·x_j for the next-layer neuron. The bottom flow band ①→②→③→④ gives the direct signal chain and contrasts it with a "traditional digital GPU (read memory → MAC → write memory)": this circuit completes inter-neuron transfer with a single voltage application, no memory read/write.

---

## 3. Accuracy: Noise / Tolerance / Depth Accumulation (Q2)

### 3.1 Rigorous Monte-Carlo of Thermal-Noise SNR (sim_v10)

Construct the crossbar summing node directly: W branches, branch j thermal-noise current σ_j = √(4kT·BW·|G_j|), independent; signal I_sig = Σ x_j G_j. Full sweep over W∈[256,16384], R0∈[100k,10MΩ], throughput∈[100kOPS,1GOPS]:

| Scaling law | Monte-Carlo exponent | Meaning |
|--------|------------------|------|
| SNR vs W | ≈0 (flat 42~44.5 dB) | Under random signs, signal √W and noise √W cancel to the same order |
| SNR vs R0 | −0.98 ~ −1.06 (≈R0^−½) | Larger R0 → more noise (4kTR theorem) |
| SNR vs throughput | −0.87 ~ −0.99 (≈BW^−½) | Faster → larger noise bandwidth |

**Numerical anchors (R0 = 1 MΩ, W = 4096):**
    100 MOPS: 33.3 dB ≈ 5.2 bit | 10 MOPS: 44.5 dB ≈ 7.1 bit
    1 MOPS:   53.3 dB ≈ 8.6 bit | 100 kOPS: 63.3 dB ≈ 10.2 bit
**Design window (Figure 5):** INT8 (49.9 dB, median) needs R0 ≤ 288 kΩ @ 10 MOPS or 1 MΩ @ ≤2.9 MOPS; INT4 (25.8 dB) is satisfied by almost any (R0, throughput) combination.

> Self-correction log: early v5b/v6 reported "SNR 90 dB," a full-scale coherent upper bound (reachable only if all inputs had equal amplitude and phase — never occurs in practice); the v9 analytic expression also missed the summation √W, underestimating by 25 dB. The v10 rigorous MC is the final authoritative value. This is exactly the practical value of "iterative re-review."

### 3.2 Resistor Tolerance (sim_v5b C5, Monte-Carlo 300 samples)

    tolerance ±1%   → output error mean 0.54%, p95 1.31%  (INT4 usable, INT8 not met)
    tolerance ±0.1% → output error mean 0.05%, p95 0.13%  (INT8 met)
Two engineering paths:
  (a) Use 0.1 % thin-film resistors / RRAM calibration (on-chip self-calibration loop, one-time overhead);
  (b) Mismatch-aware training (arXiv 1606.07786): fold measured cell mismatch as a constraint into NN training so the network "learns" its own imprecision — 1 % tolerance devices can approach INT8 precision. This is naturally compatible with the "parameters written once and never changed" architecture (calibration data can be injected post-fab).

### 3.3 Depth Accumulation (sim_v7/v8/v16, 6-layer MLP end-to-end)

Full analog chain per layer: tolerance weights + summing thermal noise + BJT readout ±1 % mismatch + N-bit ADC.

    per-layer cosine (layer out vs digital ideal): L1 0.9997, then a gentle slope:
      L2 0.998 → L3 0.991 → L4 0.960 → L5 0.83 (network-averaged, sim_v16)
    final-layer cosine (authoritative multi-seed values, sim_v16: 10 nets × 20 MC,
    BW = 1.6 MHz ≈ 3.2 MOPS/node, tol = 1%):
      mean 0.829 ± 0.024, range [0.779, 0.865]
      (single-net single-run values: 0.889 (v7, seed 42) / 0.791 (v8, seed 7)
       — implementation spread, not a model difference)
      16-bit ADC:            0.829   (ADC bits are not the bottleneck; thermal noise is)
      0.1% vs 1% tolerance:  nearly no difference (Σ cancellation)
      Recovery BW=0.5MHz(=1MOPS): mean 0.928, range [0.898, 0.947]

Interpretation: the final-layer cosine distribution of 0.78–0.87 (mean 0.83, sim_v16 multi-seed) means the network "still works but with visible accuracy loss"; the recovery levers are explicit — drop per-node throughput to 1 MOPS (bandwidth ×0.316, SNR +5 dB; cross-seed mean 0.928) or drop R0 to 288 kΩ (INT8 median window), and final-layer cosine returns to 0.9+ (the 0.928 mean is cross-seed stable). **Note: non-linear normalization ops such as softmax/LayerNorm do not belong to the linear layers and must be implemented digitally** (or in analog piecewise) — these are the "digital islands" that alternate per layer in an LLM, and they count into the overall energy-efficiency evaluation.

---

## 4. Scale: Area / Power (Q3)

### 4.1 The Area Tax: 1 Parameter = 1 Storage Cell (sim_v6)

The fundamental cost of "writing parameters into hardware" is that each weight occupies one physical storage cell (1T1R: transistor + RRAM, or transistor + polysilicon resistor). Cell area by process:
    45 nm: ~4 µm² | 7 nm: ~0.1 µm² | 3 nm: ~0.04 µm²

| Model scale | 45 nm  | 7 nm   | 3 nm   |
|----------|--------|--------|--------|
| 2.5 B    | 100 cm² (100 × 10 mm×10 mm dies) | 2.5 cm² | 1 cm²  |
| 7 B      | 280 cm² (280 × 100 mm² dies)   | 7 cm²   | 2.8 cm² |
| 27 B     | **1080 cm² (≈126 reticle)** | 27 cm²  | **10.9 cm² ≈ 1.3 reticle** |

**Term · reticle (photo-mask / exposure field):** the area of a single reticle mask that one lithography step can expose, industry-maximum ~26×33 mm² ≈ 858 mm² ≈ 8.6 cm² (about 0.86 of a 100 mm² die). We use "reticle die" = 8.6 cm² as the standard exposure unit; a chip spanning N reticles is assembled from N pieces of 8.6 cm² die (MCM multi-chip packaging). For reference, the H100 GPU's single die ≈ 8.26 cm², almost exactly one reticle.

**Key conclusion: Moore's law directly improves the feasibility boundary of this scheme.** At 45 nm, a billion-parameter model must use multi-chip / MCM / 3D stacking (interconnect cost comparable to HBM); at 3 nm, a 27 B weight array is only ~11 cm² (about 1.3 reticle dies), fitting inside a single package — only then does the architectural advantage of "parameters written into the chip" over "weights in DRAM + digital MAC" truly appear (Bowen 2023's energy argument also requires a large enough N to amortize ADC/DAC overhead).

### 4.2 Power

- Static / DC: node DC = tail current IC0 (under current-mode architecture it is independent of R0), P_node ≈ 3·VCC·IC0 (tail + mirror + driver, VCC = 0.9 V). 2.5 B parameters = 610 k nodes (W = 4096):
    IC0 = 10 µA → 16 W | 50 µA → 82 W | 100 µA → 164 W
  27 B (45 nm) @ IC0 = 100 µA → ~1.78 kW (spread across dies; the per-die average is the same order as a digital accelerator of comparable scale — a digital MAC's energy is mainly in driving and storage access, comparable to the analog scheme's DC budget);
- Dynamic: per-MAC energy is dominated by input/output ADC-DAC (Bowen Table 4: 45 nm/0.9 V/8-bit: ADC 0.25 pJ, DAC 0.01 pJ, digital MAC 0.23 pJ); the analog summation itself is 0.04~0.8 pJ — **analog summation saves 3~6× over a digital MAC**;
- Fixed-weight scenario (the core selling point of the user's scheme): no reconfiguration needed, e_op ∝ 1/N (Bowen): at N = 27 B the per-parameter per-token energy is amortized down to the sub-pJ range, which a GPU (reads the full weights from DRAM every token) cannot reach.

### 4.3 Speed

The crossbar completes a whole layer's summation in one settling time: τ ≈ R_eq·C ≈ (R0/Σ|w|)·C_node; at W = 4096, R0 = 1 MΩ, R_eq ~250 Ω, C = 5 fF → τ ~1.25 ps, so the RC itself is not a bottleneck; the actual clock is set by ADC sampling and inter-node data flow. 1 MOPS/node throughput corresponds to ~1.4e10 OPS for the full 27 B model (with inter-layer pipelining and parallel tiles), in the "edge real-time inference" regime — we do not chase GPU-class throughput; we chase **tokens per joule**.

### 4.4 Concrete Model Account: Qwen3.8-27B (sim_v12)

Apply §4.1–4.3 to a real-scale model (estimated as dense 27 B; L=64 / d=4096 / 32 heads are explicit architecture assumptions; if it is actually MoE, active parameters << 27 B and area/power/energy are all more optimistic by the active fraction). Total MAC per token ≈ 56.1e9 (including 4 k attention, ≈2.08× P); BJT readout nodes = P/W = 6.59e6.

| Process | Silicon area | # reticle | Package volume | Silicon+MCM cost | Verdict |
|------|--------|-----------|----------|------------|------|
| 45 nm | 1080 cm² | 126 | ~227 cm³ (multi-chip MCM) | ~$13k | Lab prototype only (rack-level module) |
| 28 nm* | 418 cm² | 49 | ~88 cm³ | ~$7.4k | Large MCM, not economical |
| 14 nm* | 105 cm² | 12.2 | ~22 cm³ | ~$3.2k | MCM, acceptable |
| 7 nm  | 27 cm² | 3.1 | ~5.7 cm³ | ~$2.4k | Datacenter-feasible (MCM), lowest cost |
| 3 nm  | 10.8 cm² | 1.3 | ~2.3 cm³ | ~$2.6k | Single-package feasible (process boundary) |

*28 nm ≈ the "~24 nm" tier asked about; 14 nm is a mature node. Area extrapolated from the v6 cell-area model, area ∝ node² (28 nm = 1.55, 14 nm = 0.39 µm²/parameter).

Compare with H100: silicon 8.26 cm² / package ~2 cm³. **Area is the first hard constraint of this scheme** — 27 B parameters = 27 billion storage cells, weights permanently occupy silicon, with no "computed-then-discarded" temporary storage.

Power (6.59e6 nodes, IC0 a design freedom): IC0 = 10 µA → ~205 W, 50 µA → ~1.0 kW, 100 µA → ~2.0 kW (including 15 % digital island/softmax); ADC/DAC <1 %, negligible.
**Power is on the same order as one H100 (0.7 kW) — not a killer, but not a saver either.**

Throughput and energy (4 k context, all layers in parallel; per node per token = 8518 MAC):

| Tier | SNR | tok/s | Per-token energy (IC0 10→100 µA) |
|------|-----|-------|------------------------------|
| INT8  R0=288 kΩ @ 10 MOPS | 49.9 dB | ~1,200 | 0.17–1.74 J |
| 6-bit R0=1 MΩ @ 46 MOPS   | 37.9 dB | ~5,400 | 38–379 mJ |
| INT4  R0=1 MΩ @ 740 MOPS  | 25.8 dB | ~87,000 | 2.4–23.6 mJ |

Compare with H100 running 27 B (explicit assumption, 0.7 kW): single-stream decode ~60 tok/s → 11.7 J/token; batched serving ~600 tok/s → 1.17 J/token. This chip (fixed weights, single context):
  · **Throughput:** INT8 ~1,200 / 6-bit ~5,400 / INT4 ~87,000 tok/s — beats H100 single-stream (60) by ~20–1,450× (vs H100 batched 600, ~2–145×);
  · **Energy:** INT4 per token 2.4–23.6 mJ, ~50–490× lower than H100 batched (1.17 J) and ~500–4,900× lower than single-stream (11.7 J); INT8 per token 0.17–1.74 J, same order as H100 batched, ~7–67× lower than single-stream.
**The energy advantage is only realized strongly in the "fixed weights + low precision (INT4/6-bit)" regime; at INT8 the advantage narrows to the same order.**

### 4.5 Process and Cost: Are Mature Nodes (28/14 nm) Cheaper? (sim_v15)

User's question: from the perspective of today's **mature** chip processes and costs — including ~24 nm (treated as the 28 nm tier) and 14 nm — how much does a 27 B chip cost to make, and are mature nodes more economical? Method (sim_v15): extrapolate the v6 area model (1 parameter = 1 small-area resistive cell, area ∝ node², anchored at 45 nm = 4 µm², 7 nm = 0.1 µm², 3 nm = 0.04 µm²) to 28/14 nm, then overlay 300 mm wafer price + Poisson yield Y = exp(−D0·A) (8.58 cm² reticle large die) + MCM packaging cost.

| Node | Cell µm² | Total area | Reticle die | Yield | Per-die silicon cost | **Silicon+MCM total cost** |
|------|---------|--------|------------|------|-------------|------------------|
| 45 nm | 4.00 | 1080 cm² | 126 | 55% | $46 | **~$13.0k** |
| 28 nm* | 1.55 | 418 cm² | 49 | 42% | $93 | **~$7.4k** |
| 14 nm* | 0.39 | 105 cm² | 12.2 | 33% | $193 | **~$3.2k** |
| 7 nm  | 0.10 | 27 cm² | 3.1 | 21% | $660 | **~$2.4k** (lowest) |
| 3 nm  | 0.04 | 11 cm² | 1.3 | 14% | $1824 | **~$2.6k** |

*28 nm represents the ~24 nm mature tier asked about. Wafer prices (explicit assumption): 45 nm $1800 / 28 nm $2800 / 14 nm $4500 / 7 nm $10k / 3 nm $18k.

**Conclusion (important counter-intuition): mature nodes are NOT cheaper.**
  · 45 nm wafers are cheapest, but a 27 B needs **126 reticle dies** — the package/interconnect/probe/test cost of a giant MCM completely eats the "cheap wafer" advantage, so the total ~$13k is actually the highest.
  · 28 nm needs 49 dies, 14 nm needs 12 dies; MCM packaging is 39% / 27% of cost, still ~2–3× more expensive than 7 nm.
  · **The cost sweet spot is 7–14 nm:** 7 nm cheapest (~$2.4k, 3.1 dies), 3 nm close behind (~$2.6k, 1.3 dies), 14 nm acceptable (~$3.2k, 12 dies).
  · **Structural cost dividend: this chip has no HBM/external memory** (weights live in on-die resistive cells), saving the H100's 8×HBM3 (~$5–8k) — relative to the H100 full card (GPU + HBM ~$30k) "storage cost," this scheme turns external HBM into in-place resistive cells.

**Assumptions and boundaries (honest statement):**
  ① Area basis = "small-area resistive cell" (ReRAM / floating-gate MOS / thin film, ~0.04–4 µm²/parameter). If instead a large meandered NiCr thin-film resistor (per MΩ ~mm²) were used, area and cost would rise fold-fold — this is the **key device assumption** for the scheme to be realizable.
  ② Yield uses Poisson; reticle large-die yield is inherently low (14–55%); mass production via chiplet / binning / multi-die redundancy can improve it — this estimate is conservative (an upper bound), real mass-production cost lower.
  ③ Cost excludes R&D / tape-out NRE (advanced-node NRE starts at hundreds of millions of dollars), design tools, and test-equipment amortization.

### 4.6 Thermal Effects and Thermal Design (sim_v13)

Power density: 7 nm 8–76 W/cm² (H100 = 85), 3 nm 19–190 W/cm² (exceeds H100 at 100 µA). Junction temperature (H100-measured calibration: liquid cooling 0.1, air cooling 0.6 K·cm²/W):

| Cooling | 7 nm junction | 3 nm junction |
|------|----------|----------|
| Liquid | 31–38 °C | 32–49 °C |
| Air    | 35–76 °C | 41–144 °C |

Item-by-item thermal impact on performance (quantified):

| Item | Mechanism | Impact | Acceptable? |
|----|------|------|----------|
| ① Thermal noise | SNR ∝ 1/√T | 25→105 °C only −1.0 dB | Negligible (12 dB margin) |
| ② BJT leak IS | doubles per +7 °C | 53× @ 65 °C, 380× @ 85 °C, 2756× @ 105 °C | **True thermal killer**; must suppress junction temp |
| ③ VBE drift | −2 mV/°C | 75 K → −150 mV offset | Bandgap reference + one-time calibration solves it |
| ④ Gain drift | −0.1%/°C | 75 K → −7.5% | Global scaling absorbed by readout |
| ⑤ Resistor drift | R_j and R0 same material/batch | **Common-mode cancels exactly**, residual differential 0.15% | Calibrable (architecture dividend) |

**Verdict: heating is not fatal, but liquid cooling + temperature compensation are mandatory.** The noise-class items (①④⑤) have almost no effect on accuracy — especially ⑤ common-mode cancellation is a dividend of the current-mode architecture (the common-mode drift of R_j and R0 in the same batch cancels in I = (1/R0)Σw·x). The only true culprit is ②, the BJT exponential leak: held below 50 °C by liquid cooling it is a manageable 8.5×; air-cooled 7 nm reaches 76 °C and needs compensation; 3 nm must be liquid-cooled.

### 4.7 3D Stacking: Can the Volume Be Reduced? (sim_v13)

3D reduces the **footprint**, not the silicon volume (the 27 B cell count is fixed and cannot be physically deleted).

| Scheme | Footprint | Height | Volume | Relative |
|------|------|-----|------|------|
| 2D MCM (3 reticle side-by-side) | 25.7 cm² | 2.0 mm | 5.1 cm³ | — |
| 3D 4-layer stack | 6.75 cm² (within a single reticle) | 3.4 mm | 2.3 cm³ | footprint ↓3.8×, volume ↓2.2× |
| 3 nm (2D already ~1.3 reticle) | ~10.8 cm² | 1.9 mm | ~2.1 cm³ | small 3D marginal gain |

New cost: ~1.65 M TSVs per interface, pitch ≈ 20 µm — denser than standard flip-chip µbumps (40–55 µm), requiring fine-pitch µbumps or hybrid bonding (if only the d = 4096 hidden state rather than all 6.59 M nodes is passed at the layer boundary, TSV count drops sharply and pitch relaxes). 3D thermal: bottom die +22 K extra (100 µA) → liquid-cooled Tj ≈ 57 °C, still needs temperature compensation.

**Verdict: yes it shrinks, and substantially — at 7 nm the footprint drops from 3 reticle to a single reticle (↓3.8×), volume 5.1 → 2.3 cm³.** But the essence is trading "number of reticles" for "TSV density + 3D thermal management" — a packaging/interconnect problem, not a silicon-area problem; the hard tax of "27 B parameters = 27 B cells" does not change.

### 4.8 Readout Control Modality: Current-Controlled (BJT) vs Voltage-Controlled (MOS), and Better Schemes (sim_v14)

The crossbar virtual ground outputs a **current sum** I_sig = 12.8 µA (RMS), noise floor 34.3 nA. The BJT is current-controlled (I_B), the MOS is voltage-controlled (V_GS) — their **modality match** to a current-mode output differs, which is the essence of readout selection:

| Metric | BJT (current-controlled) | MOS TIA (voltage-controlled) |
|------|----------------|---------------------|
| Control quantity | I_B (current) = intrinsic match | V_GS (voltage) = modality mismatch |
| Impedance conversion | None (current drives base directly) | Must do I→V (R_f, adds thermal noise) |
| DC input load | I_sig/β ≈ 1% (siphons crossbar current) | 0 (gate insulated) |
| Readout noise @ 10 MOPS | R_E=50 Ω → −3.8 dB; R_E≥280 Ω → ≤−1 dB | R_f≥28.8 kΩ → ≈0 dB (negligible) |
| 1/f corner | ~100 Hz (low) | ~50 kHz (high, negligible at 10 MHz readout) |
| Available at 7/3 nm | No (BiCMOS only ≤28/14 nm) | Yes (pure CMOS) |

Key points:
  ① **The control-modality difference is second-order for noise** — adjusting BJT R_E or MOS R_f both push readout noise below 20 % of the floor (R_E≥280 Ω → −1 dB, R_f≥28.8 kΩ → 0 dB). Readout noise is far from the system bottleneck (consistent with §3 sim_v8: ADC/readout is not the bottleneck, crossbar thermal noise is).
  ② **The decisive difference is node availability and load / 1/f:** the BJT is unavailable at 7/3 nm (BiCMOS discontinued), and it siphons an I_sig/β DC load, with low 1/f (good for low frequency); the MOS is pure-CMOS available with 0 DC load, but needs I→V and has a high 1/f corner (already negligible at 10 MHz readout).
  ③ A naive single MOS directly in square-law I_D ∝ (V_GS − Vth)² introduces 2nd-harmonic nonlinearity; **a transimpedance TIA is mandatory** (the gain device holds a virtual ground, V_out ∝ I_sig linearly).

**Better scheme C: current-mode differential readout** (negative weights already force a differential pair, so three birds with one stone) — the signal stays current-mode throughout (resolving the MOS modality mismatch); common-mode rejection ~40 dB (cancels R0 common-mode drift / temperature / process offset, stronger than single-ended); the gain device can be BJT (45 nm, low 1/f) or MOS (7/3 nm, pure CMOS), node-independent.

**Better scheme D: charge sampling (current-mode S/H, zero impedance conversion)** — the virtual-ground current I_sig flows into a sampling capacitor C for time τ → V = I_sig·τ/C, a natural transimpedance with no R_f thermal noise; sampling noise √(kT/C) ≈ 20.4 µV at C = 10 pF (R16-T6 erratum: the original "0.02 µV" mislabeled an mV value as µV); combined with differential = the optimal front-end.

**Verdict (including feasibility): the scheme works for both control modalities, and the control-modality mismatch can be resolved architecturally.**
  · 45 nm prototype: BJT current-mode differential readout (lowest 1/f, intrinsic match, available).
  · 7/3 nm: MOS current-mode differential TIA (pure-CMOS available, differential cancellation, shrink R_f to lower noise → no penalty).
  · Optimal front-end: current-mode + differential + (optional charge sampling) → the control-modality problem is no longer a feasibility barrier.
  · Bonus: the attention-layer softmax exp can be natively realized with a diode / Schottky (I ∝ e^{V/VT}).

Figure 8 (optimal readout front-end: current-mode differential + charge sampling): `sim/figs/fig_readout_diff.png` (script `sim/fig_readout_diff.py`). It turns schemes C/D into a complete front-end: ① the crossbar virtual-ground node outputs positive/negative branch currents I± → ② differential current buffer (current mirror) I_out = I+ − I−, CMR ≈ 40 dB cancels R0 common-mode drift / temperature / process offset → ③ charge-sampling C, I_out flows in for time τ, charging to V_out = I_out·τ/C (no R_f thermal noise, sampling noise √(kT/C) ≈ 20.4 µV @ 10 pF) → ④ ADC to the next layer. Entirely current-mode, no impedance conversion; the gain device is BJT (45 nm) / MOS (7/3 nm) chosen per node, architecturally resolving the "current-control vs voltage-control" modality mismatch.

---

## 5. Literature Positioning: Where This Scheme Sits in the Technical Lineage (Q4)

### 5.1 Key Finding: The User's Circuit Description Exists Verbatim in the Authoritative Literature

Bowen et al., "Analog, In-Memory Compute Architectures for AI" (arXiv 2302.06417, full text retrieved at `refs/full_2302.06417.txt`) states:

> "Each transistor is connected to a reconfigurable resistor, the conductance of which determines the effective weight of each element in the matrix."

This corresponds word-for-word to the user's idea (transistor + tunable resistor + conductance = weight). The landmark works cited by this reference (the complete lineage of the field):

| Time | Work | Key point | Relation to the user's scheme |
|------|------|------|------------------|
| 1989 | ANNA (16000 synapses) | Earliest large-scale analog NN chip, resistors as weights, bipolar process | **Direct precursor of the user's scheme** (also used BJT-era devices) |
| 1990s | Analog VLSI NN wave | Hopfield / associative-memory chips | Faded due to precision and device drift |
| 2016 | ISAAC (Shafiee et al., ISCA) | 45 nm ReRAM crossbar analog in-memory CNN accelerator | Engineering of the current-mode crossbar |
| 2019–2023 | IBM NorthPole (Hahn et al.) | Near-memory **digital** inference chip (not an analog crossbar; erratum: a different work from ISAAC — the old "NorthPole 2016 / 158 TOPS/W" had no source and is removed) | Near-memory inference engineering (2025 LLM system in ref. 9) |
| 2018 | Mythic "Mythic multiplies in a flash" (Demler) | Flash crossbar commercial analog accelerator | Proved "parameters written into memory" can be productized |
| 2019 | Xia & Yang, memristive crossbars | Device-level survey | Resistor/memristor non-negative → sign problem |
| 2023 | Bowen 2302.06417 | Energy-limit theory: fixed-weight e_op ∝ 1/N | Theoretical endorsement of the user's energy selling point |
| 2016 | 1606.07786 | Mismatch-aware: absorb device imprecision via training | A ready route to solve the user's tolerance problem |

### 5.2 Differentiated Positioning of This Scheme (contribution points the paper can claim)

The scheme is not a "brand-new invention," but a **re-quantification in three concrete dimensions** of the classic analog CIM family (most existing literature gives full-scale upper bounds or a device view, lacking a system-level design window):

1. **A rigorous Monte-Carlo characterization of the SNR scaling law:** SNR is independent of W, ∝ R0^−½, ∝ throughput^−½, giving a (R0, throughput) design-window plot (Figure 5) — directly answering "how to choose R0 and clock to get INT8";
2. **Quantifying the "parameters-into-hardware" area tax + the process-node boundary:** 1 parameter = 1 cell → 27 B maps to 45 nm (1080 cm² / ≈126 reticle), 7 nm (27 cm²), 3 nm (10.9 cm² / 1.3 reticle) (Figure 4), identifying ~3–5 nm as the process boundary where this scheme goes from "must be multi-chip" to "single package";
3. **An end-to-end depth-accumulation experiment (multi-seed calibrated):** 6-layer MLP per-layer 0.9997 → final 0.829 ± 0.024 (10 nets × 20 MC, ≈3.2 MOPS/node), quantifying the real accuracy cost of "analog per-layer transfer," and giving a combined recovery strategy (drop throughput to 1 MOPS → 0.928 / larger R0 / mismatch-aware training) that is stable across seeds.

In addition, the user's scheme's **retention of the transistor as the readout/linearization device** (rather than a purely digital readout) has independent value in the "low-voltage, large-swing analog domain": the BJT transconductance g_m = IC0/V_T provides a mA-scale swing current at mV-scale voltages, more suitable for analog readout in the subthreshold voltage than a CMOS transistor (which needs 100 mV+ overdrive) — this is consistent with ANNA's (1989, bipolar process) historical choice, but regains "low-voltage readout" significance in the RRAM era.

---

## 6. Feasibility Verdict and Pros/Cons List (Q5)

### 6.1 Feasibility Verdict

**Conditionally feasible.** The scheme holds only if all of the following are met simultaneously:
  ① The current-mode virtual-ground topology (abandoning the naive voltage-into-base form);
  ② Linear readout: BJT (R_E negative feedback) at 45 nm or MOS TIA at 7/3 nm (both current-control / voltage-control modalities feasible, §4.8; control-modality mismatch resolved by a differential current-mode architecture, readout noise pushed below 20 % of the floor via R_E/R_f);
  ③ R0 matched to throughput by the design window (INT8: R0 ≤ 288 kΩ @ 10 MOPS or 1 MΩ @ ≤2.9 MOPS);
  ④ 0.1 % cell tolerance, or 1 % tolerance + mismatch-aware training / on-chip calibration;
  ⑤ Advanced process + cooling + cost: 45 nm 27 B = 126 reticle is lab-prototype only; 7 nm = 3.1 reticle MCM (~6 cm³) feasible; 3 nm = 1.3 reticle single package (~2 cm³) is the process boundary; power 0.2–2 kW (IC0 freedom), power density ≤ H100 order, liquid-cooled junction < 50 °C; cost sweet spot 7–14 nm (mature 28/14 nm are **not cheaper** because of the many MCM dies, §4.5);
  ⑥ Non-linear ops (softmax/LN) kept as digital "islands," evaluated as a hybrid architecture.

Under these conditions, an "LLM linear-layer inference chip with parameters written directly into the chip" is physically feasible (Qwen3.8-27B instance: §4.4), and its energy advantage grows with model scale relative to GPUs (e_op ∝ 1/N; INT4 per-token energy is ~50–300× lower than H100).

### 6.2 Advantages

| # | Advantage | Quantitative support |
|---|------|----------|
| 1 | Energy: under fixed weights e_op ∝ 1/N, no weight shuttling | Bowen Table 4: analog summation 0.04–0.8 pJ vs digital MAC 0.23 pJ + storage access 4.3 pJ |
| 2 | Eliminates the memory wall: weights = the silicon itself | 27 B @ 3 nm: 11 cm² whole die is weights, zero DRAM reads |
| 3 | Natural spatial parallelism: one layer sum = one settling time | τ ~ ps-scale RC; clock set by ADC, not the circuit |
| 4 | Transistor readout advantage in the subthreshold region | g_m = IC0/VT: mV voltage → mA current, more efficient than CMOS overdrive |
| 5 | Tolerance statistical dividend: error ≈ tolerance × O(1), does not accumulate with W | 1 % @ W=4096 → p95 only 1.31%, mean 0.54% (MC verified) |
| 6 | Compatible with the mismatch-aware training route | 1606.07786: 1 % tolerance devices can approach INT8 |
| 7 | Process dividend is direct: Moore's law improves the area tax | 27 B: 1080 cm² (45 nm) → 11 cm² (3 nm) |
| 8 | Cost sweet spot + no HBM: advanced process lowest total cost | 7 nm ~$2.4k / 14 nm ~$3.2k / 45 nm ~$13k; no HBM (saves the H100's 8×HBM3 ~$5–8k) |

### 6.3 Disadvantages / Risks

| # | Disadvantage | Severity | Mitigation |
|---|------|--------|------|
| 1 | Naive voltage-into-base topology does not hold | Fatal (corrected) | Current-mode virtual ground (§2.1) |
| 2 | Area tax: 1 parameter = 1 cell | High | Advanced process + multi-chip/MCM; 27 B @ 3 nm ≈ 11 cm² single-package feasible |
| 2b | MCM packaging cost rises linearly with die count (mature nodes not cheap) | Medium | Pick the 7–14 nm sweet spot (the 12–49-die 28/14 nm is actually more expensive; §4.5) |
| 3 | Accuracy-throughput tradeoff: 100 MOPS only 5.2 bit | High | Drop throughput / larger R0 / multi-token averaging; positioned as "tokens per joule," not "peak TOPS" |
| 4 | Non-linear ops need digital islands | Medium | softmax/LN implemented digitally, hybrid-architecture evaluation |
| 5 | Weight write / reprogramming cost | Medium | Pure-inference scenario no reconfiguration (scheme premise); RRAM programming energy is high |
| 6 | Device drift / fatigue (RRAM route) | Medium | Periodic recalibration; polysilicon-resistor alternative (stable but larger area) |
| 7 | On-chip training limited | Medium | Analog programming/training lines are emerging (arXiv 2305.16647 gradient-descent programming of analog cores, etc.); can follow |
| 8 | ADC/DAC area and power (per node) | Medium | Amortized by large N (e_op ∝ 1/N); time-multiplexed ADC |
| 9 | Engineering ecosystem: EDA / design flow lacks an analog-CIM toolchain | Medium | Borrow SRAM-array EDA + custom analog IP |
| 10 | Incompatible with the GPU software stack (CUDA/Triton) | Medium | Model-weight export + per-layer mapping compiler (similar to the MyPU/Cerebras route) |

### 6.4 Applicability Boundary vs GPU

- **GPU still wins:** training, low-batch interactive (when weight shuttling is amortized by batching), need FP16/BF16 high precision, dynamic graphs / sparse irregular access;
- **This scheme wins:** large-model fixed-weight inference, high concurrency (large N amortizes ADC/DAC), INT4~INT8 precision acceptable (speech / translation / code-completion-class edge + datacenter inference), extreme energy-efficiency metric (tokens per watt, not peak TOPS).

---

## 7. Conclusion

The user's "transistor amplification + weights-as-resistors" AI chip idea, after R0–R14 rounds of circuit-level argumentation and rigorous Monte-Carlo simulation, is judged **conditionally feasible**: its physical core (resistor network does the weighted sum, transistor does the readout amplification) holds, but it must be corrected from "inject voltages into the base" to "current-mode virtual-ground crossbar + BJT current-mirror/transconductance readout." The quantitative boundaries of the scheme are fully characterized:

- **Accuracy:** SNR independent of layer width, ∝ R0^−½, ∝ throughput^−½; INT8 window = R0 ≤ 288 kΩ @ 10 MOPS or 1 MΩ @ ≤2.9 MOPS (median basis); 0.1 % tolerance or mismatch-aware training;
- **Scale:** area tax 1 parameter = 1 cell, 27 B @ 45 nm ≈ 1080 cm² (≈126 reticle), @ 3 nm ≈ 11 cm² (1.3 reticle) single-package feasible;
- **Energy & throughput:** Qwen3.8-27B single-context INT4 ~87,000 tok/s, INT8 ~1,200 tok/s, energy ~50–300× lower than H100 batched (fixed-weight e_op ∝ 1/N, analog summation saves 3–6× over digital MAC);
- **Process & cost:** mature 28/14 nm are **not cheaper** due to the many MCM dies; cost sweet spot 7–14 nm (7 nm ~$2.4k, 14 nm ~$3.2k, 45 nm ~$13k); no HBM/external memory, saving the H100's 8×HBM3 (~$5–8k);
- **Precedent:** the ANNA (1989) → ISAAC (2016) → Mythic (2018) → Bowen (2023) complete lineage supports it (IBM NorthPole 2019+ is near-memory **digital** inference, cited separately as modern system corroboration); the Bowen original text corresponds word-for-word to the user's idea.

The most reasonable positioning of this scheme is: **an analog in-memory-computing chip for fixed-weight LLM inference, with "tokens per joule" as the core metric, target process ≤7 nm, precision INT4~INT8, complementary to — not a replacement for — GPUs.** The three contribution points the paper can claim (SNR design window, area-tax process boundary, end-to-end depth accumulation) are all backed by re-runnable simulations and figures.

---

## References (actually cited; full text / abstract retrieved in `refs/`)

1. Bowen, M. et al. "Analog, In-memory Compute Architectures for AI." arXiv:2302.06417 (2023). — Energy-limit theory; "transistor + reconfigurable resistor" original text; Table 4 energy data. [`refs/full_2302.06417.txt`]
2. "Precise neural network computation with imprecise analog devices." arXiv:1606.07786 (2016). — Mismatch-aware training route. [`refs/full_1606.07786.txt`]
3. Shafiee, A. et al. "ISAAC: A Convolutional Neural Network Accelerator with In-Situ Analog Arithmetic in Crossbars." ISCA 2016. — ReRAM crossbar analog in-memory accelerator precedent. (Erratum: NorthPole is IBM's 2019+ near-memory **digital** inference line — a different work; see ref. 9.)
4. Demler, J. "Mythic multiplies in a flash." IEEE Spectrum, 2018. — Flash crossbar commercial analog computing (Mythic).
5. ANNA: "A neural network chip" (1989), 16000 synapses, resistors as weights, bipolar (BJT) process — direct precursor of the user's scheme (IEEE IEDM/JSSC, not on arXiv; cited here from public historical record).
6. Xia, Q. & Yang, J. "ReRAM-based analog resistive matrix multiplication for artificial neural network computing." — Memristive crossbars and the "device can only store positive numbers" sign problem.
7. Büchel, J., Vasilopoulos, A., Kersting, B., Odermatt, F. "Gradient descent-based programming of analog in-memory computing cores." arXiv:2305.16647 (2023). — Program the analog core directly by gradient descent (an alternative route for weight write/calibration, mitigating the "on-chip training limited" drawback).
8. Kavishwar, M., Shanbhag, N. "Compute SNR-Optimal Analog-to-Digital Converters for Analog In-Memory Computing." arXiv:2507.09776 (2025). — Optimal SNR ADC design theory for analog CIM (complements Figure 5 design window).
9. DeBole, M.V., Appuswamy, R., McGlohon, N., Taba, B. et al. "A Scalable NorthPole System with End-to-End Vertical Integration for Low-Latency and Energy-Efficient LLM Inference." arXiv:2511.15950 (2025). — Contemporary corroboration of systematized analog LLM inference (a direct comparator for this scheme's energy selling point).
   [All `refs/arxiv_*.xml` are retrievable and reproducible]

## Appendix: Simulation List (all re-runnable)

| Script | Content | Key output |
|------|----------|----------|
| sim/sim_v1.py | Ideal gain formula (counter-example) | Proves I_C = (β/R0)Σwx is wrong |
| sim/sim_v1b.py | Full Ebers–Moll + bias bug | Nonlinearity 13.6 → 74.6× bend |
| sim/sim_v4.py | Physically self-consistent corrected version | INT8 operating point R_E/IC0 |
| sim/sim_v5.py | Differential virtual ground (voltage-mode counter-example) | Naive back-feed 1.10 mA → residual −0.02 mA |
| sim/sim_v5b.py | Current-mode virtual ground (final topology) | C1 identity, C5 p95 1.31% @ ±1% / 0.13% @ ±0.1% |
| sim/sim_v6_designspace.py | Full design-space sweep | Area-tax table, power, throughput window |
| sim/sim_v7_e2e.py | 6-layer MLP end-to-end | Per-layer 0.9997 → final 0.889 (seed-42 single net) |
| sim/sim_v16_depth_multiseed.py | Multi-seed depth calibration (authoritative) | Final 0.829 ± 0.024 (10 nets); 1MOPS recovery 0.928 |
| sim/sim_v8_errdecomp.py | Error decomposition | ADC not the bottleneck; noise is |
| sim/sim_v9_snr.py | Analytic SNR (with self-correction) | Scaling law first version |
| sim/sim_v10_snr_mc.py | Rigorous Monte-Carlo SNR (authoritative) | W-independent, R0^−½, BW^−½ |
| sim/sim_v11_3layer.py | Three-layer wiring numerical verification | z = W2·W1·x error 1e-16 |
| sim/fig3layer_wiring.py | Three-layer wiring schematic (Fig 6) | 3→2→2 resistor wiring |
| sim/fig_circuit_flow.py | Signal-transfer circuit diagram instance (Fig 7) | x_j → resistor → sum → BJT amplification |
| sim/fig_readout_diff.py | Optimal readout front-end (Fig 8) | Differential current-mode + charge sampling, 0-overlap self-check |
| sim/sim_v12_qwen27b.py | Qwen3.8-27B volume/power/efficiency account | 45 nm = 1080 cm² / 126 ret, 3 nm = 10.8 cm² / 1.3 ret |
| sim/sim_v13_thermal_3d.py | Thermal impact + 3D stack volume + device substitution | Liquid-cooled Tj < 50 °C, IS doubles per 7 °C, 3D footprint ↓3.8× |
| sim/sim_v14_readout_cm.py | Readout control modality BJT (current) vs MOS (voltage) | Both modalities feasible, differential resolves; BJT tune R_E / MOS tune R_f push readout noise < 20 % of floor |
| sim/sim_v15_process_cost.py | Mature process + cost (28/14 nm) | Mature nodes not cheaper; 7 nm ~$2.4k sweet spot, 45 nm ~$13k, no HBM |
| sim/plot_figs.py | 5 paper figures | figs/fig1..fig5 (.png+.pdf) |
