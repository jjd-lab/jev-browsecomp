# Scoreboard

Mode `stub`. Suite `browsecomp-plus`. Arm C flat-retrieves over the per-question pool and calls stub decide. No provider was called.

`latency_ms` is the mean per question on this run. A later run can change it.
`cost_usd` is 0 because no provider returned a price.

| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 0.207 | 1.000 | 0.000 | 0.000 | 0.000000 | 8.0 |

Stub C exact_id_acc is 0.207 and cite_ok is 1.000. exact_id is set equality with the gold docids. cost_usd is 0.

The pack has 150 BrowseComp-Plus queries from Tevatron/browsecomp-plus revision 144cff8e35b5eaef7e526346aa60774a9deb941f. Pinned shard `data/test-00000-of-00006.parquet` sha256 4ff9e93054eaee61b8d079a89b7ec4d02f16c9d05fa6e2fef7185b0786427a3a. Shards in the draw: test-00000-of-00006.parquet, test-00001-of-00006.parquet, test-00002-of-00006.parquet, test-00003-of-00006.parquet. Eligible pool 165. See fixtures/browsecomp_plus/LICENSE.txt and fixtures/browsecomp_plus/PACK.json.
exact_id is set equality on the gold docids. Evidence docids are the documents labeled as needed to answer. The flat pool adds the first 4 usable negative docids in release order.
Arm C ranks that pool with Okapi BM25 (k1=1.2, b=0.75) on the full document text and calls decide on the top 3 ids. IDF and average length are taken inside that pool. Code copies the indexed span. The span is a verbatim slice of the document with no double quote.
Answer accuracy is not in this table.
Arms A and B are not run. Arm B remains the tree walk for a later recurse cut. This pack does not build that walk.
Stub decide returns Act on a unique best overlap among those ids, Review on a tie, and Abstain when every overlap is 0.

## Per question

