# Scoreboard

Mode `live`. Suite `browsecomp-plus`. Arm C calls typed decide on the top 8 documents. Jev decode is `both`. Gold held out: each pool drops its gold docids, so gold is abstain and exact_id counts Abstain only.

`latency_ms` is the mean per question on this run. A later run can change it.
`cost_usd` is the mean per question. Jev uses 0.042 dollars per million input tokens.

| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 0.100 | 1.000 | 0.000 | 0.100 | 0.000550 | 626.2 |

Live C exact_id_acc is 0.100 and cite_ok is 1.000. Mean cost_usd is 0.000550. exact_id is set equality with the gold docids.

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
| 10 | abstain | act:17299 |
| 12 | abstain | review |
| 20 | abstain | review |
| 30 | abstain | abstain |
| 36 | abstain | review |
| 37 | abstain | abstain |
| 50 | abstain | review |
| 61 | abstain | act:87038 |
| 67 | abstain | review |
| 69 | abstain | act:86999 |
| 70 | abstain | review |
| 74 | abstain | review |
| 209 | abstain | review |
| 211 | abstain | review |
| 219 | abstain | review |
| 228 | abstain | review |
| 234 | abstain | review |
| 251 | abstain | review |
| 255 | abstain | review |
| 261 | abstain | review |
| 262 | abstain | review |
| 265 | abstain | review |
| 266 | abstain | abstain |
| 282 | abstain | review |
| 287 | abstain | review |
| 309 | abstain | review |
| 315 | abstain | review |
| 319 | abstain | abstain |
| 331 | abstain | review |
| 333 | abstain | act:59751 |
| 337 | abstain | review |
| 342 | abstain | act:56512 |
| 349 | abstain | review |
| 353 | abstain | review |
| 354 | abstain | review |
| 356 | abstain | review |
| 468 | abstain | review |
| 469 | abstain | review |
| 470 | abstain | review |
| 471 | abstain | review |
| 480 | abstain | act:86730 |
| 484 | abstain | review |
| 495 | abstain | review |
| 497 | abstain | review |
| 502 | abstain | abstain |
| 524 | abstain | review |
| 527 | abstain | review |
| 552 | abstain | review |
| 553 | abstain | review |
| 556 | abstain | abstain |
| 561 | abstain | abstain |
| 569 | abstain | act:53224 |
| 575 | abstain | review |
| 579 | abstain | review |
| 581 | abstain | review |
| 582 | abstain | review |
| 583 | abstain | review |
| 587 | abstain | review |
| 588 | abstain | review |
| 592 | abstain | act:7970 |
| 593 | abstain | review |
| 594 | abstain | review |
| 596 | abstain | review |
| 605 | abstain | review |
| 607 | abstain | act:95214 |
| 611 | abstain | review |
| 614 | abstain | review |
| 618 | abstain | review |
| 624 | abstain | act:74144 |
| 627 | abstain | review |
| 632 | abstain | act:52135 |
| 635 | abstain | review |
| 636 | abstain | review |
| 643 | abstain | abstain |
| 645 | abstain | review |
| 650 | abstain | review |
| 653 | abstain | review |
| 655 | abstain | review |
| 662 | abstain | act:1548 |
| 772 | abstain | abstain |
| 775 | abstain | review |
| 787 | abstain | review |
| 790 | abstain | review |
| 793 | abstain | review |
| 794 | abstain | review |
| 806 | abstain | review |
| 819 | abstain | review |
| 821 | abstain | abstain |
| 826 | abstain | act:55054 |
| 827 | abstain | review |
| 830 | abstain | act:54126 |
| 833 | abstain | review |
| 838 | abstain | act:51499 |
| 843 | abstain | review |
| 851 | abstain | review |
| 853 | abstain | review |
| 854 | abstain | review |
| 864 | abstain | review |
| 870 | abstain | review |
| 873 | abstain | abstain |
| 876 | abstain | review |
| 884 | abstain | review |
| 897 | abstain | abstain |
| 898 | abstain | review |
| 909 | abstain | act:82367 |
| 912 | abstain | abstain |
| 926 | abstain | review |
| 928 | abstain | review |
| 930 | abstain | review |
| 944 | abstain | review |
| 948 | abstain | review |
| 952 | abstain | review |
| 960 | abstain | review |
| 962 | abstain | review |
| 963 | abstain | act:83653 |
| 968 | abstain | review |
| 971 | abstain | review |
| 981 | abstain | review |
| 985 | abstain | review |
| 996 | abstain | review |
| 1000 | abstain | review |
| 1008 | abstain | review |
| 1020 | abstain | abstain |
| 1022 | abstain | review |
| 1028 | abstain | review |
| 1030 | abstain | review |
| 1032 | abstain | abstain |
| 1033 | abstain | review |
| 1036 | abstain | review |
| 1038 | abstain | review |
| 1041 | abstain | review |
| 1042 | abstain | review |
| 1044 | abstain | review |
| 1053 | abstain | review |
| 1057 | abstain | review |
| 1060 | abstain | review |
| 1063 | abstain | review |
| 1072 | abstain | review |
| 1073 | abstain | review |
| 1185 | abstain | review |
| 1206 | abstain | review |
| 1208 | abstain | act:14727 |
| 1230 | abstain | review |
| 1238 | abstain | review |
| 1243 | abstain | act:65475 |
| 1249 | abstain | act:84298 |
| 1257 | abstain | review |
| 1264 | abstain | review |
