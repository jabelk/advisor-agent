# Contract: Lesson Template

Every lesson file MUST follow this structure. Sections are in order and all are required.

## Template

```markdown
# Lesson N: [Title]

## Objective

[One sentence: what Jordan will learn and be able to do after this lesson]

## CRM Concept: [Concept Name]

[2-3 paragraphs explaining the universal CRM concept — what it is, why every CRM has it,
and how financial advisors use it day-to-day. NOT Salesforce-specific.]

## Prerequisites

- [x] Lesson X: [Title]
- [x] Lesson Y: [Title]
(or "None — this is the first lesson" for Lesson 0/1)

## Exercise: [Exercise Title]

### Step 1: [Action]

[Clear instruction describing what to do in Salesforce. Reference specific seed data
clients by name. Describe actions by concept, not by exact UI element location.]

**What you should see**: [Description of expected result]

### Step 2: [Action]

[Next step...]

**What you should see**: [Expected result]

(Continue for 3-6 steps per exercise)

## Verify with Claude

Now let's check your work using Claude Desktop.

> **Ask Claude**: "[Exact prompt to type in Claude Desktop]"

**What to look for**: [What the MCP tool output should show that confirms success]

> **Ask Claude**: "[Second verification prompt if needed]"

**What to look for**: [Expected confirmation]

## Key Takeaways

- **[Concept]**: [How this transfers to any CRM, not just Salesforce]
- **[Concept]**: [Another transferable insight]
- **Advisor tip**: [How this applies to Jordan's day-to-day work]

## Challenge

Try this on your own, then ask Claude to verify:

[Unguided exercise description. Should use a different client or scenario than the
main exercise. Should combine skills from this lesson.]

> **When you're done, ask Claude**: "[Verification prompt for the challenge]"
```

## Validation Rules

- Lesson number MUST be sequential (00, 01, 02, 03, 04, 05)
- Objective MUST be one sentence
- CRM Concept MUST NOT mention Salesforce-specific UI elements
- Exercise steps MUST reference seed data clients by name
- "Verify with Claude" MUST include exact prompts Jordan can copy-paste
- Key Takeaways MUST include at least one "Advisor tip" relevant to financial consulting
- Challenge MUST use different data/scenario than the main exercise
