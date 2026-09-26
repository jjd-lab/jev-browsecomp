# Scoreboard

Mode `live`. Suite `browsecomp-plus`. Arm C calls typed decide on the top 8 documents. Jev decode is `both`.

`latency_ms` is the mean per question on this run. A later run can change it.
`cost_usd` is the mean per question. Jev uses 0.042 dollars per million input tokens.

| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 0.460 | 1.000 | 0.000 | 0.013 | 0.000614 | 651.7 |

Live C exact_id_acc is 0.460 and cite_ok is 1.000. Mean cost_usd is 0.000614. exact_id is set equality with the gold docids.

The pack has 150 BrowseComp-Plus queries from Tevatron/browsecomp-plus revision 144cff8e35b5eaef7e526346aa60774a9deb941f. Pinned shard `data/test-00000-of-00006.parquet` sha256 4ff9e93054eaee61b8d079a89b7ec4d02f16c9d05fa6e2fef7185b0786427a3a. Shards in the draw: test-00000-of-00006.parquet, test-00001-of-00006.parquet, test-00002-of-00006.parquet, test-00003-of-00006.parquet. Eligible pool 165. See fixtures/browsecomp_plus/LICENSE.txt and fixtures/browsecomp_plus/PACK.json.
exact_id is set equality on the gold docids. Evidence docids are the documents labeled as needed to answer. The flat pool adds the first 4 usable negative docids in release order.
Arm C ranks that pool with Okapi BM25 (k1=1.2, b=0.75) on the full document text and calls decide on the top 3 ids. IDF and average length are taken inside that pool. Code copies the indexed span. The span is a verbatim slice of the document with no double quote.
Answer accuracy is not in this table.
Arms A and B are not run. Arm B remains the tree walk for a later recurse cut. This pack does not build that walk.
Live prompts send at most 12000 characters from the start of each top-k document.

## Per question

