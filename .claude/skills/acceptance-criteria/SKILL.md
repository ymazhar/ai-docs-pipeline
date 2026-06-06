---
name: acceptance-criteria
description: Write, review, or refine acceptance criteria for a feature, task, or user story. Use when defining "done", turning a requirement into testable criteria, choosing between checklist vs Given/When/Then scenarios, classifying hard vs soft errors, specifying prohibitions, or verifying that tests and AC are losslessly convertible in both directions.
---

# Acceptance Criteria Template (Given / When / Then)

> AC is a **contract** between all parties involved in development (manager, developer, QA, AI, user):
> an unambiguous definition of **when the work can be considered done**.
>
> The key quality metric for AC: tests can be **compiled** from them, and AC can be **reconstructed** from tests
> (lossless, two-way conversion).

---

## Which format to use

| Format                               | When to use                                             |
|--------------------------------------|---------------------------------------------------------|
| **Checklist**                        | simple low-level tasks with few, obvious rules          |
| **Scenario-based (Given/When/Then)** | features, modules, subsystems, any non-trivial behavior |

---

## Format 1 — Scenario-based

### Structure of a single scenario

```
Scenario: <short name — what we are verifying>

  Given <precondition: system state / scope of the rule>
    And <additional precondition, if needed>
  When  <action that triggers the behavior>
  Then  <expected result — observable, verifiable>
    And <additional result / side effect>
```

- **Given** — the scope of the task: under what conditions the rule applies at all (who, from where, in what state).
- **When** — the specific action.
- **Then** — a result that can be verified automatically (HTTP status, message, DB state, event).

### Example (password reset)

```
Scenario: Password reset via a link valid for 30 minutes

  Given a registered user with email "user@example.com"
    And the user is on the login page
  When  the user requests a password reset for their email
  Then  the system sends an email containing a reset link with a token
    And the link is valid for exactly 30 minutes

Scenario: Expired reset link is rejected

  Given the user received a password reset link
    And 31 minutes have passed since the link was issued
  When  the user opens the link and tries to set a new password
  Then  the system returns a 400 error (link expired)
    And the password is not changed
```

> ⚠️ Common AI pitfall: "the email expires in 30 min". It is not the email that expires, but the **link with the token**.
> State the subject of the rule explicitly.

---

## Format 2 — Checklist

For simple tasks where a scenario would be overkill:

```
## <Task name>

- [ ] <verifiable statement>
- [ ] field X is required, format: <regex / rule>
- [ ] "Sign in" button is enabled ⇔ both fields (login, password) are filled
- [ ] password is masked with asterisks
- [ ] an invalid email shows the message "<exact text>"
```

---

## Mandatory sections for any AC

### 1. Preconditions (scope)

Who, in what state, from where. _("only a registered user", "only from the login page".)_

### 2. Dependencies between fields

Describe relationships explicitly:

```
- If the person has a child → the child's certificate number is required.
- If there is a registered address → the address is required. Otherwise the address may be empty.
```

### 3. Error classification (critical for AI)

| Type                      | Allowed?                                  | Example                                     |
|---------------------------|-------------------------------------------|---------------------------------------------|
| **Hard / system**         | NO, must not occur                        | crash, data loss, protocol error            |
| **Soft / business logic** | YES, must occur and be handled gracefully | invalid address format → validation message |

> If you tell the AI "there must be no errors" without this distinction, it will strip out the **needed** validation checks.

### 4. Prohibitions (negative criteria)

Not only what the system does, but also what it **must not** do:

```
- An unregistered user MUST NOT be able to request a password reset.
- An expired token MUST NOT allow changing the password.
```

### 5. References to shared requirements

Do not duplicate in every AC. Extract into shared project documentation and reference it:

```
Password and security requirements: see docs/architecture/security.md
```

---

## AC quality checklist

- [ ] The **scope** (Given) is clearly stated — when the rule applies.
- [ ] The result (Then) is **verifiable** (status/message/state), not "convenient / fast".
- [ ] Hard and soft errors are **distinguished**.
- [ ] **Prohibitions** are described, not just permissions.
- [ ] Field dependencies are stated explicitly.
- [ ] Shared requirements are extracted and linked, not duplicated.
- [ ] Tests can be generated from the AC, and the same AC can be reconstructed from the tests.

---

## Verifying via two-way conversion

1. Take tests written **against a user story** (not arbitrary unit/integration tests).
2. Use the AI to reconstruct AC from them.
3. In a **fresh context** (so the AI does not remember) — generate tests from those AC.
4. Compare: the tests should match.
5. A mismatch → either the tests were unclear, or the AC do not extract cleanly. Iterate until conversion is stable in both directions.

> Why: humans share an implicit context (team, culture, onboarding).
> The AI has none — the project's text documents **replace onboarding** for it.

---

## Blank template to copy

```
Feature: <feature name>

Scenario: <scenario name>
  Given <precondition>
    And <...>
  When  <action>
  Then  <verifiable result>
    And <...>

# Prohibitions
- <what the system must not do>

# Errors
- hard (not allowed): <...>
- soft (expected): <...>

# Shared requirements
- see <link to document>
```