// NEAR Smart Contract Specification: Disjoint Maker-Checker Policy Escrow & Exact Coalition Settlement
use near_sdk::borsh::{BorshDeserialize, BorshSerialize};
use near_sdk::{env, near, AccountId, NearToken, Promise};

#[derive(BorshDeserialize, BorshSerialize, Clone)]
pub struct IntentRecord {
    pub intent_id: String,
    pub maker_account: AccountId,
    pub checker_account: Option<AccountId>,
    pub escrowed_yocto: u128,
    pub settled: bool,
}

#[near(contract_state)]
#[derive(Default)]
pub struct PolicyEscrowContract {
    pub max_call_yocto: u128,
}

#[near]
impl PolicyEscrowContract {
    #[init]
    pub fn new(max_call_yocto: u128) -> Self {
        Self { max_call_yocto }
    }

    /// Enforces `maker_account != checker_account` and exact coalition payout conservation.
    pub fn attest_and_settle(
        &mut self,
        maker_account: AccountId,
        escrowed_yocto: u128,
        recipients: Vec<AccountId>,
        shares_yocto: Vec<u128>,
    ) {
        let caller = env::predecessor_account_id();
        assert_ne!(caller, maker_account, "Self-attestation blocked: maker == checker");
        assert!(escrowed_yocto <= self.max_call_yocto, "Exceeds function-call spend cap");
        assert_eq!(recipients.len(), shares_yocto.len(), "Recipient/share length mismatch");

        let total_out: u128 = shares_yocto.iter().copied().sum();
        assert_eq!(total_out, escrowed_yocto, "Coalition shares must sum exactly to escrow");

        for (acct, amt) in recipients.into_iter().zip(shares_yocto.into_iter()) {
            if amt > 0 {
                let _ = Promise::new(acct).transfer(NearToken::from_yoctonear(amt));
            }
        }
    }
}
