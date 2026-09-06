# Flow streak × state × forward-return validation

## Verdict: `useful_as_falsifier`（有用作為否證器／濾鏡）

外資連買≥3 並未穩定優於基線（5d hit lift=-0.034、mean lift=-0.0013、N=10109）；長連買(6+)亦未顯示正優勢。適合用來否證「連買=必漲」敘事，或當 persistence 清晰度工具，而非獨立買訊。半樣本 lift 符號一致=True/False（hit/mean）。

**EN:** foreign_buy>=3 does not reliably beat base (5d hit lift=-0.034, mean lift=-0.0013, N=10109); long streaks (6+) also lack positive edge. Useful to falsify 'streak=must-rise' narratives / as a clarity filter, not a standalone buy signal. Half-sample sign agree hit/mean=True/False.

> Heuristic / not investment advice. 60d sample — default skepticism.

## Plumbing
- rows=134021, stocks=2360, days=60 (2026-06-11→2026-09-04)
- primary universe rows (common∩outcomes): 64382 (all common=113160)
- close coverage: outcomes/MI_INDEX/TPEX_QUOTE merge
- material filter: |foreign_net| ≥ 0.5 千張

## Base rate (common stocks, 5d)
- P(fwd_ret_5d>0)=44.30%, mean=-0.0005, median=-0.0035, n=58954

## Key: foreign_buy_streak ≥ 3 vs base (5d)
- N=10109
- hit=40.93% (lift -0.034)
- mean=-0.0017 (lift -0.0013)

### Half-sample stability (foreign_buy≥3)
- split @ 2026-07-27
- lift_hit sign agree: True
- lift_mean sign agree: False
```json
{
  "first": {
    "n": 5176,
    "too_small": false,
    "hit_5d": 0.3695904173106646,
    "lift_hit": -0.007230774742315538,
    "mean_5d": -0.011910216846399587,
    "lift_mean": 0.0013688538258762248,
    "base_hit": 0.37682119205298015,
    "base_mean": -0.013279070672275812
  },
  "second": {
    "n": 4933,
    "too_small": false,
    "hit_5d": 0.4510439894587472,
    "lift_hit": -0.07732315128890183,
    "mean_5d": 0.008928051021864534,
    "lift_mean": -0.007117826452793387,
    "base_hit": 0.528367140747649,
    "base_mean": 0.01604587747465792
  }
}
```

### Material filter half-sample (|foreign_net|≥0.5)
- lift_hit agree: False, lift_mean agree: False

## By streak bucket (5d)

