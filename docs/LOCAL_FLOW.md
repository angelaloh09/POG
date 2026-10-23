# Running Quiz Chip locally

Run these commands from the Quiz Chip repository root. Docker must be running.
`tools/osic` mounts this checkout at `/w` inside the container, selects SKY130,
and preserves the tool's exit status. It sets `PDK`, `PDKPATH`, and the
standard-cell library **after** the login script, which otherwise resets the
technology to IHP despite Docker `-e PDK=sky130A`. It does not use the radio repo's
machine-specific `/home/matt/...` or `/Users/mattvenn/...` paths.

The local image is `hpretl/iic-osic-tools:2026.05` (already installed on the
development Mac). On a new machine, fetch it with
`docker pull hpretl/iic-osic-tools:2026.05`.

## RTL simulation

```bash
tools/osic bash -c 'set -e
  python3 model/quiz.py selftest
  cd test
  make -B
  python3 -m cocotb_tools.check_results results.xml
'
```

This replays all 2,020 model vectors and checks no-answer and button-bounce
behavior. Results are in `test/results.xml`; waveforms are in `test/tb.fst`.
Running `make` directly on the Mac requires a separate Icarus/cocotb install.

## Physical layout build

The `tt/` support-tool checkout must exist. On a fresh clone, obtain it from
<https://github.com/TinyTapeout/tt-support-tools> and use the revision selected
by the target shuttle's GDS action.

The image bundles the physical design tools, but lacks three Python helper
packages used by the checked-out support tools. Install those into the
disposable container, generate the configuration, and build into a new run:

```bash
tools/osic bash -c 'set -e
  python3 -m pip install --quiet --target /tmp/tt-extra --no-deps \
    chevron==0.14.0 configupdater==3.2 python-frontmatter==1.1.0
  export PYTHONPATH="/tmp/tt-extra:$PYTHONPATH"
  python3 tt/tt_tool.py --create-user-config
  run_dir="runs/local-$(date -u +%Y%m%d-%H%M%S)"
  mkdir -p runs
  mkdir "$run_dir"
  python3 -m librelane --manual-pdk --pdk-root /foss/pdks \
    --pdk sky130A --scl sky130_fd_sc_hd --jobs 4 \
    --run-tag local --force-run-dir "$run_dir" src/config_merged.json
'
```

The output directory must exist before `--force-run-dir` is passed to this LibreLane
version. Each run contains `final/gds/`, `final/lef/`, `final/pnl/`, and
`final/metrics.json`. The existing `runs/wokwi` trial is preserved.

Installing all of `tt/requirements.txt` over the image is unnecessary for
these commands. On this ARM64 image it attempts to rebuild a pinned `gdstk`
and fails because the Qhull development library is absent.

## Gate-level simulation

Choose the run whose netlist you intend to check; this example uses the
original trial run:

```bash
tools/osic bash -c 'set -e
  cp runs/wokwi/final/pnl/tt_um_pog_quiz.pnl.v test/gate_level_netlist.v
  cd test
  make -B GATES=yes COCOTB_RESULTS_FILE=results_gl.xml
  python3 -m cocotb_tools.check_results results_gl.xml
'
```

SKY130 requires the powered (`pnl`) netlist. The gate-level test uses the real
17-bit debounce counter, so it runs much longer than the RTL test, whose
counter is shortened. The gate-level quiz vectors cover all three result
colours. The display check waits through the real blink interval when the
result is initially dark; the old 40-clock window could falsely fail. Both modes write `test/tb.fst`; run them sequentially.

### Gate-level run with Verilator

The corrected suite was also run with the image's Verilator 5.048. After
copying the powered netlist as above:

```bash
tools/osic bash -c 'set -e
  cd test
  COMPILE_ARGS="-Wno-fatal --timing" make -B GATES=yes SIM=verilator \
    SIM_BUILD=sim_build/gl_verilator COCOTB_RESULTS_FILE=results_gl_verilator.xml
  python3 -m cocotb_tools.check_results results_gl_verilator.xml
'
```

The emitted Verilator warnings were `PINMISSING` for unused well/tie-cell
ports. This invocation does not enable waveform tracing. Shuttle CI uses
Icarus; retain that check as part of submission.

## Local precheck

Stage the GDS, LEF, and powered netlist together under the same basename.
Set `run_dir` to the run you built, then run from `tt/precheck` so its relative
rule-deck and DEF-template paths resolve:

```bash
tools/osic bash -c 'set -e
  run_dir=/w/runs/codex-local-20261023
  mkdir -p "$run_dir/precheck-input"
  cp "$run_dir/final/gds/tt_um_pog_quiz.gds" "$run_dir/precheck-input/"
  cp "$run_dir/final/lef/tt_um_pog_quiz.lef" "$run_dir/precheck-input/"
  cp "$run_dir/final/pnl/tt_um_pog_quiz.pnl.v" "$run_dir/precheck-input/tt_um_pog_quiz.v"
  cd tt/precheck
  python3 precheck.py --gds "$run_dir/precheck-input/tt_um_pog_quiz.gds" --tech sky130A
'
```

Reports are in `tt/precheck/reports/results.md` and `results.xml`. Passing
requires every check to pass; a missing tool or technology file is a failure.

## Submission checks and version differences

These are local development runs. The installed image has LibreLane 3.0.3
and cocotb 2.0.1; `test/requirements.txt` pins cocotb 2.1.0 for CI. As checked
on 2026-10-23, `tt-gds-action@ttsky26d` selects LibreLane 3.0.14, and its SKY130
precheck selects PDK revision `0536d02d875c8f67dd7cca3902ac457e62f20005`.
The bundled SKY130 PDK is open_pdks `7b70722e33c03fcb5dabcf4d479fb0822d9251c9`;
final submission still needs the shuttle action with its selected tool and PDK versions.

The existing `.github/workflows/gds.yaml` runs the digital GDS build,
precheck, gate-level test, and viewer. The radio repo uses the `custom_gds`
action because it supplies a manually assembled mixed-signal layout. Quiz
Chip uses the digital action to generate its layout from Verilog.

Official references:

- [Tiny Tapeout local hardening](https://tinytapeout.com/guides/local-hardening/)
- [TTSKY26d GDS action](https://github.com/TinyTapeout/tt-gds-action/blob/ttsky26d/action.yml)
- [TTSKY26d precheck](https://github.com/TinyTapeout/tt-gds-action/blob/ttsky26d/precheck/action.yml)
- [IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS)

## Local results, 2026-10-23

- Model self-test and all three RTL tests passed (2,020 quiz vectors).
- Fresh layout: `runs/codex-local-20261023/final/gds/tt_um_pog_quiz.gds`.
- Routing DRC, Magic DRC, LVS, and antenna violation counts: zero.
- Worst setup slack: +9.467 ns; worst hold slack: +0.109 ns at the configured
  20 ns clock period (50 MHz). The intended quiz clock remains 10 MHz.
- All 15 local Tiny Tapeout prechecks passed with the bundled SKY130 PDK.
- The fresh powered netlist is byte-for-byte identical to the existing
  `runs/wokwi/final/pnl/tt_um_pog_quiz.pnl.v`.
- Corrected gate-level suite: 3/3 tests passed with Verilator 5.048, covering
  Purple, Green, Orange, no-answer, and button bounce (193 seconds of simulation).
  Report: `test/results_gl_verilator.xml`; RTL rerun: `runs/codex-local-20261023/rtl-results.xml`.
