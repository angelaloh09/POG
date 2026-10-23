## How it works

This chip runs the *Purple, Green, or Orange?* quiz. Read the 15 questions and answer choices on the supplied quiz card. Set `ui_in[1:0]` to 1 for A, 2 for B, or 3 for C, then hold `ui_in[7]` high for at least 14 ms and release it for at least 14 ms to submit each answer. The button input is synchronized and debounced. Answer code 0 is ignored during the quiz; Next still restarts from the result screen.

The 7-segment display shows the current question number. For questions 10–15, the decimal point is lit and the digit shows the ones place. After question 15, the display blinks the result: P for Purple, G for Green, or lowercase o for Orange. Purple or Green wins only with a count strictly greater than each of the other two colours; a tie is Orange. `uio_out[1:0]` reports 0 for Purple, 1 for Green, or 2 for Orange, and `uio_out[2]` indicates that the quiz is complete. `uio_out[6:3]` exposes the current question index (0–14).

Hold `rst_n` low to restart. Press Next after the result to begin another quiz.

## How to test

The segment outputs are active high. Connect a compatible display interface to `uo_out[6:0]` (segments a–g) and its decimal point to `uo_out[7]`. Use a switch or jumper to set `ui_in[1:0]`; connect a momentary button to `ui_in[7]`. The chip uses a 10 MHz clock. Keep the answer stable while pressing Next. Read the result from the display or `uio_out[1:0]` when `uio_out[2]` is high.

## External hardware

A 7-segment display, three answer-selection states (two switches or equivalent), a momentary Next button, and a 10 MHz clock source are required. A separate display needs appropriate current limiting and any required drivers; keep button and switch inputs at defined logic levels.
