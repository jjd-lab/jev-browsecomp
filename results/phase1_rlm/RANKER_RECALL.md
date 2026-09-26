# Ranker recall: does the top 8 hold a gold doc?

Phase 1 main questions 1–100, each with 1,000 docs. Jev's top 8 is from the recorded arm J rows; BM25's top 8 is recomputed over full document text. "Hard" = a question where arm A or B hit the v1 turn cap (27 of 100).

| Set | n | BM25 | Jev |
| --- | ---: | ---: | ---: |
| All | 100 | 49 | 94 |
| Hard | 27 | 10 | 23 |
| Easy | 73 | 39 | 71 |

Both 48, Jev only 46, BM25 only 1, neither 5.
