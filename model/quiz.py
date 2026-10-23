"""
Golden model of the Purple, Green, or Orange? quiz chip (Tier 1: scoring core).

The chip stores no text. The player reads the questions from a printed card
(`card`), picks A, B or C on the DIP switches and presses the button. The chip
looks up which colour that answer belongs to, counts the colours, and shows the
result on the 7-segment display after question 15.

Colours
  PURPLE  fun and technical
  GREEN   aggressively, enthusiastically in sales
  ORANGE  neither: a bit lost, a bit boring

Scoring rule (plurality, Orange wins ties)
  p, g, o = how many Purple, Green and Orange answers (p + g + o = 15)
  PURPLE  if p > g and p > o
  GREEN   if g > p and g > o
  ORANGE  otherwise (Orange leads, or any tie for the lead: undecided is Orange)

Each question lists its answers in display order (A, B, C). The colour behind
each letter changes from question to question, so "always pick A" doesn't win.
That letter-to-colour table (15 x 3 x 2 bits = 90 bits) is the chip's only ROM.

Usage
  python3 model/quiz.py card               printable quiz card (Markdown)
  python3 model/quiz.py rom                Verilog case statement for the ROM
  python3 model/quiz.py vectors [out.json] test vectors for cocotb
  python3 model/quiz.py stats              result odds for a random player, letter balance
  python3 model/quiz.py selftest
"""
import json
import random
import sys
from math import comb

PURPLE, GREEN, ORANGE = 0, 1, 2           # 2-bit colour codes, as stored in the ROM
NAMES = {PURPLE: 'Purple', GREEN: 'Green', ORANGE: 'Orange'}
P, G, O = PURPLE, GREEN, ORANGE
LETTERS = 'ABC'
N_Q = 15

# (question, [(answer text, colour) for A, B, C])
QUESTIONS = [
    ("Your ideal Saturday morning:", [
        ("Cold-calling leads before the competition wakes up.", G),
        ("Building an LED badge that plays a tune when you shake it.", P),
        ("Laundry. Maybe. I haven't decided.", O)]),
    ("Someone sends you a calendar invite titled 'quick sync'. You:", [
        ("Bring a whiteboard marker and a diagram nobody asked for.", P),
        ("Accept it, then forget which meeting it was.", O),
        ("Turn it into an upsell before the agenda loads.", G)]),
    ("Your phone's home screen is:", [
        ("The default wallpaper. Still.", O),
        ("A CRM with 47 notifications, every one an opportunity.", G),
        ("A terminal app, a synth app and a folder of memes.", P)]),
    ("A colleague's change breaks the build. You:", [
        ("Bisect it, fix it, and send them a gif of the culprit commit.", P),
        ("Sell them a premium support plan.", G),
        ("Wait for someone else to notice.", O)]),
    ("Pick a superpower:", [
        ("Closing any deal with a single handshake.", G),
        ("Sorry, what were the options again?", O),
        ("Seeing radio waves.", P)]),
    ("Your LinkedIn headline:", [
        ("Breaks things professionally, fixes them for fun.", P),
        ("Employee.", O),
        ("Revenue Ninja | Closer | Hustle 24/7 | DM me", G)]),
    ("At a party, you're most likely:", [
        ("Standing near the snacks, nodding.", O),
        ("Handing your business card to the host's grandma.", G),
        ("Explaining why the speakers hum, then fixing it.", P)]),
    ("Favourite number:", [
        ("0x2A.", P),
        ("Quota, plus 30 percent.", G),
        ("Seven? Everyone says seven.", O)]),
    ("A new gadget arrives. You:", [
        ("Resell it at a markup before opening it.", G),
        ("Open it with a screwdriver before reading the manual.", P),
        ("Leave it in the box for a month.", O)]),
    ("Your email sign-off:", [
        ("Regards.", O),
        ("Cheers, sent from my hand-wired keyboard.", P),
        ("Let's circle back at 7 am tomorrow. Sent from my car.", G)]),
    ("Someone tells you 'no'. You:", [
        ("Hear 'not yet' and follow up in five minutes.", G),
        ("Accept it. It was probably the right answer anyway.", O),
        ("Ask for the error message and start debugging.", P)]),
    ("Pick a lunch:", [
        ("Whatever the vending machine gives after the Konami code.", P),
        ("Plain toast.", O),
        ("Steak with a client, expensed.", G)]),
    ("Your desk has:", [
        ("A stapler. Nothing else.", O),
        ("A gong you hit every time you close a deal.", G),
        ("An oscilloscope, a rubber duck and three half-built projects.", P)]),
    ("Your dream job title:", [
        ("Chief Revenue Officer, by 30.", G),
        ("Chip designer who also makes the demo video.", P),
        ("Whatever pays, I suppose.", O)]),
    ("This quiz is running on a chip you could hold on a fingertip. Your reaction:", [
        ("Okay.", O),
        ("Can I see the layout?", P),
        ("How many units can I pre-sell?", G)]),
]

