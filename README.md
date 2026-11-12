# OmniNode NEAR Intents & Swarm Quorum (`v1.1.0`)

Policy-gated multi-agent coordination, confidential NEAR AI Cloud TEE maker/checker quorum, Cellular Sheaf coboundary dispute pinpointing, and exact `2^K` Shapley cross-chain settlement built for the **NEAR Hackathon** (`agents`, `swarms`, `security`, `privacy`).

## Hackathon Window Development & Commit Disclosure

- **Built Fresh During the Hackathon Window**: This entire repository was written fresh during the NEAR Hackathon window (November 2026); no code in this repository predates October 19.
- **Scaffold-to-Release Commit Progression (`dff7726` -> `HEAD`)**: Initial commit `dff7726` (tagged `pre-hackathon` at initial push) holds only the minimal domain-agnostic scaffold (`src/grid_ledger_core.py` and `src/sheaf_shapley_wasm_core.py`), followed in the hackathon window by the NEAR Intents `1Click` quote & live read-only token adapter (`src/near_intent_quorum_adapter.py`), live zero-spend NEAR Mainnet/Testnet RPC + `1Click` check (`cli.py --live-readonly-check` and `artifacts/live_near_readonly_probe.json`), NEAR AI Cloud TEE (`cloud-api.near.ai`) disjoint `maker != checker` quorum client, compiled and unit-tested Rust policy-escrow state machine (`contracts/near_policy_escrow/`), interactive Paper & Ink WebAssembly studio (`web/omninode-near-studio.html`), and automated Python + Rust test suites (`v1.1.0`).
- **Full Implementation Diff**: `https://github.com/aidonerightcorp/omninode-near-intents/compare/dff7726...main`

## Quick Reproducibility (`Do X -> See Y` in Under 5 Seconds, Zero Keys Required)

1. **Do**: Run the Python functional & conformance test suite:
   ```bash
   python3 -m unittest discover -s tests -v
   ```
   **See**: All tests pass (`OK`), covering zero-hardcoded-values AST gate, domain-agnostic naming, banned-word & private-name hygiene, lease-epoch replay block, `50 B` WebAssembly spend-cap tripwire, `maker != checker` quorum, Cellular Sheaf tamper edge pinpointing, exact `2^K` Shapley micro-unit conservation, and Rust policy-escrow contract checks.

2. **Do**: Compile and run the Rust policy-escrow state machine test suite:
   ```bash
   cargo test --manifest-path contracts/near_policy_escrow/Cargo.toml
   ```
   **See**: `7 passed; 0 failed` across coalition conservation, `maker == checker` self-attestation block, ambiguous-clause & spend-cap gates, monotonic CAS lease-epoch fencing, Cellular Sheaf dispute hold + depositor refund, and C/WebAssembly `check_budget` ABI checks.

3. **Do**: Run all 4 end-to-end NEAR Swarm scenarios via CLI:
   ```bash
   python3 cli.py --scenario all
   ```
   **See**: Structured JSON showing:
   - `settle`: `"SETTLED_VIA_NEAR_INTENTS_AND_SHAPLEY"` (`net_micro_units: 2475000 == sum_allocated_micro_units: 2475000`, plus 3 `dry: true` NEAR Intents `nep141:wrap.near -> nep141:usdc.tether-token.near` quotes)
   - `ambiguous`: `"REJECTED_PRE_LOCK_AMBIGUOUS_CLAUSE"` (`["asap", "best effort"]` caught prior to escrow lock)
   - `tamper`: `"HELD_ON_SHEAF_OBSTRUCTION"` (`top_obstruction_edge: "relay->checker"`)
   - `runaway`: `"ABORTED_BY_WASM_SPEND_GUARDRAIL"` (`95,000,000 > 10,000,000` cap)

4. **Do**: Run the live zero-spend, zero-key NEAR network & Intents `1Click` check:
   ```bash
   python3 cli.py --live-readonly-check
   ```
   **See**: Live cross-chain asset metadata from `https://1click.chaindefuser.com/v0/tokens` (`230` supported assets across `nep141:wrap.near`, `nep141:usdc.tether-token.near`, etc.) alongside live block heights, protocol versions, and yoctoNEAR gas prices from public NEAR Mainnet (`rpc.mainnet.near.org`) and Testnet (`rpc.testnet.near.org`). A captured live response record is saved at `artifacts/live_near_readonly_probe.json`.

5. **Do**: Open `web/omninode-near-studio.html` in any browser.
   **See**: Live Paper & Ink (`#f5f2ea`, light-only) interactive studio instantiating the `50 B` WebAssembly budget policy gate in-browser across all 4 scenarios.

## Live NEAR AI Cloud TEE & NEAR Intents Quote Execution Mode

Set optional environment flags to enable live POST calls:
- `NEAR_AI_API_KEY=<key>` -> routes checker quorum prompts through `https://cloud-api.near.ai/v1/chat/completions`
- `NEAR_INTENTS_LIVE=1` -> posts `dry: true` exact-input quote envelopes to `https://1click.chaindefuser.com/v0/quote`

## License

MIT (`LICENSE`).