| id | gold | C |
| --- | --- | --- |
| 6 | act:31173 | act:46930 |
| 7 | act:87290 | act:5341 |
| 10 | act:37250 | act:18290 |
| 12 | act:8412 | act:42118 |
| 20 | act:11288 | review |
| 30 | act:51456 | act:17507 |
| 36 | act:52862 | act:24652 |
| 37 | act:85088 | review |
| 50 | act:6493 | act:69439 |
| 61 | act:53730 | act:87038 |
| 67 | act:82352 | act:68508 |
| 69 | act:72360 | act:72360 |
| 70 | act:39636 | act:56616 |
| 74 | act:72667 | act:50713 |
| 209 | act:68214 | act:21695 |
| 211 | act:60006 | act:17858 |
| 219 | act:58631 | act:35891 |
| 228 | act:39643 | act:70944 |
| 234 | act:30191 | act:30191 |
| 251 | act:26611 | act:15122 |
| 255 | act:86826 | review |
| 261 | act:28761 | act:28761 |
| 262 | act:63409 | act:63409 |
| 265 | act:9660 | act:66792 |
| 266 | act:84916 | act:84916 |
| 282 | act:45388 | act:35931 |
| 287 | act:85242 | act:85242 |
| 309 | act:75064 | act:18128 |
| 315 | act:30687 | act:90905 |
| 319 | act:41926 | act:41926 |
| 331 | act:70445 | act:40697 |
| 333 | act:88879 | act:59751 |
| 337 | act:50198 | act:30559 |
| 342 | act:56147 | act:27287 |
| 349 | act:57264 | act:57264 |
| 353 | act:26789 | act:94079 |
| 354 | act:7093 | act:40658 |
| 356 | act:74612 | act:74612 |
| 468 | act:1426 | act:65526 |
| 469 | act:89639 | act:7293 |
| 470 | act:98848 | act:68842 |
| 471 | act:12516 | act:96936 |
| 480 | act:75172 | act:84049 |
| 484 | act:86435 | act:86435 |
| 495 | act:76155 | act:76155 |
| 497 | act:68061 | act:69759 |
| 502 | act:44045 | act:15439 |
| 524 | act:5677 | act:27503 |
| 527 | act:73317 | review |
| 552 | act:91738 | act:74790 |
| 553 | act:42392 | act:54431 |
| 556 | act:50715 | act:50715 |
| 561 | act:86444 | act:72594 |
| 569 | act:55065 | act:25380 |
| 575 | act:28343 | act:16068 |
| 579 | act:12761 | act:3324 |
| 581 | act:80624 | act:9130 |
| 582 | act:74180 | act:81260 |
| 583 | act:85177 | review |
| 587 | act:85723 | act:85723 |
| 588 | act:17210 | act:56124 |
| 592 | act:4813 | review |
| 593 | act:64506 | act:79594 |
| 594 | act:9628 | act:75808 |
| 596 | act:23829 | act:12909 |
| 605 | act:47140 | act:74324 |
| 607 | act:66885 | act:95214 |
| 611 | act:25113 | act:58983 |
| 614 | act:69505 | act:53935 |
| 618 | act:79680 | act:94750 |
| 624 | act:67367 | act:74144 |
| 627 | act:22294 | act:60455 |
| 632 | act:72814 | act:52135 |
| 635 | act:33399 | act:332 |
| 636 | act:62889 | act:19992 |
| 643 | act:59631 | act:83797 |
| 645 | act:28183 | act:5920 |
| 650 | act:26086 | act:78442 |
| 653 | act:42955 | act:75665 |
| 655 | act:71127 | review |
| 662 | act:7892 | act:13624 |
| 772 | act:93372 | act:45777 |
| 775 | act:51064 | act:51064 |
| 787 | act:8354 | act:82388 |
| 790 | act:93510 | act:28008 |
| 793 | act:29584 | act:79342 |
| 794 | act:68944 | act:5454 |
| 806 | act:10923 | act:61561 |
| 819 | act:44019 | act:82937 |
| 821 | act:64690 | review |
| 826 | act:26625 | act:84284 |
| 827 | act:52689 | act:51374 |
| 830 | act:75647 | review |
| 833 | act:52903 | act:72858 |
| 838 | act:29124 | act:51499 |
| 843 | act:69717 | act:10944 |
| 851 | act:7850 | act:7850 |
| 853 | act:51676 | act:77487 |
| 854 | act:41381 | act:45499 |
| 864 | act:374 | act:374 |
| 870 | act:84322 | act:84322 |
| 873 | act:65512 | act:77644 |
| 876 | act:74540 | act:74540 |
| 884 | act:31419 | act:17036 |
| 897 | act:42806 | act:93230 |
| 898 | act:52161 | act:10114 |
| 909 | act:30548 | act:96514 |
| 912 | act:33637 | act:51529 |
| 926 | act:44134 | review |
| 928 | act:86840 | act:100192 |
| 930 | act:27330 | act:27330 |
| 944 | act:76644 | act:76644 |
| 948 | act:52952 | act:52952 |
| 952 | act:1600 | act:92949 |
| 960 | act:21800 | review |
| 962 | act:33026 | act:33026 |
| 963 | act:56120 | act:56120 |
| 968 | act:45335 | act:75162 |
| 971 | act:95857 | act:6193 |
| 981 | act:15348 | act:89555 |
| 985 | act:50013 | act:94137 |
| 996 | act:1478 | act:1478 |
| 1000 | act:33294 | act:33294 |
| 1008 | act:73771 | act:62635 |
| 1020 | act:16793 | act:4234 |
| 1022 | act:42206 | act:100159 |
| 1028 | act:23639 | act:10752 |
| 1030 | act:65120 | act:96454 |
| 1032 | act:56046 | act:54513 |
| 1033 | act:72169 | act:16137 |
| 1036 | act:33069 | act:75822 |
| 1038 | act:36249 | act:36249 |
| 1041 | act:61696 | act:40325 |
| 1042 | act:33958 | act:79586 |
| 1044 | act:74764 | act:40056 |
| 1053 | act:78028 | act:78028 |
| 1057 | act:5868 | act:5868 |
| 1060 | act:11483 | review |
| 1063 | act:29352 | act:22608 |
| 1072 | act:51882 | act:51882 |
| 1073 | act:1302 | act:37424 |
| 1185 | act:58097 | act:24184 |
| 1206 | act:7581 | act:3917 |
| 1208 | act:99079 | act:56725 |
| 1230 | act:98819 | act:98819 |
| 1238 | act:4444 | act:67664 |
| 1243 | act:70561 | act:6391 |
| 1249 | act:78744 | act:42464 |
| 1257 | act:86876 | act:69351 |
| 1264 | act:28287 | act:28287 |
