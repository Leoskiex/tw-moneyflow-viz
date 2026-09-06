# Flow streak × state × forward-return validation

## Verdict: `not_a_signal`（非訊號（描述子））

外資連買≥3 相對基線 lift 接近零（hit +0.002、mean +0.0016、N=100756）。目前更像描述「資金持續性」的欄位，不是可交易訊號。

**EN:** foreign_buy>=3 lift vs base is near zero (hit +0.002, mean +0.0016, N=100756). Looks like a persistence descriptor, not a tradable signal.

> Heuristic / not investment advice. ~648 交易日優於 60d，仍非 3–5 年 OOS — default skepticism.

## Plumbing
- rows=859670, stocks=2385, days=648 (2024-01-02→2026-09-04)
- primary universe rows (common∩outcomes): 664910 (all common=729781)
- close coverage: outcomes/MI_INDEX/TPEX_QUOTE merge
- material filter: |foreign_net| ≥ 0.5 千張

## Base rate (common stocks, 5d)
- P(fwd_ret_5d>0)=46.21%, mean=+0.0024, median=-0.0016, n=659430

## Key: foreign_buy_streak ≥ 3 vs base (5d)
- N=100756
- hit=46.36% (lift +0.002)
- mean=+0.0040 (lift +0.0016)

### Half-sample stability (foreign_buy≥3)
- split @ 2025-05-13
- lift_hit sign agree: False
- lift_mean sign agree: True
```json
{
  "first": {
    "n": 47495,
    "too_small": false,
    "hit_5d": 0.4908095589009369,
    "lift_hit": 0.017499688969796923,
    "mean_5d": 0.004192900266056288,
    "lift_mean": 0.003095494633126918,
    "base_hit": 0.47330986993114,
    "base_mean": 0.0010974056329293707
  },
  "second": {
    "n": 53261,
    "too_small": false,
    "hit_5d": 0.4393458628264584,
    "lift_hit": -0.01168816386585858,
    "mean_5d": 0.003897554609407081,
    "lift_mean": 0.00017487045150532633,
    "base_hit": 0.45103402669231696,
    "base_mean": 0.0037226841579017546
  }
}
```

### Material filter half-sample (|foreign_net|≥0.5)
- lift_hit agree: False, lift_mean agree: False

## By streak bucket (5d)