RESULTS = {
    PURPLE: ("Purple", "Fun and technical. You read datasheets for pleasure and still get invited to parties."),
    GREEN: ("Green", "Pure sales energy. You'd sell this chip back to the people who made it, at a markup."),
    ORANGE: ("Orange", "Neither. A little lost, a little beige, and honestly that's fine."),
}


def colour_of(q, letter):
    """Colour of answer `letter` (0 = A, 1 = B, 2 = C) to question q (0..14)."""
    return QUESTIONS[q][1][letter][1]


def counts(colours):
    return tuple(sum(1 for c in colours if c == k) for k in (PURPLE, GREEN, ORANGE))


def decide(p, g, o):
    """The scoring rule. In hardware: two 4-bit counters (o = 15 - p - g) and four comparisons."""
    if p > g and p > o:
        return PURPLE
    if g > p and g > o:
        return GREEN
    return ORANGE


def score(letters):
    """letters: 15 answers, each 0/1/2 for A/B/C. Returns (result, colours, (p, g, o))."""
    assert len(letters) == N_Q and all(l in (0, 1, 2) for l in letters)
    colours = [colour_of(q, l) for q, l in enumerate(letters)]
    pgo = counts(colours)
    return decide(*pgo), colours, pgo


def check_data():
    assert len(QUESTIONS) == N_Q
    for i, (text, opts) in enumerate(QUESTIONS):
        assert len(opts) == 3, f'Q{i + 1}: needs 3 answers'
        assert sorted(c for _, c in opts) == [PURPLE, GREEN, ORANGE], f'Q{i + 1}: one answer per colour'


# ---------------------------------------------------------------- exports

def card():
    out = ['# Purple, Green, or Orange?', '',
           'Set the switches to your answer (A, B or C) and press the button. '
           'The display shows the question number; after question 15 it shows your colour.', '']
    for i, (text, opts) in enumerate(QUESTIONS):
        out.append(f'**{i + 1}. {text}**')
        out.append('')
        for l, (a, _) in zip(LETTERS, opts):
            out.append(f'- **{l}** {a}')
        out.append('')
    out.append('**Results:** ' + ' · '.join(f'{n}: {d}' for n, d in RESULTS.values()))
    return '\n'.join(out)


def rom_verilog():
    """Module pog_rom: {q[3:0], ans[1:0]} -> colour[1:0]. ans is 1..3 for A..C (0 = no answer)."""
    lines = ['// Generated by model/quiz.py rom > src/pog_rom.v. Do not edit by hand.',
             '// colour: 0 = purple, 1 = green, 2 = orange',
             '`default_nettype none', '',
             'module pog_rom (',
             '    input  wire [3:0] q,       // question 0..14',
             '    input  wire [1:0] ans,     // 1 = A, 2 = B, 3 = C',
             '    output reg  [1:0] colour',
             ');',
             '  always @(*) begin',
             '    case ({q, ans})']
    for q in range(N_Q):
        for l in range(3):
            c = colour_of(q, l)
            lines.append(f"      {{4'd{q}, 2'd{l + 1}}}: colour = 2'd{c};   // Q{q + 1} {LETTERS[l]}: {NAMES[c]}")
    lines += ["      default: colour = 2'd2;", '    endcase', '  end', 'endmodule']
    return '\n'.join(lines)


