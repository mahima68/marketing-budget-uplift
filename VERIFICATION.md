# Verification

- All 12 notebook code cells executed successfully, without error outputs.
- Notebook schema validated; charts are embedded for offline reading.
- Full-source SHA-256 matches the publisher's file identity.
- Split indices cover the sample exactly once without overlap.
- Targeting policies respect the 20% audience capacity.
- Independent simulated randomized experiment verifies that uplift targeting can outperform likely-buyer targeting and that the policy-gain scale is correct.
- Confidence interval ordering and one validation-selected winner checked.
- All scenario net-contribution calculations reconciled to the measured gain table and stated assumptions.

These checks validate the implementation, not real-world causal validity or profitability.

## App and API verification

- 12 API tests passed, including invalid inputs, all 60 evaluated strategy/capacity combinations, audience scaling, and zero-margin economics.
- Browser scenario arithmetic independently reconciled against all 60 result combinations.
- Browser checks confirmed initial results, changing margin, changing strategy and capacity, and reset behavior. A reset naming conflict was found and fixed before publication.
- Dashboard visually inspected at a narrow viewport.
- JavaScript syntax check passed.
- Docker configuration supplied; container execution has not been verified in this environment.