| filter           | dim                 | bucket   |      n |   mean_fwd_ret_5d |   median_fwd_ret_5d |   hit_rate_5d |   lift_hit_vs_base |   lift_mean_vs_base | reliable   |
|:-----------------|:--------------------|:---------|-------:|------------------:|--------------------:|--------------:|-------------------:|--------------------:|:-----------|
| all              | foreign_buy_bucket  | 0        | 343830 |       0.00127595  |         -0.00177936 |      0.458421 |        -0.00365048 |        -0.0011459   | True       |
| all              | foreign_buy_bucket  | 1-2      | 214844 |       0.00349836  |         -0.0012945  |      0.467195 |         0.00512301 |         0.00107651  | True       |
| all              | foreign_buy_bucket  | 3-5      |  74221 |       0.00434292  |         -0.00130548 |      0.467374 |         0.00530267 |         0.00192108  | True       |
| all              | foreign_buy_bucket  | 6+       |  26535 |       0.00318045  |         -0.00238663 |      0.453062 |        -0.0090098  |         0.000758601 | True       |
| all              | foreign_sell_bucket | 0        | 328128 |       0.0036284   |         -0.00144928 |      0.464779 |         0.0027072  |         0.00120655  | True       |
| all              | foreign_sell_bucket | 1-2      | 217885 |       0.00160463  |         -0.00215983 |      0.456938 |        -0.0051335  |        -0.000817218 | True       |
| all              | foreign_sell_bucket | 3-5      |  78757 |       0.00116556  |         -0.0011976  |      0.464238 |         0.00216631 |        -0.00125629  | True       |
| all              | foreign_sell_bucket | 6+       |  34660 |      -0.00100867  |          0          |      0.463791 |         0.00171932 |        -0.00343052  | True       |
| all              | trust_buy_bucket    | 0        | 579718 |       0.0022259   |         -0.0018315  |      0.457897 |        -0.00417502 |        -0.000195948 | True       |
| all              | trust_buy_bucket    | 1-2      |  43502 |       0.00573807  |          0.0010923  |      0.500851 |         0.0387787  |         0.00331622  | True       |
| all              | trust_buy_bucket    | 3-5      |  18924 |       0.00301869  |         -0.00113257 |      0.477225 |         0.0151529  |         0.000596842 | True       |
| all              | trust_buy_bucket    | 6+       |  17286 |      -5.66866e-06 |          0          |      0.487909 |         0.0258375  |        -0.00242752  | True       |
| all              | inst_buy_bucket     | 0        | 342794 |       0.00143646  |         -0.00157853 |      0.461026 |        -0.00104563 |        -0.000985388 | True       |
| all              | inst_buy_bucket     | 1-2      | 217148 |       0.00350276  |         -0.00143885 |      0.465908 |         0.00383626 |         0.00108091  | True       |
| all              | inst_buy_bucket     | 3-5      |  73703 |       0.00401237  |         -0.00189394 |      0.460646 |        -0.00142568 |         0.00159052  | True       |
| all              | inst_buy_bucket     | 6+       |  25785 |       0.00187272  |         -0.0027137  |      0.447741 |        -0.0143309  |        -0.000549126 | True       |
| material_foreign | foreign_buy_bucket  | 0        |  67379 |       0.00208692  |         -0.00171233 |      0.471245 |        -0.00630797 |        -0.00222185  | True       |
| material_foreign | foreign_buy_bucket  | 1-2      |  39669 |       0.00698307  |          0          |      0.483173 |         0.00562054 |         0.0026743   | True       |
| material_foreign | foreign_buy_bucket  | 3-5      |  15428 |       0.00736096  |          0          |      0.490148 |         0.0125951  |         0.0030522   | True       |
| material_foreign | foreign_buy_bucket  | 6+       |   7317 |       0.00383445  |          0          |      0.478611 |         0.00105873 |        -0.000474317 | True       |
| material_foreign | foreign_sell_bucket | 0        |  62414 |       0.00670736  |          0          |      0.484362 |         0.00680976 |         0.00239859  | True       |
| material_foreign | foreign_sell_bucket | 1-2      |  42009 |       0.0029377   |         -0.00247525 |      0.467257 |        -0.0102957  |        -0.00137107  | True       |
| material_foreign | foreign_sell_bucket | 3-5      |  16405 |       0.00237285  |          0          |      0.479854 |         0.00230098 |        -0.00193591  | True       |
| material_foreign | foreign_sell_bucket | 6+       |   8965 |      -0.00242297  |          0          |      0.474177 |        -0.00337536 |        -0.00673173  | True       |
| material_foreign | trust_buy_bucket    | 0        |  91637 |       0.00448079  |         -0.00184162 |      0.47112  |        -0.00643297 |         0.000172022 | True       |
| material_foreign | trust_buy_bucket    | 1-2      |  18984 |       0.00623316  |          0.00114878 |      0.501106 |         0.0235535  |         0.00192439  | True       |
| material_foreign | trust_buy_bucket    | 3-5      |   9563 |       0.00397871  |          0          |      0.481334 |         0.00378159 |        -0.000330054 | True       |
| material_foreign | trust_buy_bucket    | 6+       |   9609 |      -0.000805186 |          0          |      0.488604 |         0.0110517  |        -0.00511395  | True       |
| material_foreign | inst_buy_bucket     | 0        |  66965 |       0.00271569  |         -0.00110011 |      0.47595  |        -0.0016026  |        -0.00159307  | True       |
| material_foreign | inst_buy_bucket     | 1-2      |  41125 |       0.00632616  |         -0.00109409 |      0.478979 |         0.001426   |         0.0020174   | True       |
| material_foreign | inst_buy_bucket     | 3-5      |  14980 |       0.00713575  |          0          |      0.484246 |         0.00669294 |         0.00282699  | True       |
| material_foreign | inst_buy_bucket     | 6+       |   6723 |       0.0015371   |         -0.00130208 |      0.46988  |        -0.0076732  |        -0.00277167  | True       |
| all_common       | foreign_buy_bucket  | 0        | 381137 |       0.00134184  |          0          |      0.433052 |        -0.0445011  |        -0.00296692  | True       |
| all_common       | foreign_buy_bucket  | 1-2      | 231489 |       0.00327117  |          0          |      0.438371 |        -0.039182   |        -0.00103759  | True       |
| all_common       | foreign_buy_bucket  | 3-5      |  79178 |       0.00409706  |          0          |      0.44208  |        -0.0354728  |        -0.000211706 | True       |
| all_common       | foreign_buy_bucket  | 6+       |  27887 |       0.00302168  |          0          |      0.435794 |        -0.0417583  |        -0.00128709  | True       |
| all_common       | foreign_sell_bucket | 0        | 363828 |       0.00350017  |          0          |      0.439603 |        -0.0379494  |        -0.000808597 | True       |
| all_common       | foreign_sell_bucket | 1-2      | 235094 |       0.00148227  |          0          |      0.427982 |        -0.0495707  |        -0.00282649  | True       |
| all_common       | foreign_sell_bucket | 3-5      |  84256 |       0.00108767  |          0          |      0.437441 |        -0.0401121  |        -0.0032211   | True       |
| all_common       | foreign_sell_bucket | 6+       |  36513 |      -0.000992681 |          0          |      0.445677 |        -0.0318758  |        -0.00530145  | True       |
| all_common       | trust_buy_bucket    | 0        | 638140 |       0.00214651  |          0          |      0.429671 |        -0.0478821  |        -0.00216226  | True       |
| all_common       | trust_buy_bucket    | 1-2      |  44741 |       0.00559168  |          0          |      0.490624 |         0.0130711  |         0.00128292  | True       |
| all_common       | trust_buy_bucket    | 3-5      |  19341 |       0.00296821  |          0          |      0.470141 |        -0.00741157 |        -0.00134056  | True       |
| all_common       | trust_buy_bucket    | 6+       |  17469 |      -1.61981e-06 |          0          |      0.483828 |         0.00627578 |        -0.00431038  | True       |
| all_common       | inst_buy_bucket     | 0        | 373621 |       0.00137667  |          0          |      0.433129 |        -0.044424   |        -0.0029321   | True       |
| all_common       | inst_buy_bucket     | 1-2      | 237612 |       0.00337996  |          0          |      0.43949  |        -0.0380631  |        -0.000928806 | True       |
| all_common       | inst_buy_bucket     | 3-5      |  80143 |       0.00379937  |          0          |      0.43788  |        -0.0396729  |        -0.000509394 | True       |
| all_common       | inst_buy_bucket     | 6+       |  28315 |       0.00195535  |          0          |      0.435776 |        -0.0417766  |        -0.00235342  | True       |

