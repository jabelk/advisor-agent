# Lesson 2: Creating and Managing Tasks

## Objective

Learn how to create follow-up tasks for clients and track your to-do list — the system that keeps client relationships from falling through the cracks.

## CRM Concept: Activity Tracking

Every CRM has a task or activity system. This is how advisors track what needs to happen next for each client — follow-up calls, document requests, annual reviews, birthday outreach. Without it, you're relying on memory or sticky notes, which doesn't scale past a handful of clients.

Tasks in a CRM are different from your personal to-do list. CRM tasks are linked to a specific contact, have due dates, and create a history. When you open a client's record six months from now, you can see every task that was created, completed, or missed. This history tells a story about the relationship.

For financial advisors managing 100+ client relationships, a disciplined task system is the difference between proactive service ("I'm calling because your annual review is coming up") and reactive scrambling ("Sorry I missed your review deadline").

## Prerequisites

- [x] Lesson 0: Getting Started
- [x] Lesson 1: Navigating Contacts

## Exercise: Create a Follow-Up Task

### Step 1: Navigate to Janet Morales' Contact Record

Open the Contacts tab and find Janet Morales (or your substitute client). Click to open her detail page.

**What you should see**: Janet's contact detail page with her information.

### Step 2: Find the Activity or Task Section

On the contact detail page, look for a section related to activities, tasks, or the activity timeline. In Salesforce Lightning, this is typically below the contact details, in a tab labeled "Activity" or "Related."

**What you should see**: A section showing past activities (if any) and an option to create new tasks.

### Step 3: Create a New Task

Create a new task with these details:
- **Subject**: "Annual portfolio review call"
- **Due Date**: One week from today
- **Priority**: High
- **Status**: Not Started

Link it to Janet Morales if it isn't automatically associated.

**What you should see**: A confirmation that the task was created, and it appears in Janet's activity timeline.

### Step 4: Create a Second Task

Create another task for Janet:
- **Subject**: "Send retirement planning brochure"
- **Due Date**: Two weeks from today
- **Priority**: Normal
- **Status**: Not Started

**What you should see**: Both tasks now appear in Janet's activity section, with the earlier due date first.

### Step 5: Check Your Task List

Navigate to the Tasks tab (find it in the navigation bar or App Launcher). This shows all your tasks across all clients.

**What you should see**: Your two new tasks for Janet Morales appear in the task list, along with any other tasks that existed previously.

## Verify with Claude

Now let's check your work using Claude Desktop.

> **Ask Claude**: "Show me all open tasks."

**What to look for**: Claude uses `sandbox_show_tasks` and your two newly created tasks appear in the list — "Annual portfolio review call" and "Send retirement planning brochure," both linked to Janet Morales. Check that the due dates and priorities match what you entered.

> **Ask Claude**: "Create a task for Janet Morales: Schedule Q2 financial checkup, due in 3 weeks, normal priority."

**What to look for**: Claude uses `sandbox_create_task` to create the task. Now go back to Salesforce, refresh Janet's page, and confirm the new task appears in her activity timeline. This demonstrates the two-way connection: you can create tasks in Salesforce or through Claude, and both show up in the same place.

## Key Takeaways

- **Tasks keep relationships alive**: Every client interaction should end with a next step captured as a task. "I'll follow up next week" means nothing without a task to remind you.
- **Linked tasks tell a story**: CRM tasks aren't just reminders — they create a record of your service history. This matters for compliance, handoffs to colleagues, and your own review of client relationships.
- **Advisor tip**: Build a habit of creating a task immediately after every client call or meeting. It takes 10 seconds and prevents the most common advisor mistake: promising a follow-up and forgetting.

## Challenge

Try this on your own, then ask Claude to verify:

Pick a different client (not Janet Morales). Create two tasks for them: one high-priority task due this week and one normal-priority task due next month. Then verify both tasks exist using Claude.

> **When you're done, ask Claude**: "Show me all open tasks. Do you see the two tasks I just created for [client name]?"
