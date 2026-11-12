//! NEAR Policy Escrow State Machine: Disjoint `maker != checker` Attestation,
//! Monotonic CAS Lease Fencing, Per-Call Spend Cap, Sheaf Dispute Hold, and Exact Coalition Split.

use std::collections::BTreeMap;

const BPS_DENOMINATOR: u128 = 10_000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EscrowStatus {
    Locked,
    Settled,
    HeldOnDispute { obstruction_edge: String },
    Refunded,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PolicyEscrowError {
    AmbiguousSpecification,
    StaleLeaseEpoch { expected: u64, current: u64 },
    ZeroEscrowDeposit,
    ExceedsFunctionCallSpendCap { requested: u128, max_allowed: u128 },
    MakerEqualsCheckerSelfAttestation,
    IntentNotFound,
    InvalidStateTransition,
    ZeroCoalitionRecipients,
    RecipientShareLengthMismatch,
    ArithmeticOverflow,
    NonConservingCoalitionSplit { sum_shares: u128, net_escrow: u128 },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransferAction {
    pub recipient_account: String,
    pub amount_yocto: u128,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SettlementOutcome {
    pub intent_id: String,
    pub fee_yocto: u128,
    pub net_yocto: u128,
    pub transfers: Vec<TransferAction>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IntentRecord {
    pub intent_id: String,
    pub fencing_epoch: u64,
    pub maker_account: String,
    pub checker_account: Option<String>,
    pub depositor_account: String,
    pub escrowed_yocto: u128,
    pub status: EscrowStatus,
    pub payouts: Vec<TransferAction>,
}

#[derive(Debug, Clone)]
pub struct PolicyEscrowContract {
    pub max_call_yocto: u128,
    pub platform_fee_bps: u16,
    pub lease_epochs: BTreeMap<String, u64>,
    pub intents: BTreeMap<String, IntentRecord>,
}

impl Default for PolicyEscrowContract {
    fn default() -> Self {
        Self {
            max_call_yocto: 10_000_000,
            platform_fee_bps: 100,
            lease_epochs: BTreeMap::new(),
            intents: BTreeMap::new(),
        }
    }
}

impl PolicyEscrowContract {
    pub fn new(max_call_yocto: u128, platform_fee_bps: u16) -> Self {
        assert!(
            u128::from(platform_fee_bps) <= BPS_DENOMINATOR,
            "platform_fee_bps must not exceed 10000"
        );
        Self {
            max_call_yocto,
            platform_fee_bps,
            lease_epochs: BTreeMap::new(),
            intents: BTreeMap::new(),
        }
    }

    /// Locks funds into escrow after checking unambiguous clause flag, CAS lease epoch, and spend cap.
    pub fn lock_intent(
        &mut self,
        intent_id: &str,
        expected_epoch: u64,
        maker_account: &str,
        depositor_account: &str,
        escrowed_yocto: u128,
        clause_unambiguous: bool,
    ) -> Result<u64, PolicyEscrowError> {
        if !clause_unambiguous {
            return Err(PolicyEscrowError::AmbiguousSpecification);
        }
        if escrowed_yocto == 0 {
            return Err(PolicyEscrowError::ZeroEscrowDeposit);
        }
        if escrowed_yocto > self.max_call_yocto {
            return Err(PolicyEscrowError::ExceedsFunctionCallSpendCap {
                requested: escrowed_yocto,
                max_allowed: self.max_call_yocto,
            });
        }

        let current_epoch = *self.lease_epochs.get(intent_id).unwrap_or(&0);
        if expected_epoch != current_epoch {
            return Err(PolicyEscrowError::StaleLeaseEpoch {
                expected: expected_epoch,
                current: current_epoch,
            });
        }
        if let Some(existing) = self.intents.get(intent_id) {
            if existing.status == EscrowStatus::Locked {
                return Err(PolicyEscrowError::InvalidStateTransition);
            }
        }

        let next_epoch = current_epoch
            .checked_add(1)
            .ok_or(PolicyEscrowError::ArithmeticOverflow)?;
        self.lease_epochs.insert(intent_id.to_string(), next_epoch);
        self.intents.insert(
            intent_id.to_string(),
            IntentRecord {
                intent_id: intent_id.to_string(),
                fencing_epoch: next_epoch,
                maker_account: maker_account.trim().to_string(),
                checker_account: None,
                depositor_account: depositor_account.trim().to_string(),
                escrowed_yocto,
                status: EscrowStatus::Locked,
                payouts: Vec::new(),
            },
        );
        Ok(next_epoch)
    }

    /// Places an active locked intent on hold when Cellular Sheaf audit detects a tampered edge.
    pub fn hold_on_sheaf_dispute(
        &mut self,
        intent_id: &str,
        caller_checker: &str,
        obstruction_edge: &str,
    ) -> Result<(), PolicyEscrowError> {
        let rec = self
            .intents
            .get_mut(intent_id)
            .ok_or(PolicyEscrowError::IntentNotFound)?;
        if rec.status != EscrowStatus::Locked {
            return Err(PolicyEscrowError::InvalidStateTransition);
        }
        if caller_checker.trim().eq_ignore_ascii_case(&rec.maker_account) {
            return Err(PolicyEscrowError::MakerEqualsCheckerSelfAttestation);
        }
        rec.checker_account = Some(caller_checker.trim().to_string());
        rec.status = EscrowStatus::HeldOnDispute {
            obstruction_edge: obstruction_edge.to_string(),
        };
        Ok(())
    }

    /// Refunds a dispute-held intent back to its original depositor.
    pub fn refund_held_intent(
        &mut self,
        intent_id: &str,
    ) -> Result<TransferAction, PolicyEscrowError> {
        let rec = self
            .intents
            .get_mut(intent_id)
            .ok_or(PolicyEscrowError::IntentNotFound)?;
        match rec.status {
            EscrowStatus::HeldOnDispute { .. } => {
                rec.status = EscrowStatus::Refunded;
                Ok(TransferAction {
                    recipient_account: rec.depositor_account.clone(),
                    amount_yocto: rec.escrowed_yocto,
                })
            }
            _ => Err(PolicyEscrowError::InvalidStateTransition),
        }
    }

    /// Enforces `maker_account != checker_account` and exact coalition payout conservation.
    pub fn attest_and_settle(
        &mut self,
        intent_id: &str,
        caller_checker: &str,
        recipients: Vec<String>,
        shares_yocto: Vec<u128>,
    ) -> Result<SettlementOutcome, PolicyEscrowError> {
        if recipients.is_empty() {
            return Err(PolicyEscrowError::ZeroCoalitionRecipients);
        }
        if recipients.len() != shares_yocto.len() {
            return Err(PolicyEscrowError::RecipientShareLengthMismatch);
        }

        let rec = self
            .intents
            .get_mut(intent_id)
            .ok_or(PolicyEscrowError::IntentNotFound)?;
        if rec.status != EscrowStatus::Locked {
            return Err(PolicyEscrowError::InvalidStateTransition);
        }
        if caller_checker.trim().eq_ignore_ascii_case(&rec.maker_account) {
            return Err(PolicyEscrowError::MakerEqualsCheckerSelfAttestation);
        }

        let fee_yocto = rec
            .escrowed_yocto
            .checked_mul(u128::from(self.platform_fee_bps))
            .ok_or(PolicyEscrowError::ArithmeticOverflow)?
            / BPS_DENOMINATOR;
        let net_yocto = rec
            .escrowed_yocto
            .checked_sub(fee_yocto)
            .ok_or(PolicyEscrowError::ArithmeticOverflow)?;

        let mut total_shares: u128 = 0;
        for share in &shares_yocto {
            total_shares = total_shares
                .checked_add(*share)
                .ok_or(PolicyEscrowError::ArithmeticOverflow)?;
        }
        if total_shares != net_yocto {
            return Err(PolicyEscrowError::NonConservingCoalitionSplit {
                sum_shares: total_shares,
                net_escrow: net_yocto,
            });
        }

        let mut transfers = Vec::with_capacity(recipients.len());
        for (acct, amt) in recipients.into_iter().zip(shares_yocto.into_iter()) {
            if amt > 0 {
                transfers.push(TransferAction {
                    recipient_account: acct,
                    amount_yocto: amt,
                });
            }
        }

        rec.checker_account = Some(caller_checker.trim().to_string());
        rec.status = EscrowStatus::Settled;
        rec.payouts = transfers.clone();

        Ok(SettlementOutcome {
            intent_id: intent_id.to_string(),
            fee_yocto,
            net_yocto,
            transfers,
        })
    }
}

/// C/WebAssembly ABI spend-cap check aligned with the 50-byte Function-Call Access Key guardrail.
#[no_mangle]
pub extern "C" fn check_budget(requested_micro_units: u64, max_call_micro_units: u64) -> i32 {
    if requested_micro_units <= max_call_micro_units {
        1
    } else {
        0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn settles_valid_coalition_with_exact_conservation() {
        let mut contract = PolicyEscrowContract::new(10_000_000, 100);
        let epoch = contract
            .lock_intent(
                "near-intent-001",
                0,
                "maker-agent.testnet",
                "treasury.testnet",
                2_500_000,
                true,
            )
            .expect("lock should succeed");
        assert_eq!(epoch, 1);

        // 1% fee on 2,500,000 = 25,000; net = 2,475,000
        let outcome = contract
            .attest_and_settle(
                "near-intent-001",
                "checker-guard.testnet",
                vec![
                    "planner-node.testnet".to_string(),
                    "maker-agent.testnet".to_string(),
                    "checker-guard.testnet".to_string(),
                ],
                vec![800_000, 925_000, 750_000],
            )
            .expect("disjoint checker settlement should succeed");

        assert_eq!(outcome.fee_yocto, 25_000);
        assert_eq!(outcome.net_yocto, 2_475_000);
        let paid: u128 = outcome.transfers.iter().map(|t| t.amount_yocto).sum();
        assert_eq!(paid, outcome.net_yocto);
        assert_eq!(
            contract.intents["near-intent-001"].status,
            EscrowStatus::Settled
        );
    }

    #[test]
    fn blocks_maker_equals_checker_self_attestation() {
        let mut contract = PolicyEscrowContract::new(10_000_000, 100);
        contract
            .lock_intent(
                "intent-self",
                0,
                "Same-Agent.testnet",
                "treasury.testnet",
                1_000_000,
                true,
            )
            .unwrap();

        let err = contract
            .attest_and_settle(
                "intent-self",
                "same-agent.testnet",
                vec!["same-agent.testnet".to_string()],
                vec![990_000],
            )
            .unwrap_err();
        assert_eq!(err, PolicyEscrowError::MakerEqualsCheckerSelfAttestation);
    }

    #[test]
    fn blocks_ambiguous_clause_and_spend_cap_overrun() {
        let mut contract = PolicyEscrowContract::new(10_000_000, 100);
        assert_eq!(
            contract.lock_intent("i-amb", 0, "m.near", "d.near", 500_000, false),
            Err(PolicyEscrowError::AmbiguousSpecification)
        );
        assert_eq!(
            contract.lock_intent("i-cap", 0, "m.near", "d.near", 95_000_000, true),
            Err(PolicyEscrowError::ExceedsFunctionCallSpendCap {
                requested: 95_000_000,
                max_allowed: 10_000_000,
            })
        );
    }

    #[test]
    fn enforces_monotonic_cas_lease_epoch_against_replay() {
        let mut contract = PolicyEscrowContract::new(10_000_000, 0);
        contract
            .lock_intent("i-epoch", 0, "maker.near", "dep.near", 1_000, true)
            .unwrap();
        assert_eq!(
            contract.lock_intent("i-epoch", 0, "maker.near", "dep.near", 1_000, true),
            Err(PolicyEscrowError::StaleLeaseEpoch {
                expected: 0,
                current: 1,
            })
        );
    }

    #[test]
    fn rejects_non_conserving_split_and_double_settle() {
        let mut contract = PolicyEscrowContract::new(10_000_000, 100);
        contract
            .lock_intent("i-conservation", 0, "maker.near", "dep.near", 1_000_000, true)
            .unwrap();

        let bad_split = contract
            .attest_and_settle(
                "i-conservation",
                "checker.near",
                vec!["maker.near".to_string(), "checker.near".to_string()],
                vec![500_000, 489_999],
            )
            .unwrap_err();
        assert_eq!(
            bad_split,
            PolicyEscrowError::NonConservingCoalitionSplit {
                sum_shares: 989_999,
                net_escrow: 990_000,
            }
        );

        contract
            .attest_and_settle(
                "i-conservation",
                "checker.near",
                vec!["maker.near".to_string(), "checker.near".to_string()],
                vec![500_000, 490_000],
            )
            .unwrap();

        let replay = contract
            .attest_and_settle(
                "i-conservation",
                "checker.near",
                vec!["maker.near".to_string(), "checker.near".to_string()],
                vec![500_000, 490_000],
            )
            .unwrap_err();
        assert_eq!(replay, PolicyEscrowError::InvalidStateTransition);
    }

    #[test]
    fn holds_on_sheaf_dispute_and_refunds_depositor() {
        let mut contract = PolicyEscrowContract::new(10_000_000, 100);
        contract
            .lock_intent("i-sheaf", 0, "maker.near", "depositor.near", 3_000_000, true)
            .unwrap();

        assert_eq!(
            contract.hold_on_sheaf_dispute("i-sheaf", "maker.near", "relay->checker"),
            Err(PolicyEscrowError::MakerEqualsCheckerSelfAttestation)
        );

        contract
            .hold_on_sheaf_dispute("i-sheaf", "checker.near", "relay->checker")
            .unwrap();
        assert_eq!(
            contract.intents["i-sheaf"].status,
            EscrowStatus::HeldOnDispute {
                obstruction_edge: "relay->checker".to_string()
            }
        );

        let refund = contract.refund_held_intent("i-sheaf").unwrap();
        assert_eq!(refund.recipient_account, "depositor.near");
        assert_eq!(refund.amount_yocto, 3_000_000);
        assert_eq!(contract.intents["i-sheaf"].status, EscrowStatus::Refunded);
    }

    #[test]
    fn wasm_abi_check_budget_matches_policy_boundary() {
        assert_eq!(check_budget(2_500_000, 10_000_000), 1);
        assert_eq!(check_budget(10_000_000, 10_000_000), 1);
        assert_eq!(check_budget(10_000_001, 10_000_000), 0);
    }
}