## Regime × foreign_buy_bucket (n≥30)

| filter           | regime         | bucket   |     n |   mean_fwd_ret_5d |   hit_rate_5d |   lift_hit_vs_base |   lift_mean_vs_base |
|:-----------------|:---------------|:---------|------:|------------------:|--------------:|-------------------:|--------------------:|
| all              | hot_money      | 0        |   381 |       0.0247455   |      0.653543 |        0.191472    |         0.0223237   |
| all              | hot_money      | 1-2      |   504 |       0.0164172   |      0.615079 |        0.153008    |         0.0139953   |
| all              | hot_money      | 3-5      |   154 |       0.00846155  |      0.538961 |        0.0768892   |         0.0060397   |
| all              | hot_money      | 6+       |    34 |      -0.00571811  |      0.411765 |       -0.0503071   |        -0.00813996  |
| all              | inst_push      | 0        | 14567 |       0.00718328  |      0.464269 |        0.00219676  |         0.00476143  |
| all              | inst_push      | 1-2      | 12162 |       0.00836467  |      0.460122 |       -0.0019501   |         0.00594282  |
| all              | inst_push      | 3-5      |  4755 |       0.00786372  |      0.454048 |       -0.00802342  |         0.00544188  |
| all              | inst_push      | 6+       |  1604 |       0.00189689  |      0.382793 |       -0.0792788   |        -0.000524963 |
| all              | leverage_relay | 0        |  6763 |      -0.0026603   |      0.430726 |       -0.0313458   |        -0.00508215  |
| all              | leverage_relay | 1-2      |  5480 |       0.00468148  |      0.441058 |       -0.0210134   |         0.00225963  |
| all              | leverage_relay | 3-5      |  1982 |       0.00171242  |      0.431887 |       -0.0301848   |        -0.000709426 |
| all              | leverage_relay | 6+       |   762 |      -0.0034872   |      0.401575 |       -0.060497    |        -0.00590905  |
| all              | mixed          | 0        |  2657 |       0.00077766  |      0.38201  |       -0.080062    |        -0.00164419  |
| all              | mixed          | 1-2      |  2248 |       0.00861553  |      0.437722 |       -0.0243494   |         0.00619369  |
| all              | mixed          | 3-5      |  1024 |       0.00969965  |      0.442383 |       -0.019689    |         0.0072778   |
| all              | mixed          | 6+       |   462 |      -0.000185839 |      0.363636 |       -0.0984354   |        -0.00260769  |
| all              | regulatory     | 0        | 13521 |      -0.000393363 |      0.444198 |       -0.0178739   |        -0.00281521  |
| all              | regulatory     | 1-2      |  8515 |       0.00367393  |      0.470816 |        0.00874442  |         0.00125208  |
| all              | regulatory     | 3-5      |  3456 |       0.00110195  |      0.422164 |       -0.0399074   |        -0.0013199   |
| all              | regulatory     | 6+       |  1286 |      -0.00220287  |      0.381804 |       -0.0802677   |        -0.00462472  |
| all              | risk_off       | 0        | 22431 |       0.00761945  |      0.493558 |        0.0314862   |         0.0051976   |
| all              | risk_off       | 1-2      | 11384 |       0.00925502  |      0.492094 |        0.0300224   |         0.00683317  |
| all              | risk_off       | 3-5      |  4231 |       0.00997076  |      0.4909   |        0.0288287   |         0.00754891  |
| all              | risk_off       | 6+       |  1442 |       0.0117471   |      0.483356 |        0.0212847   |         0.00932529  |
| material_foreign | hot_money      | 0        |    85 |       0.0315853   |      0.729412 |        0.251859    |         0.0272766   |
| material_foreign | hot_money      | 1-2      |    68 |       0.0164418   |      0.529412 |        0.051859    |         0.012133    |
| material_foreign | hot_money      | 3-5      |    41 |       0.00705916  |      0.463415 |       -0.0141381   |         0.00275039  |
| material_foreign | inst_push      | 0        |  3396 |       0.0120834   |      0.5      |        0.0224473   |         0.00777466  |
| material_foreign | inst_push      | 1-2      |  2794 |       0.0191787   |      0.52398  |        0.0464272   |         0.01487     |
| material_foreign | inst_push      | 3-5      |  1164 |       0.01136     |      0.492268 |        0.0147153   |         0.00705127  |
| material_foreign | inst_push      | 6+       |   459 |       0.00132103  |      0.440087 |       -0.0374656   |        -0.00298774  |
| material_foreign | leverage_relay | 0        |  1583 |      -0.00931041  |      0.423247 |       -0.0543057   |        -0.0136192   |
| material_foreign | leverage_relay | 1-2      |  1104 |       0.0102914   |      0.481884 |        0.00433134  |         0.00598262  |
| material_foreign | leverage_relay | 3-5      |   416 |       0.00716131  |      0.478365 |        0.000812666 |         0.00285254  |
| material_foreign | leverage_relay | 6+       |   185 |      -0.00454446  |      0.410811 |       -0.0667419   |        -0.00885323  |
| material_foreign | mixed          | 0        |   619 |       0.00128391  |      0.410339 |       -0.0672135   |        -0.00302486  |
| material_foreign | mixed          | 1-2      |   467 |       0.0239681   |      0.524625 |        0.0470725   |         0.0196593   |
| material_foreign | mixed          | 3-5      |   200 |       0.0118006   |      0.46     |       -0.0175527   |         0.00749187  |
| material_foreign | mixed          | 6+       |   116 |      -0.00449938  |      0.413793 |       -0.0637596   |        -0.00880814  |
| material_foreign | regulatory     | 0        |  3216 |       0.00273033  |      0.470149 |       -0.00740346  |        -0.00157844  |
| material_foreign | regulatory     | 1-2      |  1888 |       0.0019936   |      0.460805 |       -0.0167476   |        -0.00231516  |
| material_foreign | regulatory     | 3-5      |   843 |       0.00865907  |      0.440095 |       -0.0374578   |         0.0043503   |
| material_foreign | regulatory     | 6+       |   390 |       0.00443851  |      0.446154 |       -0.0313989   |         0.000129743 |
| material_foreign | risk_off       | 0        |  4939 |       0.011551    |      0.505163 |        0.0276103   |         0.00724219  |
| material_foreign | risk_off       | 1-2      |  2284 |       0.0171937   |      0.518827 |        0.0412739   |         0.012885    |
| material_foreign | risk_off       | 3-5      |   964 |       0.0127455   |      0.525934 |        0.0483809   |         0.00843671  |
| material_foreign | risk_off       | 6+       |   458 |       0.014416    |      0.5131   |        0.0355477   |         0.0101072   |

## Caveats
- 樣本約 648 個交易日（優於早期 ~60d，但仍遠短於 3–5 年 OOS）；半衰期與 regime 切換覆蓋仍有限。
- Heuristic / not investment advice. 不構成投資建議。
- Streaks derived from official T86 nets, not Goodinfo.

## How to read
- Streaks = consecutive days of same-sign net from official T86 (curated post-pass).
- Buckets: 0 / 1-2 / 3-5 / 6+.
- Forward returns by stock on trading-day shifts (not calendar).
- Verdict enum: `not_a_signal` | `useful_as_filter` | `useful_as_falsifier` | `edge_candidate`.