def vectors(n_random=2000, seed=1):
    """Edge cases (all A/B/C, ties, all one colour) plus seeded random players."""
    rng = random.Random(seed)
    cases = [[l] * N_Q for l in range(3)]
    for want in (PURPLE, GREEN, ORANGE):                       # all answers one colour
        cases.append([[c for _, c in opts].index(want) for _, opts in QUESTIONS])
    # exact count patterns around the decision boundaries
    for p, g, o in [(5, 5, 5), (6, 6, 3), (6, 5, 4), (5, 6, 4), (7, 7, 1), (4, 4, 7), (7, 1, 7), (1, 7, 7),
                    (8, 7, 0), (7, 8, 0), (6, 3, 6), (3, 6, 6), (5, 4, 6), (6, 4, 5)]:
        cols = [PURPLE] * p + [GREEN] * g + [ORANGE] * o
        rng.shuffle(cols)
        cases.append([[c for _, c in QUESTIONS[q][1]].index(col) for q, col in enumerate(cols)])
    cases += [[rng.randrange(3) for _ in range(N_Q)] for _ in range(n_random)]
    out = []
    for letters in cases:
        r, colours, pgo = score(letters)
        out.append({'answers': [l + 1 for l in letters], 'colours': colours,
                    'p': pgo[0], 'g': pgo[1], 'o': pgo[2], 'result': r})
    return out


def stats():
    """Exact odds for a player answering uniformly at random (each colour 1/3 per question)."""
    tot = {PURPLE: 0, GREEN: 0, ORANGE: 0}
    for p in range(N_Q + 1):
        for g in range(N_Q + 1 - p):
            o = N_Q - p - g
            tot[decide(p, g, o)] += comb(N_Q, p) * comb(N_Q - p, g)
    n = 3 ** N_Q
    lines = ['Random player: ' + ', '.join(f'{NAMES[k]} {100 * v / n:.1f} %' for k, v in tot.items())]
    for k in (PURPLE, GREEN, ORANGE):
        pos = [sum(1 for _, opts in QUESTIONS if opts[i][1] == k) for i in range(3)]
        lines.append(f'{NAMES[k]:6} answers at A/B/C: {pos[0]}/{pos[1]}/{pos[2]}')
    return '\n'.join(lines)


def selftest():
    check_data()
    assert decide(5, 5, 5) == ORANGE and decide(6, 6, 3) == ORANGE      # ties are Orange
    assert decide(6, 5, 4) == PURPLE and decide(5, 6, 4) == GREEN
    assert decide(7, 1, 7) == ORANGE and decide(6, 4, 5) == PURPLE
    for want in (PURPLE, GREEN, ORANGE):
        letters = [[c for _, c in opts].index(want) for _, opts in QUESTIONS]
        assert score(letters)[0] == want
    assert all(score([l] * N_Q)[0] == ORANGE for l in range(3)), 'one letter all the way should not win'
    for v in vectors(200):
        assert v['p'] + v['g'] + v['o'] == N_Q
    print('selftest ok')


if __name__ == '__main__':
    check_data()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    if cmd == 'card':
        print(card())
    elif cmd == 'rom':
        print(rom_verilog())
    elif cmd == 'vectors':
        path = sys.argv[2] if len(sys.argv) > 2 else 'vectors.json'
        v = vectors()
        json.dump(v, open(path, 'w'), indent=0)
        print(f'wrote {len(v)} vectors to {path}')
    elif cmd == 'stats':
        print(stats())
    elif cmd == 'selftest':
        selftest()
    else:
        sys.exit(__doc__)
