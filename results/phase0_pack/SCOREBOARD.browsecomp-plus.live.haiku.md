# Scoreboard

Mode `live`. Suite `browsecomp-plus`. Arm C calls typed decide on the top 3 documents. Arm C uses the scored chat decide: a route with p(act) and one support probability per id, decoded like Jev `both`.

`latency_ms` is the mean per question on this run. A later run can change it.
`cost_usd` is the mean per question. Anthropic model `claude-haiku-4-5` is priced at 1.00 dollars per million input tokens and 5.00 dollars per million output tokens. Jev uses 0.042 dollars per million input tokens.

| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 0.340 | 1.000 | 0.000 | 0.120 | 0.008626 | 1559.8 |

Live C exact_id_acc is 0.340 and cite_ok is 1.000. Mean cost_usd is 0.008626. exact_id is set equality with the gold docids.

The pack has 150 BrowseComp-Plus queries from Tevatron/browsecomp-plus revision 144cff8e35b5eaef7e526346aa60774a9deb941f. Pinned shard `data/test-00000-of-00006.parquet` sha256 4ff9e93054eaee61b8d079a89b7ec4d02f16c9d05fa6e2fef7185b0786427a3a. Shards in the draw: test-00000-of-00006.parquet, test-00001-of-00006.parquet, test-00002-of-00006.parquet, test-00003-of-00006.parquet. Eligible pool 165. See fixtures/browsecomp_plus/LICENSE.txt and fixtures/browsecomp_plus/PACK.json.
exact_id is set equality on the gold docids. Evidence docids are the documents labeled as needed to answer. The flat pool adds the first 4 usable negative docids in release order.
Arm C ranks that pool with Okapi BM25 (k1=1.2, b=0.75) on the full document text and calls decide on the top 3 ids. IDF and average length are taken inside that pool. Code copies the indexed span. The span is a verbatim slice of the document with no double quote.
Answer accuracy is not in this table.
Arms A and B are not run. Arm B remains the tree walk for a later recurse cut. This pack does not build that walk.
Live prompts send at most 12000 characters from the start of each top-k document.

## Per question

