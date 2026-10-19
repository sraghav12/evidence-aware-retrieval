# Evidence-aware retrieval: four real-filing traces

Exported from saved run `real_dev_002` (executor only, 0 provider calls). Every number below is a raw inline-XBRL cell; locators point into the SEC filing.

## Early stop: complete evidence after the cheap stage

**Question:** What was Apple FY2024 revenue growth over FY2023? (as of 2025-03-01)

**Route:** cheap_search → answer

- `cheap_search`: 12 units, 3724 tokens inspected; supported 2, missing 0, conflicts 0

**Result:** answered — `"2.02"` percent

- cited `AAPL_10K_2023` FY2023 = 383285 USD_million — table 27, row 7, fact `f-385` ([filing](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm))
- cited `AAPL_10K_2024` FY2024 = 391035 USD_million — table 22, row 6, fact `f-66` ([filing](https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm))
- cited `AAPL_10K_2024` FY2023 = 383285 USD_million — table 22, row 6, fact `f-67` ([filing](https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm))

## Escalation: section search recovers the missing company

**Question:** What was Apple and Coca-Cola FY2023 total revenue? (as of 2024-06-30)

**Route:** cheap_search → section_search → answer

- `cheap_search`: 12 units, 2826 tokens inspected; supported 1, missing 1, conflicts 0
- `section_search`: 12 units, 4637 tokens inspected; supported 2, missing 0, conflicts 0

**Result:** answered — `"429039"` USD_million

- cited `KO_10K_2023` FY2023 = 45754 USD_million — table 26, row 2, fact `f-92` ([filing](https://www.sec.gov/Archives/edgar/data/21344/000002134424000009/ko-20231231.htm))
- cited `AAPL_10K_2023` FY2023 = 383285 USD_million — table 22, row 6, fact `f-69` ([filing](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm))

## Principled abstention: reported vs restated revenue

**Question:** What was Johnson & Johnson FY2022 revenue? (as of 2024-06-30)

**Route:** cheap_search → abstain

- `cheap_search`: 12 units, 2801 tokens inspected; supported 0, missing 1, conflicts 1

**Result:** abstained — reason `conflicting_evidence`

- `JNJ_10K_2022` FY2022 = 94943 USD_million — table 69, row 2, fact `id3VybDovL2RvY3MudjEvZG9…` ([filing](https://www.sec.gov/Archives/edgar/data/200406/000020040623000016/jnj-20230101.htm))
- `JNJ_10K_2023` FY2022 = 79990 USD_million — table 75, row 2, fact `f-136` ([filing](https://www.sec.gov/Archives/edgar/data/200406/000020040624000013/jnj-20231231.htm))

## Unresolved failure: BM25 slot competition in a three-company ranking

**Question:** Rank Apple, AMD and Coca-Cola by FY2024 revenue growth over FY2023. (as of 2025-03-01)

**Route:** cheap_search → section_search → expanded_search → abstain

- `cheap_search`: 12 units, 3708 tokens inspected; supported 0, missing 6, conflicts 0
- `section_search`: 12 units, 4095 tokens inspected; supported 2, missing 4, conflicts 0
- `expanded_search`: 12 units, 4101 tokens inspected; supported 3, missing 3, conflicts 0

**Result:** abstained — reason `incomplete_evidence`

- `KO_10K_2023` FY2023 = 45754 USD_million — table 26, row 2, fact `f-92` ([filing](https://www.sec.gov/Archives/edgar/data/21344/000002134424000009/ko-20231231.htm))
- `KO_10K_2024` FY2024 = 47061 USD_million — table 26, row 2, fact `f-121` ([filing](https://www.sec.gov/Archives/edgar/data/21344/000002134425000011/ko-20241231.htm))
- `KO_10K_2024` FY2023 = 45754 USD_million — table 26, row 2, fact `f-122` ([filing](https://www.sec.gov/Archives/edgar/data/21344/000002134425000011/ko-20241231.htm))
- `AAPL_10K_2023` FY2023 = 383285 USD_million — table 27, row 7, fact `f-385` ([filing](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm))

