# OmniNode NEAR Intents & Swarm Quorum

Policy-gated multi-agent coordination, confidential NEAR AI Cloud TEE maker/checker quorum, Cellular Sheaf coboundary dispute pinpointing, and exact `2^K` Shapley cross-chain settlement built for the **NEAR Hackathon** (`agents`, `swarms`, `security`, `privacy`).

## Baseline vs. Hackathon Window Work Disclosure

- **Pre-Hackathon Baseline (`pre-hackathon` tag)**: Domain-agnostic Configuration Settings Grid (`src/grid_ledger_core.py`) and core clause/lease/WebAssembly/Sheaf/Shapley math (`src/sheaf_shapley_wasm_core.py`).
- **NEAR Hackathon Additions (`hackathon-submission` tag)**: NEAR Intents `1Click` (`dry: true`) quote adapter, NEAR AI Cloud TEE (`cloud-api.near.ai`) disjoint `maker != checker` quorum client, NEAR `near_sdk` Function-Call Policy Escrow smart contract (`contracts/near_policy_escrow/src/lib.rs`), interactive Paper & Ink WebAssembly studio (`web/omninode-near-studio.html`), deterministic CLI (`cli.py`), and 12-test suite (`tests/test_near_intent_quorum.py`).
- **Direct Diff URL**: `https://github.com/aidonerightcorp/omninode-near-intents/compare/pre-hackathon...hackathon-submission`

## Quick Reproducibility (`Do X -> See Y` in Under 5 Seconds, Zero Keys Required)

Every external endpoint defaults to a deterministic offline twin so automated evaluators can inspect every gate immediately with Python 3.10+ stdlib:

1. **Do**: Run the 12-check test suite:
   ```bash
   python3 -m unittest discover -s tests -v
   ```
   **See**: `Ran 12 tests ... OK` (covering zero-hardcoded-values AST check, domain-agnostic naming, lease-epoch replay block, `50 B` WebAssembly spend-cap tripwire, `maker != checker` TEE quorum, Cellular Sheaf tamper edge pinpointing, and exact `2^K` Shapley micro-unit conservation).

2. **Do**: Run all 4 end-to-end NEAR Swarm scenarios via CLI:
   ```bash
   python3 cli.py --scenario all
   ```
   **See**: Structured JSON showing:
   - `settle`: `"SETTLED_VIA_NEAR_INTENTS_AND_SHAPLEY"` (`net_micro_units: 2475000 == sum_allocated_micro_units: 2475000`, plus 3 `dry: true` NEAR Intents `nep141:wrap.near -> nep141:usdc.tether-token.near` quotes)
   - `ambiguous`: `"REJECTED_PRE_LOCK_AMBIGUOUS_CLAUSE"` (`["asap", "best effort"]` caught prior to escrow lock)
   - `tamper`: `"HELD_ON_SHEAF_OBSTRUCTION"` (`top_obstruction_edge: "relay->checker"`)
   - `runaway`: `"ABORTED_BY_WASM_SPEND_GUARDRAIL"` (`95,000,000 > 10,000,000` cap)

3. **Do**: Open `web/omninode-near-studio.html` in any browser.
   **See**: Live Paper & Ink (`#f5f2ea`, light-only) interactive studio instantiating the `50 B` WebAssembly budget policy gate in-browser across all 4 scenarios.

## Live NEAR AI Cloud TEE & NEAR Intents Mode

Set optional environment flags to switch from the deterministic twin to live NEAR endpoints:
- `NEAR_AI_API_KEY=<key>` -> routes checker quorum prompts through `https://cloud-api.near.ai/v1/chat/completions`
- `NEAR_INTENTS_LIVE=1` -> posts `dry: true` exact-input quote envelopes to `https://1click.chaindefuser.com/v0/quote`

## License

MIT (`LICENSE`).
