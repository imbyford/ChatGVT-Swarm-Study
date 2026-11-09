# Focused audit implementation response

The user's seven final CODEX AUDIT findings were incorporated after R2 collection had completed. This response documents implementation checks; it is not a new independent scientific review or human validation.

| Finding | Completed action and evidence |
| --- | --- |
| Preserve historical scoring and binding results | R1's adverse results remain unchanged. The manuscript states that the focused reviewer found no scoring-sign or saved-binding mismatch. Exact offline replay retains all historical analyses. |
| Check the actual first nonblank R2 field | The frozen `r1/prefix.py` first separates lines and then uses exact matching on one line. It is not the historical multiline regex. `Choice:` followed by an ID on the next line is invalid. Thirty-four tests cover LF/CRLF, EOS, length limits, empty/incomplete fields, preambles, competing first-line values and irrevocable later-line conflicts. |
| No mid-run protocol changes | R2 was already complete. No parser, protocol, action, scoring or observation was changed. The tested parser hash matches the precollection freeze; all 244 frozen files remain exact. |
| U format terminology | Verified exact raw records for three of 17 historical U extractor-valid choices without a complete Trade-off field. Section 4.5 and Appendix E distinguish extractor validity from full compliance; original scores remain intact. |
| Interface-specific N uptake | The 4/5 versus 1/5 saved-prefix observation is preserved alongside rationale contradictions, the full 25-row diagnostics and U missingness. It is not described as reliable N-policy acquisition. |
| Protected versus development | The manuscript explicitly reports protected harm reductions for all three R1 arms and N's larger reduction than V's. Development results remain separate; R2 development missingness is reported. |
| Author attribution | Author has now confirmed Independent researcher, United Kingdom, and no project-specific work before 6 November 2026. Updated without claiming institutional affiliation. |

All 62 readable fields in the GUIDE's 72 saved-response records were additionally checked to place their exact extracted action on the actual first nonblank line. The original GUIDE first-field report was reproduced byte-for-byte; its historical rule is not reused as R2's production parser.

Reproduction: run `scripts/verify_final_audit.py` with Python 3.12/3.13 from the extracted delivery. It checks the packaged frozen parser and saved raw data and writes the same focused evidence record. Then run `reproducibility/reproduce.py` for the complete historical and R2 replay. Neither loads a model or accesses a provider.