| id | gold | C |
| --- | --- | --- |
| 6 | act:31173 | act:31173 |
| 7 | act:87290 | review |
| 10 | act:37250 | act:17299 |
| 12 | act:8412 | review |
| 20 | act:11288 | act:11288 |
| 30 | act:51456 | act:51456 |
| 36 | act:52862 | review |
| 37 | act:85088 | act:85088 |
| 50 | act:6493 | act:6493 |
| 61 | act:53730 | act:83844 |
| 67 | act:82352 | act:3783 |
| 69 | act:72360 | act:86999 |
| 70 | act:39636 | review |
| 74 | act:72667 | act:72667 |
| 209 | act:68214 | act:34649 |
| 211 | act:60006 | act:60006 |
| 219 | act:58631 | review |
| 228 | act:39643 | act:39643 |
| 234 | act:30191 | review |
| 251 | act:26611 | review |
| 255 | act:86826 | review |
| 261 | act:28761 | act:28761 |
| 262 | act:63409 | review |
| 265 | act:9660 | review |
| 266 | act:84916 | act:84916 |
| 282 | act:45388 | act:45388 |
| 287 | act:85242 | review |
| 309 | act:75064 | act:75064 |
| 315 | act:30687 | review |
| 319 | act:41926 | act:41926 |
| 331 | act:70445 | act:70445 |
| 333 | act:88879 | act:59751 |
| 337 | act:50198 | act:50198 |
| 342 | act:56147 | act:56512 |
| 349 | act:57264 | act:59431 |
| 353 | act:26789 | act:26789 |
| 354 | act:7093 | act:40658 |
| 356 | act:74612 | act:38409 |
| 468 | act:1426 | act:1426 |
| 469 | act:89639 | act:89639 |
| 470 | act:98848 | act:98848 |
| 471 | act:12516 | act:12516 |
| 480 | act:75172 | review |
| 484 | act:86435 | review |
| 495 | act:76155 | act:76155 |
| 497 | act:68061 | review |
| 502 | act:44045 | act:44045 |
| 524 | act:5677 | act:5677 |
| 527 | act:73317 | act:5290 |
| 552 | act:91738 | review |
| 553 | act:42392 | review |
| 556 | act:50715 | act:50715 |
| 561 | act:86444 | review |
| 569 | act:55065 | act:55065 |
| 575 | act:28343 | review |
| 579 | act:12761 | review |
| 581 | act:80624 | act:80624 |
| 582 | act:74180 | act:74180 |
| 583 | act:85177 | act:85177 |
| 587 | act:85723 | review |
| 588 | act:17210 | act:40871 |
| 592 | act:4813 | review |
| 593 | act:64506 | act:64506 |
| 594 | act:9628 | act:9628 |
| 596 | act:23829 | review |
| 605 | act:47140 | review |
| 607 | act:66885 | act:95214 |
| 611 | act:25113 | review |
| 614 | act:69505 | act:59177 |
| 618 | act:79680 | review |
| 624 | act:67367 | act:74144 |
| 627 | act:22294 | act:22294 |
| 632 | act:72814 | review |
| 635 | act:33399 | review |
| 636 | act:62889 | act:62889 |
| 643 | act:59631 | review |
| 645 | act:28183 | act:28183 |
| 650 | act:26086 | act:26086 |
| 653 | act:42955 | act:42955 |
| 655 | act:71127 | act:71127 |
| 662 | act:7892 | act:1548 |
| 772 | act:93372 | act:93372 |
| 775 | act:51064 | review |
| 787 | act:8354 | review |
| 790 | act:93510 | act:93510 |
| 793 | act:29584 | review |
| 794 | act:68944 | review |
| 806 | act:10923 | act:10923 |
| 819 | act:44019 | act:44019 |
| 821 | act:64690 | act:64690 |
| 826 | act:26625 | act:26625 |
| 827 | act:52689 | review |
| 830 | act:75647 | act:54126 |
| 833 | act:52903 | review |
| 838 | act:29124 | act:29124 |
| 843 | act:69717 | review |
| 851 | act:7850 | review |
| 853 | act:51676 | act:51676 |
| 854 | act:41381 | act:41381 |
| 864 | act:374 | act:11918 |
| 870 | act:84322 | act:32790 |
| 873 | act:65512 | abstain |
| 876 | act:74540 | act:74540 |
| 884 | act:31419 | act:9391 |
| 897 | act:42806 | act:42806 |
| 898 | act:52161 | abstain |
| 909 | act:30548 | act:82367 |
| 912 | act:33637 | review |
| 926 | act:44134 | act:44134 |
| 928 | act:86840 | act:86840 |
| 930 | act:27330 | review |
| 944 | act:76644 | act:76644 |
| 948 | act:52952 | act:52952 |
| 952 | act:1600 | act:51325 |
| 960 | act:21800 | act:21800 |
| 962 | act:33026 | act:33026 |
| 963 | act:56120 | act:56120 |
| 968 | act:45335 | act:45335 |
| 971 | act:95857 | act:95857 |
| 981 | act:15348 | review |
| 985 | act:50013 | act:50013 |
| 996 | act:1478 | review |
| 1000 | act:33294 | act:33294 |
| 1008 | act:73771 | act:72157 |
| 1020 | act:16793 | act:16793 |
| 1022 | act:42206 | act:69906 |
| 1028 | act:23639 | review |
| 1030 | act:65120 | act:23048 |
| 1032 | act:56046 | act:56046 |
| 1033 | act:72169 | act:72169 |
| 1036 | act:33069 | review |
| 1038 | act:36249 | act:36249 |
| 1041 | act:61696 | act:61696 |
| 1042 | act:33958 | act:33958 |
| 1044 | act:74764 | review |
| 1053 | act:78028 | review |
| 1057 | act:5868 | review |
| 1060 | act:11483 | act:39092 |
| 1063 | act:29352 | act:76179 |
| 1072 | act:51882 | act:51882 |
| 1073 | act:1302 | act:1302 |
| 1185 | act:58097 | review |
| 1206 | act:7581 | act:7581 |
| 1208 | act:99079 | act:22997 |
| 1230 | act:98819 | act:98819 |
| 1238 | act:4444 | review |
| 1243 | act:70561 | review |
| 1249 | act:78744 | act:78744 |
| 1257 | act:86876 | review |
| 1264 | act:28287 | act:55008 |
