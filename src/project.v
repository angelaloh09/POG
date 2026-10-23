/*
 * POG: Purple, Green, or Orange? quiz chip.
 * SPDX-License-Identifier: Apache-2.0
 *
 * The player reads the questions from the printed card (QUIZ_CARD.md), sets
 * the answer on ui_in[1:0] (1 = A, 2 = B, 3 = C) and presses Next (ui_in[7]).
 * After question 15 the display blinks the result: P, G or o.
 * Pressing Next on the result restarts the quiz.
 *
 * Scoring (model/quiz.py is the reference): p, g, o = counts of Purple, Green,
 * Orange answers. Purple if p > g and p > o; Green if g > p and g > o; else Orange.
 *
 * Pins
 *   ui_in[1:0]    answer (0 = none: Next is ignored)
 *   ui_in[7]      Next button (synchronised, debounced, acts on the press)
 *   uo_out[6:0]   7-segment a..g, uo_out[7] = dp (lit for questions 10..15)
 *   uio_out[1:0]  result (0 purple, 1 green, 2 orange), valid when uio_out[2] = 1
 *   uio_out[2]    done
 *   uio_out[6:3]  question index 0..14
 */

`default_nettype none

module tt_um_pog_quiz #(
    parameter DEBOUNCE_W = 17,   // 2^17 clocks = 13 ms at 10 MHz
    parameter BLINK_W    = 23    // result blinks every 2^22 clocks = 0.42 s at 10 MHz
) (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
  localparam PURPLE = 2'd0, GREEN = 2'd1, ORANGE = 2'd2;
  localparam LAST_Q = 4'd14;

  // ---------------------------------------------------------------- Next button
  reg [1:0] btn_sync;
  reg btn_stable;
  reg [DEBOUNCE_W-1:0] btn_cnt;
  wire press = btn_sync[1] & ~btn_stable & (&btn_cnt);   // stable-high edge

  always @(posedge clk) begin
    if (!rst_n) begin
      btn_sync   <= 2'b00;
      btn_stable <= 1'b0;
      btn_cnt    <= 0;
    end else begin
      btn_sync <= {btn_sync[0], ui_in[7]};
      if (btn_sync[1] == btn_stable)
        btn_cnt <= 0;
      else if (&btn_cnt)
        btn_stable <= btn_sync[1];
      else
        btn_cnt <= btn_cnt + 1'b1;
    end
  end

  // ---------------------------------------------------------------- quiz state
  wire [1:0] ans = ui_in[1:0];
  reg  [3:0] q;          // current question 0..14
  reg  [3:0] p, g;       // Purple and Green counts (Orange = 15 - p - g)
  reg        done;
  wire [1:0] colour;

  pog_rom rom (.q(q), .ans(ans), .colour(colour));

  always @(posedge clk) begin
    if (!rst_n) begin
      q    <= 4'd0;
      p    <= 4'd0;
      g    <= 4'd0;
      done <= 1'b0;
    end else if (press) begin
      if (done) begin
        q    <= 4'd0;
        p    <= 4'd0;
        g    <= 4'd0;
        done <= 1'b0;
      end else if (ans != 2'd0) begin
        p <= p + (colour == PURPLE);
        g <= g + (colour == GREEN);
        if (q == LAST_Q) done <= 1'b1;
        else q <= q + 1'b1;
      end
    end
  end

  wire [3:0] o = 4'd15 - p - g;
  wire [1:0] result = (p > g && p > o) ? PURPLE :
                      (g > p && g > o) ? GREEN : ORANGE;

  // ---------------------------------------------------------------- display
  // Restarted on every press, so the result appears (blink on) the moment Q15 is answered.
  reg [BLINK_W-1:0] blink_cnt;
  always @(posedge clk) begin
    if (!rst_n || press) blink_cnt <= 0;
    else blink_cnt <= blink_cnt + 1'b1;
  end
  wire blink_on = ~blink_cnt[BLINK_W-1];

  wire [3:0] num = q + 4'd1;                              // 1..15
  wire [3:0] digit = (num >= 4'd10) ? num - 4'd10 : num;
  reg  [6:0] seg_digit, seg_result;

  always @(*) begin
    case (digit)                                          // gfedcba
      4'd0: seg_digit = 7'b0111111;
      4'd1: seg_digit = 7'b0000110;
      4'd2: seg_digit = 7'b1011011;
      4'd3: seg_digit = 7'b1001111;
      4'd4: seg_digit = 7'b1100110;
      4'd5: seg_digit = 7'b1101101;
      4'd6: seg_digit = 7'b1111101;
      4'd7: seg_digit = 7'b0000111;
      4'd8: seg_digit = 7'b1111111;
      4'd9: seg_digit = 7'b1101111;
      default: seg_digit = 7'b0000000;
    endcase
    case (result)
      PURPLE:  seg_result = 7'b1110011;                   // P
      GREEN:   seg_result = 7'b0111101;                   // G
      default: seg_result = 7'b1011100;                   // o
    endcase
  end

  assign uo_out = done ? {1'b0, blink_on ? seg_result : 7'b0000000}
                       : {num >= 4'd10, seg_digit};

  assign uio_out = {1'b0, q, done, result};
  assign uio_oe  = 8'hFF;

  wire _unused = &{ena, uio_in, ui_in[6:2], 1'b0};

endmodule
