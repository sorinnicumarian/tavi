# Diagnostic Temporal Rule Design

A diagnostic temporal rule is a rule designed not only to detect that a safety violation happened, but also to locate where the risky chain began.

Each rule should identify:

1. Trigger:
   The state change or action attempt that opens the risk.

2. Active interval:
   The period during which the risk or obligation remains active.

3. Resolution:
   The state change that safely closes the risk.

4. Violation condition:
   The condition that makes the rule fail.

5. Evidence:
   The trace atoms needed to report the trigger step, relevant interval, and violation step.

Prefer:
trigger -> safety condition until resolution
trigger -> response before done
trigger -> forbidden action while hazard holds

Avoid:
pure invariants, unless the hazard is truly instantaneous.