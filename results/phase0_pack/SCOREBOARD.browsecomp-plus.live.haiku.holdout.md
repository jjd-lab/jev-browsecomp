# Scoreboard

Mode `live`. Suite `browsecomp-plus`. Arm C calls typed decide on the top 3 documents. Arm C uses the scored chat decide: a route with p(act) and one support probability per id, decoded like Jev `both`. Gold held out: each pool drops its gold docids, so gold is abstain and exact_id counts Abstain only.

`latency_ms` is the mean per question on this run. A later run can change it.
`cost_usd` is the mean per question. Anthropic model `claude-haiku-4-5` is priced at 1.00 dollars per million input tokens and 5.00 dollars per million output tokens. Jev uses 0.042 dollars per million input tokens.

| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 0.247 | 1.000 | 0.000 | 0.247 | 0.008267 | 1524.4 |

Live C exact_id_acc is 0.247 and cite_ok is 1.000. Mean cost_usd is 0.008267. exact_id is set equality with the gold docids.

The pack has 150 BrowseComp-Plus queries from Tevatron/browsecomp-plus revision 144cff8e35b5eaef7e526346aa60774a9deb941f. Pinned shard `data/test-00000-of-00006.parquet` sha256 4ff9e93054eaee61b8d079a89b7ec4d02f16c9d05fa6e2fef7185b0786427a3a. Shards in the draw: test-00000-of-00006.parquet, test-00001-of-00006.parquet, test-00002-of-00006.parquet, test-00003-of-00006.parquet. Eligible pool 165. See fixtures/browsecomp_plus/LICENSE.txt and fixtures/browsecomp_plus/PACK.json.
exact_id is set equality on the gold docids. Evidence docids are the documents labeled as needed to answer. The flat pool adds the first 4 usable negative docids in release order.
Arm C ranks that pool with Okapi BM25 (k1=1.2, b=0.75) on the full document text and calls decide on the top 3 ids. IDF and average length are taken inside that pool. Code copies the indexed span. The span is a verbatim slice of the document with no double quote.
Answer accuracy is not in this table.
Arms A and B are not run. Arm B remains the tree walk for a later recurse cut. This pack does not build that walk.
Live prompts send at most 12000 characters from the start of each top-k document.

## Per question

| id | gold | C |
| --- | --- | --- |
| 6 | abstain | review |
| 7 | abstain | review |
| 10 | abstain | abstain |
| 12 | abstain | review |
| 20 | abstain | act:23118 |
| 30 | abstain | abstain |
| 36 | abstain | act:24652 |
| 37 | abstain | abstain |
| 50 | abstain | review |
| 61 | abstain | act:11492 |
| 67 | abstain | review |
| 69 | abstain | act:98058 |
| 70 | abstain | act:56616 |
| 74 | abstain | review |
| 209 | abstain | review |
| 211 | abstain | act:77650 |
| 219 | abstain | review |
| 228 | abstain | review |
| 234 | abstain | act:5120 |
| 251 | abstain | abstain |
| 255 | abstain | act:52926 |
| 261 | abstain | act:39924 |
| 262 | abstain | review |
| 265 | abstain | abstain |
| 266 | abstain | abstain |
| 282 | abstain | review |
| 287 | abstain | act:54210 |
| 309 | abstain | act:87041 |
| 315 | abstain | abstain |
| 319 | abstain | review |
| 331 | abstain | act:40697 |
| 333 | abstain | act:59751 |
| 337 | abstain | review |
| 342 | abstain | act:56512 |
| 349 | abstain | review |
| 353 | abstain | act:67775 |
| 354 | abstain | act:40658 |
| 356 | abstain | abstain |
| 468 | abstain | abstain |
| 469 | abstain | act:7293 |
| 470 | abstain | review |
| 471 | abstain | review |
| 480 | abstain | act:86730 |
| 484 | abstain | review |
| 495 | abstain | abstain |
| 497 | abstain | review |
| 502 | abstain | abstain |
| 524 | abstain | act:72501 |
| 527 | abstain | review |
| 552 | abstain | abstain |
| 553 | abstain | review |
| 556 | abstain | act:84412 |
| 561 | abstain | abstain |
| 569 | abstain | act:25380 |
| 575 | abstain | review |
| 579 | abstain | review |
| 581 | abstain | review |
| 582 | abstain | review |
| 583 | abstain | review |
| 587 | abstain | review |
| 588 | abstain | abstain |
| 592 | abstain | review |
| 593 | abstain | act:54532 |
| 594 | abstain | review |
| 596 | abstain | review |
| 605 | abstain | act:57487 |
| 607 | abstain | act:95214 |
| 611 | abstain | abstain |
| 614 | abstain | review |
| 618 | abstain | act:51187 |
| 624 | abstain | review |
| 627 | abstain | review |
| 632 | abstain | act:22191 |
| 635 | abstain | act:94439 |
| 636 | abstain | act:19992 |
| 643 | abstain | act:83797 |
| 645 | abstain | review |
| 650 | abstain | review |
| 653 | abstain | abstain |
| 655 | abstain | abstain |
| 662 | abstain | review |
| 772 | abstain | review |
| 775 | abstain | act:94091 |
| 787 | abstain | act:82388 |
| 790 | abstain | review |
| 793 | abstain | review |
| 794 | abstain | abstain |
| 806 | abstain | abstain |
| 819 | abstain | review |
| 821 | abstain | abstain |
| 826 | abstain | act:55054 |
| 827 | abstain | abstain |
| 830 | abstain | act:54126 |
| 833 | abstain | act:40824 |
| 838 | abstain | act:51499 |
| 843 | abstain | review |
| 851 | abstain | review |
| 853 | abstain | act:77487 |
| 854 | abstain | abstain |
| 864 | abstain | review |
| 870 | abstain | review |
| 873 | abstain | abstain |
| 876 | abstain | review |
| 884 | abstain | review |
| 897 | abstain | abstain |
| 898 | abstain | abstain |
| 909 | abstain | act:41249 |
| 912 | abstain | abstain |
| 926 | abstain | abstain |
| 928 | abstain | act:100192 |
| 930 | abstain | review |
| 944 | abstain | review |
| 948 | abstain | review |
| 952 | abstain | act:51325 |
| 960 | abstain | review |
| 962 | abstain | abstain |
| 963 | abstain | abstain |
| 968 | abstain | act:97882 |
| 971 | abstain | act:9900 |
| 981 | abstain | abstain |
| 985 | abstain | review |
| 996 | abstain | act:94709 |
| 1000 | abstain | act:44464 |
| 1008 | abstain | act:3774 |
| 1020 | abstain | abstain |
| 1022 | abstain | review |
| 1028 | abstain | act:10752 |
| 1030 | abstain | review |
| 1032 | abstain | abstain |
| 1033 | abstain | abstain |
| 1036 | abstain | review |
| 1038 | abstain | review |
| 1041 | abstain | review |
| 1042 | abstain | act:79586 |
| 1044 | abstain | review |
| 1053 | abstain | abstain |
| 1057 | abstain | review |
| 1060 | abstain | act:61809 |
| 1063 | abstain | review |
| 1072 | abstain | abstain |
| 1073 | abstain | review |
| 1185 | abstain | abstain |
| 1206 | abstain | abstain |
| 1208 | abstain | act:40083 |
| 1230 | abstain | act:36417 |
| 1238 | abstain | review |
| 1243 | abstain | act:78137 |
| 1249 | abstain | act:42464 |
| 1257 | abstain | review |
| 1264 | abstain | review |