| filter           | dim                 | bucket   |     n |   mean_fwd_ret_5d |   median_fwd_ret_5d |   hit_rate_5d |   lift_hit_vs_base |   lift_mean_vs_base | reliable   |
|:-----------------|:--------------------|:---------|------:|------------------:|--------------------:|--------------:|-------------------:|--------------------:|:-----------|
| all              | foreign_buy_bucket  | 0        | 28908 |      -0.00150239  |         -0.00295639 |      0.451743 |        0.00877097  |        -0.00102394  | True       |
| all              | foreign_buy_bucket  | 1-2      | 19937 |       0.00164669  |         -0.00305344 |      0.447309 |        0.00433654  |         0.00212513  | True       |
| all              | foreign_buy_bucket  | 3-5      |  7820 |      -0.000406331 |         -0.00495356 |      0.41509  |       -0.027883    |         7.21116e-05 | True       |
| all              | foreign_buy_bucket  | 6+       |  2289 |      -0.00630306  |         -0.00638978 |      0.38969  |       -0.0532827   |        -0.00582461  | True       |
| all              | foreign_sell_bucket | 0        | 30941 |       0.000425703 |         -0.00388098 |      0.433599 |       -0.00937306  |         0.000904146 | True       |
| all              | foreign_sell_bucket | 1-2      | 19336 |      -0.000402216 |         -0.00301432 |      0.451179 |        0.00820666  |         7.62267e-05 | True       |
| all              | foreign_sell_bucket | 3-5      |  6525 |      -0.00324166  |         -0.00162338 |      0.467126 |        0.0241539   |        -0.00276322  | True       |
| all              | foreign_sell_bucket | 6+       |  2152 |      -0.00578472  |         -0.00471159 |      0.430762 |       -0.0122104   |        -0.00530628  | True       |
| all              | trust_buy_bucket    | 0        | 51577 |      -0.000942485 |         -0.0037037  |      0.436086 |       -0.00688663  |        -0.000464042 | True       |
| all              | trust_buy_bucket    | 1-2      |  4159 |       0.00956104  |          0.00395257 |      0.520558 |        0.0775853   |         0.0100395   | True       |
| all              | trust_buy_bucket    | 3-5      |  1725 |      -0.00393665  |         -0.00460829 |      0.46087  |        0.0178971   |        -0.0034582   | True       |
| all              | trust_buy_bucket    | 6+       |  1493 |      -0.00841878  |         -0.00680272 |      0.444072 |        0.00109985  |        -0.00794034  | True       |
| all              | inst_buy_bucket     | 0        | 28846 |      -0.00149665  |         -0.00291545 |      0.451848 |        0.00887526  |        -0.00101821  | True       |
| all              | inst_buy_bucket     | 1-2      | 20121 |       0.00173533  |         -0.0030581  |      0.447691 |        0.00471898  |         0.00221378  | True       |
| all              | inst_buy_bucket     | 3-5      |  7764 |      -0.000645418 |         -0.00504096 |      0.412416 |       -0.0305562   |        -0.000166975 | True       |
| all              | inst_buy_bucket     | 6+       |  2223 |      -0.00672036  |         -0.00637959 |      0.391813 |       -0.0511596   |        -0.00624192  | True       |
| material_foreign | foreign_buy_bucket  | 0        |  6404 |      -0.00285841  |         -0.00455077 |      0.458463 |        0.000595049 |        -0.00251758  | True       |
| material_foreign | foreign_buy_bucket  | 1-2      |  4133 |       0.00238916  |         -0.00373134 |      0.465279 |        0.00741105  |         0.00272999  | True       |
| material_foreign | foreign_buy_bucket  | 3-5      |  1790 |       0.00331696  |         -0.00395895 |      0.450279 |       -0.00758908  |         0.00365779  | True       |
| material_foreign | foreign_buy_bucket  | 6+       |   668 |      -0.00289758  |         -0.00742137 |      0.426647 |       -0.0312217   |        -0.00255675  | True       |
| material_foreign | foreign_sell_bucket | 0        |  6591 |       0.00210532  |         -0.00435414 |      0.45729  |       -0.000578167 |         0.00244615  | True       |
| material_foreign | foreign_sell_bucket | 1-2      |  4085 |      -0.00038293  |         -0.00312012 |      0.468054 |        0.0101854   |        -4.21011e-05 | True       |
| material_foreign | foreign_sell_bucket | 3-5      |  1642 |      -0.00345217  |         -0.00347232 |      0.470158 |        0.0122899   |        -0.00311134  | True       |
| material_foreign | foreign_sell_bucket | 6+       |   677 |      -0.0163553   |         -0.0159011  |      0.37223  |       -0.085638    |        -0.0160144   | True       |
| material_foreign | trust_buy_bucket    | 0        |  8960 |      -0.00129822  |         -0.00582106 |      0.444308 |       -0.0135604   |        -0.000957388 | True       |
| material_foreign | trust_buy_bucket    | 1-2      |  2072 |       0.00970885  |          0.00384255 |      0.519788 |        0.0619192   |         0.0100497   | True       |
| material_foreign | trust_buy_bucket    | 3-5      |  1008 |      -0.00195314  |         -0.00339936 |      0.470238 |        0.0123697   |        -0.00161231  | True       |
| material_foreign | trust_buy_bucket    | 6+       |   955 |      -0.0114608   |         -0.00668151 |      0.437696 |       -0.0201721   |        -0.0111199   | True       |
| material_foreign | inst_buy_bucket     | 0        |  6262 |      -0.00262513  |         -0.0045045  |      0.45816  |        0.000291921 |        -0.0022843   | True       |
| material_foreign | inst_buy_bucket     | 1-2      |  4268 |       0.00167875  |         -0.00445437 |      0.461106 |        0.00323749  |         0.00201958  | True       |
| material_foreign | inst_buy_bucket     | 3-5      |  1769 |       0.00367514  |         -0.00413223 |      0.449406 |       -0.00846197  |         0.00401596  | True       |
| material_foreign | inst_buy_bucket     | 6+       |   696 |      -0.00238035  |         -0.00458754 |      0.456897 |       -0.000971859 |        -0.00203952  | True       |
| all_common       | foreign_buy_bucket  | 0        | 53050 |      -0.000789793 |          0          |      0.254194 |       -0.203674    |        -0.000448964 | True       |
| all_common       | foreign_buy_bucket  | 1-2      | 34471 |       0.000927609 |          0          |      0.261234 |       -0.196634    |         0.00126844  | True       |
| all_common       | foreign_buy_bucket  | 3-5      | 12249 |      -0.000269339 |          0          |      0.268675 |       -0.189193    |         7.14901e-05 | True       |
| all_common       | foreign_buy_bucket  | 6+       |  3439 |      -0.00443797  |          0          |      0.264321 |       -0.193547    |        -0.00409714  | True       |
| all_common       | foreign_sell_bucket | 0        | 53859 |       0.00025115  |          0          |      0.257561 |       -0.200307    |         0.000591979 | True       |
| all_common       | foreign_sell_bucket | 1-2      | 34349 |      -0.000246618 |          0          |      0.256339 |       -0.201529    |         9.42115e-05 | True       |
| all_common       | foreign_sell_bucket | 3-5      | 11412 |      -0.00185973  |          0          |      0.269541 |       -0.188328    |        -0.00151891  | True       |
| all_common       | foreign_sell_bucket | 6+       |  3589 |      -0.00343174  |          0          |      0.261076 |       -0.196793    |        -0.00309091  | True       |
| all_common       | trust_buy_bucket    | 0        | 94367 |      -0.000518192 |          0          |      0.244418 |       -0.21345     |        -0.000177363 | True       |
| all_common       | trust_buy_bucket    | 1-2      |  5139 |       0.00774002  |          0          |      0.421677 |       -0.036191    |         0.00808085  | True       |
| all_common       | trust_buy_bucket    | 3-5      |  2056 |      -0.00330288  |          0          |      0.386673 |       -0.0711953   |        -0.00296205  | True       |
| all_common       | trust_buy_bucket    | 6+       |  1647 |      -0.0076316   |          0          |      0.40255  |       -0.0553183   |        -0.00729077  | True       |
| all_common       | inst_buy_bucket     | 0        | 52617 |      -0.000781592 |          0          |      0.252295 |       -0.205574    |        -0.000440763 | True       |
| all_common       | inst_buy_bucket     | 1-2      | 35018 |       0.000964654 |          0          |      0.263207 |       -0.194661    |         0.00130548  | True       |
| all_common       | inst_buy_bucket     | 3-5      | 12198 |      -0.000398869 |          0          |      0.270372 |       -0.187496    |        -5.80401e-05 | True       |
| all_common       | inst_buy_bucket     | 6+       |  3376 |      -0.00482051  |          0          |      0.266588 |       -0.191281    |        -0.00447968  | True       |