| id | gold | C |
| --- | --- | --- |
| 6 | act:31173 | review |
| 7 | act:87290 | review |
| 10 | act:37250 | abstain |
| 12 | act:8412 | review |
| 20 | act:11288 | act:23118 |
| 30 | act:51456 | act:51456 |
| 36 | act:52862 | review |
| 37 | act:85088 | review |
| 50 | act:6493 | review |
| 61 | act:53730 | act:11492 |
| 67 | act:82352 | act:68508 |
| 69 | act:72360 | act:98058 |
| 70 | act:39636 | review |
| 74 | act:72667 | act:72667 |
| 209 | act:68214 | review |
| 211 | act:60006 | act:60006 |
| 219 | act:58631 | review |
| 228 | act:39643 | act:39643 |
| 234 | act:30191 | act:5120 |
| 251 | act:26611 | abstain |
| 255 | act:86826 | act:52926 |
| 261 | act:28761 | act:28761 |
| 262 | act:63409 | abstain |
| 265 | act:9660 | abstain |
| 266 | act:84916 | act:84916 |
| 282 | act:45388 | act:78675 |
| 287 | act:85242 | act:85242 |
| 309 | act:75064 | act:87041 |
| 315 | act:30687 | abstain |
| 319 | act:41926 | act:41926 |
| 331 | act:70445 | act:40697 |
| 333 | act:88879 | act:59751 |
| 337 | act:50198 | act:30559 |
| 342 | act:56147 | act:56512 |
| 349 | act:57264 | act:57264 |
| 353 | act:26789 | act:67775 |
| 354 | act:7093 | act:7093 |
| 356 | act:74612 | act:74612 |
| 468 | act:1426 | act:1426 |
| 469 | act:89639 | act:7293 |
| 470 | act:98848 | review |
| 471 | act:12516 | review |
| 480 | act:75172 | act:86730 |
| 484 | act:86435 | act:28465 |
| 495 | act:76155 | act:76155 |
| 497 | act:68061 | review |
| 502 | act:44045 | act:15453 |
| 524 | act:5677 | act:27503 |
| 527 | act:73317 | review |
| 552 | act:91738 | act:91738 |
| 553 | act:42392 | review |
| 556 | act:50715 | act:50715 |
| 561 | act:86444 | act:86444 |
| 569 | act:55065 | act:55065 |
| 575 | act:28343 | review |
| 579 | act:12761 | review |
| 581 | act:80624 | act:80624 |
| 582 | act:74180 | act:74180 |
| 583 | act:85177 | review |
| 587 | act:85723 | abstain |
| 588 | act:17210 | review |
| 592 | act:4813 | review |
| 593 | act:64506 | act:64506 |
| 594 | act:9628 | act:9628 |
| 596 | act:23829 | act:12909 |
| 605 | act:47140 | act:57487 |
| 607 | act:66885 | act:95214 |
| 611 | act:25113 | abstain |
| 614 | act:69505 | review |
| 618 | act:79680 | act:51187 |
| 624 | act:67367 | act:74144 |
| 627 | act:22294 | act:22294 |
| 632 | act:72814 | act:22191 |
| 635 | act:33399 | act:33399 |
| 636 | act:62889 | act:19992 |
| 643 | act:59631 | act:59631 |
| 645 | act:28183 | act:28183 |
| 650 | act:26086 | review |
| 653 | act:42955 | review |
| 655 | act:71127 | act:71127 |
| 662 | act:7892 | act:7892 |
| 772 | act:93372 | review |
| 775 | act:51064 | act:51064 |
| 787 | act:8354 | act:82388 |
| 790 | act:93510 | act:28008 |
| 793 | act:29584 | review |
| 794 | act:68944 | review |
| 806 | act:10923 | review |
| 819 | act:44019 | review |
| 821 | act:64690 | abstain |
| 826 | act:26625 | act:55054 |
| 827 | act:52689 | act:52689 |
| 830 | act:75647 | act:54126 |
| 833 | act:52903 | act:40824 |
| 838 | act:29124 | act:51499 |
| 843 | act:69717 | abstain |
| 851 | act:7850 | review |
| 853 | act:51676 | act:51676 |
| 854 | act:41381 | abstain |
| 864 | act:374 | act:374 |
| 870 | act:84322 | act:84322 |
| 873 | act:65512 | abstain |
| 876 | act:74540 | act:74540 |
| 884 | act:31419 | review |
| 897 | act:42806 | abstain |
| 898 | act:52161 | review |
| 909 | act:30548 | review |
| 912 | act:33637 | act:33637 |
| 926 | act:44134 | abstain |
| 928 | act:86840 | act:100192 |
| 930 | act:27330 | review |
| 944 | act:76644 | act:76644 |
| 948 | act:52952 | act:52952 |
| 952 | act:1600 | act:1600 |
| 960 | act:21800 | act:21800 |
| 962 | act:33026 | act:33026 |
| 963 | act:56120 | act:56120 |
| 968 | act:45335 | act:97882 |
| 971 | act:95857 | act:9900 |
| 981 | act:15348 | abstain |
| 985 | act:50013 | review |
| 996 | act:1478 | act:1478 |
| 1000 | act:33294 | act:33294 |
| 1008 | act:73771 | act:3774 |
| 1020 | act:16793 | abstain |
| 1022 | act:42206 | review |
| 1028 | act:23639 | act:10752 |
| 1030 | act:65120 | review |
| 1032 | act:56046 | act:56046 |
| 1033 | act:72169 | abstain |
| 1036 | act:33069 | review |
| 1038 | act:36249 | act:36249 |
| 1041 | act:61696 | act:40325 |
| 1042 | act:33958 | act:79586 |
| 1044 | act:74764 | abstain |
| 1053 | act:78028 | review |
| 1057 | act:5868 | act:47667 |
| 1060 | act:11483 | act:11483 |
| 1063 | act:29352 | review |
| 1072 | act:51882 | act:51882 |
| 1073 | act:1302 | review |
| 1185 | act:58097 | abstain |
| 1206 | act:7581 | act:7581 |
| 1208 | act:99079 | act:99079 |
| 1230 | act:98819 | act:98819 |
| 1238 | act:4444 | review |
| 1243 | act:70561 | act:70561 |
| 1249 | act:78744 | act:42464 |
| 1257 | act:86876 | review |
| 1264 | act:28287 | act:28287 |
