# M5 dev gate (a development check, not a result)

v1 `d269d28d9581…`, v2 `0a788479eb8c…`. **Gate: FAILED**

| Check | v1 | v2 | Requirement | Met |
|---|---|---|---|---|
| G1 runs with a valid change-tool call before the first ranking | 0/22 | 22/22 | v2 >= 16 of 22 | True |
| G2 valid reports | 19/22 | 17/22 | v2 >= v1 | False |
| G3 unknown_tool calls | 0 | 0 | v2 = 0 | True |
| G4 overflow runs | 1 | 4 | v2 = 0 | False |

Information only (not gated):

- dev top-1: v1 8/22, v2 12/22
- compaction levels, all requests: v1 {0: 36, 1: 29, 2: 29, 3: 217, 4: 138}, v2 {0: 64, 1: 33, 2: 15, 3: 180, 4: 126}
- at HYPOTHESIZE: v1 {0: 8, 1: 2, 2: 4, 3: 6}, v2 {0: 12, 1: 4, 3: 5}
- at REPORT: v1 {2: 1, 3: 18}, v2 {2: 2, 3: 15}
