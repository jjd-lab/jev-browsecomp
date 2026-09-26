# Scoreboard

Mode `live`. Arm A fans out one chat completion per depth-1 section. Arm B calls typed id decide. Arm C retrieves the top 3 depth-2 nodes and asks for id cites. Jev decode is `noul_only`.

`latency_ms` is the mean per question on this run. A later run can change it.
`cost_usd` is the mean per question. Anthropic model `claude-haiku-4-5` is priced at 1.00 dollars per million input tokens and 5.00 dollars per million output tokens. Jev uses 0.042 dollars per million input tokens.

| arm | exact_id_acc | cite_ok | illegal_span_rate | abstain_rate | cost_usd | latency_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0.174 | 0.000 | 1.000 | 0.565 | 0.015699 | 37674.6 |
| B | 0.739 | 1.000 | 0.000 | 0.261 | 0.000233 | 834.4 |
| C | 0.696 | 1.000 | 0.000 | 0.261 | 0.000016 | 297.9 |

Live B exact_id_acc is 0.739 and live C exact_id_acc is 0.696. B is ahead on accuracy. Mean cost_usd is 0.000233 for B and 0.000016 for C, so C is cheaper. Risk-coverage is not in the table. Live abstain uses the decision itself, and this run does not sweep a threshold.

The gold file has 23 questions from HotpotQA dev distractor v1 (Yang et al., EMNLP 2018, https://hotpotqa.github.io/), CC BY-SA 4.0. Passages are the Wikipedia sentences frozen in that dump. This repo assigns the node ids. Each question contributes its two supporting articles, not the eight distractor paragraphs. See fixtures/LICENSE.txt and fixtures/provenance.jsonl.
Arm A sends free-form text per depth-1 section. A quote that is not `Span.text` is an illegal span.
Arm B returns `Act`, `Review`, or `Abstain`. Code copies `Span.text`.
Arm C asks for ids from the top 3 depth-2 nodes. Code copies `Span.text`.

## Per question

| id | gold | A | B | C |
| --- | --- | --- | --- | --- |
| b01 | act:al-horford/al-horford/0 | act:al-horford/al-horford illegal | act:al-horford/al-horford/0 | act:2007-08-atlanta-hawks-season/2007-08-atlanta-hawks-season/1 |
| b02 | act:pat-bowlen/pat-bowlen/2 | abstain illegal | act:pat-bowlen/pat-bowlen/2 | act:pat-bowlen/pat-bowlen/2 |
| b03 | act:anita-berber/anita-berber/0 | abstain illegal | act:anita-berber/anita-berber/0 | act:anita-berber/anita-berber/0 |
| b04 | act:roman-gonzalez-boxer/roman-gonzalez-boxer/0 | abstain illegal | act:roman-gonzalez-boxer/roman-gonzalez-boxer/1 | act:roman-gonzalez-boxer/roman-gonzalez-boxer/1 |
| b05 | act:wij-zijn-ajax/wij-zijn-ajax/1 | abstain illegal | act:wij-zijn-ajax/wij-zijn-ajax/1 | act:wij-zijn-ajax/wij-zijn-ajax/1 |
| b06 | act:baltimore-orioles/baltimore-orioles/2 | act:baltimore-orioles/baltimore-orioles illegal | act:baltimore-orioles/baltimore-orioles/2 | act:baltimore-orioles/baltimore-orioles/2 |
| b07 | act:percheron/percheron/5 | abstain illegal | act:percheron/percheron/5 | act:percheron/percheron/5 |
| b08 | act:howl-s-moving-castle/howl-s-moving-castle/2 | abstain illegal | act:howl-s-moving-castle/howl-s-moving-castle/2 | act:howl-s-moving-castle/howl-s-moving-castle/2 |
| b09 | act:illegal-drug-trade-in-the-philippines/illegal-drug-trade-in-the-philippines/2 | act:illegal-drug-trade-in-the-philippines/illegal-drug-trade-in-the-philippines illegal | act:ephedrine/ephedrine/4 | act:ephedrine/ephedrine/4 |
| b10 | act:saab-36/saab-36/3 | act:saab-36/saab-36 illegal | act:saab-36/saab-36/3 | act:saab-36/saab-36/3 |
| b11 | act:winner-band/winner-band/0 | act:winner-band/winner-band illegal | act:winner-band/winner-band/0 | act:winner-band/winner-band/0 |
| e01 | act:the-churchills-tv-series/the-churchills-tv-series/0 | act:david-starkey/david-starkey+the-churchills-tv-series/the-churchills-tv-series illegal | act:the-churchills-tv-series/the-churchills-tv-series/0 | act:the-churchills-tv-series/the-churchills-tv-series/0 |
| e02 | act:carl-maria-von-weber/carl-maria-von-weber/0 | act:carl-maria-von-weber/carl-maria-von-weber illegal | act:heinrich-marschner/heinrich-marschner/0 | act:heinrich-marschner/heinrich-marschner/0 |
| e03 | act:united-states-house-of-representatives/united-states-house-of-representatives/0 | abstain illegal | act:lafe-pence/lafe-pence/0 | act:lafe-pence/lafe-pence/0 |
| e04 | act:howell-conant/howell-conant/0 | abstain illegal | act:howell-conant/howell-conant/0 | act:howell-conant/howell-conant/0 |
| m01 | act:big-stone-gap-film/big-stone-gap-film/0+adriana-trigiani/adriana-trigiani/0 | abstain illegal | act:adriana-trigiani/adriana-trigiani/0 | act:adriana-trigiani/adriana-trigiani/0 |
| m02 | act:lewiston-maineiacs/lewiston-maineiacs/1+androscoggin-bank-colisee/androscoggin-bank-colisee/0 | act:androscoggin-bank-colisee/androscoggin-bank-colisee illegal | act:androscoggin-bank-colisee/androscoggin-bank-colisee/0 | act:androscoggin-bank-colisee/androscoggin-bank-colisee/0 |
| z01 | abstain | abstain illegal | abstain | abstain |
| z02 | abstain | abstain illegal | abstain | abstain |
| z03 | abstain | abstain illegal | abstain | abstain |
| z04 | abstain | act:biological/scientific+biology/molecular+scientific/medical+scientific/biological+biological/biochemical+biological/molecular illegal | abstain | abstain |
| z05 | abstain | act:nuclear/chemistry+chemistry/nuclear illegal | abstain | abstain |
| z06 | abstain | abstain illegal | abstain | abstain |
