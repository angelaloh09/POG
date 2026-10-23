# Purple, Green, or Orange? on a chip

A Tiny Tapeout chip (sky130) that can run only one thing: the *Purple, Green, or Orange?* quiz.

- **Purple:** fun and technical.
- **Green:** aggressively, enthusiastically in sales.
- **Orange:** neither. A little lost, a little boring.

**Tier 1 (this plan):** the chip does the scoring. The questions are printed on a card, [QUIZ_CARD.md](QUIZ_CARD.md). The player picks A, B or C on the DIP switches, presses the button, and reads the result on the 7-segment display.

## Source of truth: `model/quiz.py`

The questions, the hidden letter-to-colour table and the scoring rule all live in [model/quiz.py](model/quiz.py). Everything else is generated from it:

| command | output |
|---|---|
| `python3 model/quiz.py card > QUIZ_CARD.md` | the printable quiz card |
| `python3 model/quiz.py rom` | the Verilog `case` for the colour ROM |
| `python3 model/quiz.py vectors model/vectors.json` | 2,020 test vectors for cocotb |
| `python3 model/quiz.py stats` | result odds for a random player, letter balance |
| `python3 model/quiz.py selftest` | checks the data and the rule |

If you edit a question, rerun `selftest` and regenerate the card, the ROM and the vectors.

### Scoring rule

`p`, `g` and `o` are the counts of Purple, Green and Orange answers (`p + g + o = 15`).

- **Purple** if `p > g` and `p > o`.
- **Green** if `g > p` and `g > o`.
- **Orange** otherwise: Orange leads, or there's a tie for the lead. Being undecided counts as Orange.

**Balance:**
- Each letter (A, B, C) hides exactly 5 Purple, 5 Green and 5 Orange answers. Picking the same letter every time gives 5/5/5, which is Orange.
- A player who answers at random gets Purple 28.3 %, Green 28.3 % and Orange 43.4 %.

## Tier 1 chip spec (draft)

| pin | function |
|---|---|
| `ui_in[1:0]` | answer: 1 = A, 2 = B, 3 = C (0 = none; the button is ignored) |
| `ui_in[7]` | **Next** button (synchronised and debounced, acts on the press) |
| `rst_n` | restart the quiz |
| `uo_out[6:0]` | 7-segment display |
| `uo_out[7]` | decimal point: lit for questions 10–15 (`3.` = question 13) |
| `uio_out[1:0]` | result code (0 Purple, 1 Green, 2 Orange), valid when `uio_out[2]` = 1 |
| `uio_out[2]` | done |
| `uio_out[6:3]` | current question index 0–14 (debug) |

**Display:**
- During the quiz it shows the question number 1–15, using the decimal point for 10–15.
- After question 15 it blinks the result as a letter: `P`, `G`, or a lowercase `o`. The lowercase `o` keeps the result from looking like the digit 0.

**Logic:**
- a 4-bit question counter;
- a 90-bit colour ROM, written as a generated `case` statement;
- two 4-bit counters for `p` and `g` (`o` = 15 − `p` − `g`);
- four comparators;
- a debounce counter and a blink divider;
- a 7-segment decoder.

This should fit comfortably in one 1×1 digital tile.

Pressing **Next** on the result screen restarts the quiz.

## Plan

1. **Model** ✅ `model/quiz.py`, the card and the vectors.
2. **RTL** ✅ [src/project.v](src/project.v) (`tt_um_pog_quiz`) and [src/pog_rom.v](src/pog_rom.v), generated with `python3 model/quiz.py rom > src/pog_rom.v`.
3. **cocotb tests** ✅ [test/test.py](test/test.py) replays all 2,020 model vectors through the pins: result code, done flag, question number and 7-segment patterns. There are also tests for Next with no answer and for a bouncy button. Run them with `cd test && make`.
4. **Local trial harden** ✅ LibreLane 3 via the TT config, on one 1×1 tile (161 × 111.5 µm). Results:
   - 614 standard cells (56 flip-flops), 27 % utilisation;
   - 0 routing DRC, 0 magic DRC, 0 LVS errors;
   - setup slack +9.5 ns, hold slack +0.11 ns at 50 MHz.

   Picture: [docs/images/pog_layout.png](docs/images/pog_layout.png).
5. **Next:**
   - push to GitHub so the TT Action hardens it with the pinned PDK and runs the precheck and the gate-level test;
   - submit to a shuttle.

### Running things locally (IIC-OSIC-TOOLS container)

See [docs/LOCAL_FLOW.md](docs/LOCAL_FLOW.md) for the portable `tools/osic` helper, verified commands, and local-versus-shuttle tool-version constraints.

```bash
docker run --rm -v "$PWD:/w" -w /w --entrypoint /bin/bash hpretl/iic-osic-tools:2026.05 -lc 'cd test && make -B'
```

For the trial harden, set `PDK=sky130A STD_CELL_LIBRARY=sky130_fd_sc_hd` in the container (it defaults to IHP). Then run:

```bash
python3 -m librelane --manual-pdk --pdk-root /foss/pdks --pdk sky130A --scl sky130_fd_sc_hd --run-tag wokwi --force-run-dir runs/wokwi src/config_merged.json
```

Make `src/config_merged.json` first with `./tt/tt_tool.py --create-user-config`. That needs a clone of tt-support-tools in `tt/`.