## Regime × foreign_buy_bucket (n≥30)

| filter           | regime         | bucket   |     n |   mean_fwd_ret_5d |   hit_rate_5d |   lift_hit_vs_base |   lift_mean_vs_base |
|:-----------------|:---------------|:---------|------:|------------------:|--------------:|-------------------:|--------------------:|
| all              | hot_money      | 0        |   381 |       0.0247455   |      0.653543 |        0.210571    |         0.025224    |
| all              | hot_money      | 1-2      |   504 |       0.0164172   |      0.615079 |        0.172107    |         0.0168956   |
| all              | hot_money      | 3-5      |   154 |       0.00846155  |      0.538961 |        0.0959886   |         0.00893999  |
| all              | hot_money      | 6+       |    33 |      -0.00589139  |      0.424242 |       -0.0187301   |        -0.00541294  |
| all              | inst_push      | 0        |  6301 |      -0.00311111  |      0.405491 |       -0.0374813   |        -0.00263267  |
| all              | inst_push      | 1-2      |  5076 |       0.000101478 |      0.388101 |       -0.0548716   |         0.000579921 |
| all              | inst_push      | 3-5      |  1980 |      -0.00385842  |      0.355556 |       -0.0874169   |        -0.00337997  |
| all              | inst_push      | 6+       |   545 |      -0.0141063   |      0.321101 |       -0.121872    |        -0.0136279   |
| all              | leverage_relay | 0        |  4296 |      -0.00628981  |      0.440177 |       -0.00279558  |        -0.00581137  |
| all              | leverage_relay | 1-2      |  3604 |       0.00212257  |      0.429523 |       -0.0134497   |         0.00260101  |
| all              | leverage_relay | 3-5      |  1344 |      -0.00172524  |      0.419643 |       -0.0233296   |        -0.0012468   |
| all              | leverage_relay | 6+       |   415 |      -0.00796469  |      0.409639 |       -0.0333339   |        -0.00748625  |
| all              | mixed          | 0        |   475 |      -0.00827234  |      0.383158 |       -0.0598146   |        -0.0077939   |
| all              | mixed          | 1-2      |   464 |      -0.00363507  |      0.452586 |        0.00961372  |        -0.00315663  |
| all              | mixed          | 3-5      |    97 |      -0.00995082  |      0.360825 |       -0.0821477   |        -0.00947237  |
| all              | mixed          | 6+       |    39 |      -0.00339714  |      0.384615 |       -0.0583571   |        -0.0029187   |
| all              | regulatory     | 0        |  7411 |      -0.00384724  |      0.458643 |        0.0156701   |        -0.0033688   |
| all              | regulatory     | 1-2      |  5098 |       0.00255355  |      0.483719 |        0.0407466   |         0.00303199  |
| all              | regulatory     | 3-5      |  1906 |      -0.00194303  |      0.412382 |       -0.0305905   |        -0.00146459  |
| all              | regulatory     | 6+       |   604 |      -0.0108208   |      0.362583 |       -0.0803897   |        -0.0103424   |
| all              | risk_off       | 0        | 10044 |       0.00260916  |      0.476205 |        0.0332322   |         0.0030876   |
| all              | risk_off       | 1-2      |  5191 |       0.000974697 |      0.465036 |        0.0220632   |         0.00145314  |
| all              | risk_off       | 3-5      |  2339 |       0.00433794  |      0.459171 |        0.0161981   |         0.00481638  |
| all              | risk_off       | 6+       |   653 |       0.00525003  |      0.457887 |        0.0149142   |         0.00572847  |
| material_foreign | hot_money      | 0        |    85 |       0.0315853   |      0.729412 |        0.271543    |         0.0319262   |
| material_foreign | hot_money      | 1-2      |    68 |       0.0164418   |      0.529412 |        0.0715434   |         0.0167826   |
| material_foreign | hot_money      | 3-5      |    41 |       0.00705916  |      0.463415 |        0.00554622  |         0.00739999  |
| material_foreign | inst_push      | 0        |  1385 |       0.00294632  |      0.47148  |        0.0136117   |         0.00328715  |
| material_foreign | inst_push      | 1-2      |  1175 |       0.00576255  |      0.458723 |        0.000854993 |         0.00610338  |
| material_foreign | inst_push      | 3-5      |   470 |      -0.00179328  |      0.421277 |       -0.0365918   |        -0.00145245  |
| material_foreign | inst_push      | 6+       |   154 |      -0.0175429   |      0.363636 |       -0.094232    |        -0.017202    |
| material_foreign | leverage_relay | 0        |   980 |      -0.0160797   |      0.417347 |       -0.0405215   |        -0.0157389   |
| material_foreign | leverage_relay | 1-2      |   747 |       0.00736894  |      0.472557 |        0.0146885   |         0.00770977  |
| material_foreign | leverage_relay | 3-5      |   274 |       0.00527744  |      0.5      |        0.0421316   |         0.00561827  |
| material_foreign | leverage_relay | 6+       |    95 |      -0.00987102  |      0.389474 |       -0.0683947   |        -0.0095302   |
| material_foreign | mixed          | 0        |   107 |      -0.0137077   |      0.364486 |       -0.0933824   |        -0.0133669   |
| material_foreign | mixed          | 1-2      |    77 |      -0.00223173  |      0.506494 |        0.0486251   |        -0.0018909   |
| material_foreign | regulatory     | 0        |  1603 |      -0.00457792  |      0.473487 |        0.0156188   |        -0.00423709  |
| material_foreign | regulatory     | 1-2      |  1046 |      -0.00349891  |      0.463671 |        0.00580272  |        -0.00315808  |
| material_foreign | regulatory     | 3-5      |   465 |       0.00691597  |      0.434409 |       -0.0234598   |         0.0072568   |
| material_foreign | regulatory     | 6+       |   187 |      -0.00479767  |      0.449198 |       -0.00867055  |        -0.00445684  |
| material_foreign | risk_off       | 0        |  2244 |      -0.000226114 |      0.451872 |       -0.00599675  |         0.000114716 |
| material_foreign | risk_off       | 1-2      |  1020 |       0.000306329 |      0.461765 |        0.00389629  |         0.000647158 |
| material_foreign | risk_off       | 3-5      |   518 |       0.00421254  |      0.469112 |        0.0112436   |         0.00455337  |
| material_foreign | risk_off       | 6+       |   210 |       0.0130185   |      0.480952 |        0.023084    |         0.0133593   |

## Caveats
- 樣本僅約 60 個交易日（短窗），半衰期與 regime 切換未充分覆蓋。
- Heuristic / not investment advice. 不構成投資建議。
- Streaks derived from official T86 nets, not Goodinfo.

## How to read
- Streaks = consecutive days of same-sign net from official T86 (curated post-pass).
- Buckets: 0 / 1-2 / 3-5 / 6+.
- Forward returns by stock on trading-day shifts (not calendar).
- Verdict enum: `not_a_signal` | `useful_as_filter` | `useful_as_falsifier` | `edge_candidate`.
