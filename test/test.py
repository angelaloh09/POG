# SPDX-License-Identifier: Apache-2.0
# POG quiz chip tests: replay model/vectors.json (from model/quiz.py) through the pins.
#   make                RTL, all 2,020 vectors
#   make GATES=yes      gate level, a few vectors (the real 13 ms debounce is slow to simulate)
import json
import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, ValueChange, with_timeout

HERE = os.path.dirname(os.path.abspath(__file__))
VECTORS = json.load(open(os.path.join(HERE, '..', 'model', 'vectors.json')))

DIGITS = [0b0111111, 0b0000110, 0b1011011, 0b1001111, 0b1100110,
          0b1101101, 0b1111101, 0b0000111, 0b1111111, 0b1101111]
LETTER = {0: 0b1110011, 1: 0b0111101, 2: 0b1011100}     # P, G, o
NAMES = {0: 'Purple', 1: 'Green', 2: 'Orange'}


def expected_number(n):
    """uo_out while showing question n (1..15): digit, dp for 10..15."""
    return DIGITS[n % 10] | (0x80 if n >= 10 else 0)


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, 100, unit='ns').start())   # 10 MHz
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    return 2 ** int(dut.debounce_w.value) + 4     # cycles to hold a button level


async def press(dut, ans, hold):
    """Set the answer (0..3), press Next and release it."""
    dut.ui_in.value = ans
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = 0x80 | ans
    await ClockCycles(dut.clk, hold)
    dut.ui_in.value = ans
    await ClockCycles(dut.clk, hold)


def state(dut):
    uio = int(dut.uio_out.value)
    return {'result': uio & 3, 'done': (uio >> 2) & 1, 'q': (uio >> 3) & 0xF}


async def play(dut, v, hold):
    for i, a in enumerate(v['answers']):
        st = state(dut)
        assert st['done'] == 0 and st['q'] == i, f'before Q{i + 1}: {st}'
        assert int(dut.uo_out.value) == expected_number(i + 1), f'display at Q{i + 1}'
        await press(dut, a, hold)
    st = state(dut)
    assert st['done'] == 1, 'not done after 15 answers'
    assert st['result'] == v['result'], \
        f"p/g/o {v['p']}/{v['g']}/{v['o']}: chip says {NAMES[st['result']]}, model says {NAMES[v['result']]}"
    # the display blinks the result letter: it must show it, and nothing else
    seen = set()
    for _ in range(40):
        seen.add(int(dut.uo_out.value))
        await ClockCycles(dut.clk, 1)
    # In gate-level simulation the real blink half-period is 2^22 clocks.
    # A 40-clock observation can legitimately fall entirely in the dark phase.
    # Wait for the display to change, bounded by one half-period, then allow
    # the standard-cell combinational paths to settle before sampling.
    if seen == {0}:
        half_period_ns = (1 << (int(dut.blink_w.value) - 1)) * 100
        await with_timeout(ValueChange(dut.uo_out), half_period_ns + 100, "ns")
        await Timer(50, unit="ns")
        seen.add(int(dut.uo_out.value))
    assert seen <= {LETTER[v['result']], 0} and LETTER[v['result']] in seen, f'display {seen}'


@cocotb.test()
async def test_vectors(dut):
    """Every model vector, back to back; Next on the result screen restarts the quiz."""
    hold = await setup(dut)
    gl = int(dut.debounce_w.value) > 8
    # The first three vectors all score Orange; cover every result at gate level.
    vecs = [next(v for v in VECTORS if v["result"] == r) for r in range(3)] if gl else VECTORS
    for n, v in enumerate(vecs):
        await play(dut, v, hold)
        await press(dut, 0, hold)                       # restart
        if n % 500 == 0:
            dut._log.info(f'{n + 1} / {len(vecs)} vectors ok')
    dut._log.info(f'all {len(vecs)} vectors match the model')


@cocotb.test()
async def test_no_answer_is_ignored(dut):
    """Next with no answer selected doesn't advance."""
    hold = await setup(dut)
    await press(dut, 0, hold)
    assert state(dut)['q'] == 0
    await press(dut, 1, hold)
    assert state(dut)['q'] == 1


@cocotb.test()
async def test_bouncy_button(dut):
    """A press that bounces for a while still counts once."""
    hold = await setup(dut)
    dut.ui_in.value = 2
    await ClockCycles(dut.clk, 2)
    for k in range(12):                                  # bounces shorter than the debounce time
        dut.ui_in.value = 0x80 | 2 if k % 2 == 0 else 2
        await ClockCycles(dut.clk, max(1, hold // 4))
    dut.ui_in.value = 0x82
    await ClockCycles(dut.clk, hold)
    for k in range(12):
        dut.ui_in.value = 2 if k % 2 == 0 else 0x82
        await ClockCycles(dut.clk, max(1, hold // 4))
    dut.ui_in.value = 2
    await ClockCycles(dut.clk, hold)
    assert state(dut)['q'] == 1, f"q = {state(dut)['q']} after one bouncy press"
