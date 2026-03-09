# Lesson 0: Getting Started

## Objective

Set up your Salesforce sandbox environment and Claude Desktop so you're ready to learn CRM fundamentals hands-on.

## CRM Concept: The Practice Sandbox

Every major CRM platform offers a sandbox or trial environment where you can experiment without affecting real data. This is how professionals learn — you don't practice on live client records. A sandbox gives you the full CRM experience with synthetic data, so you can click around, make mistakes, and build confidence before touching anything that matters.

In your career, whether you're working in Salesforce, Schwab Advisor Center, or any other platform, always look for the training or sandbox environment first. It's the fastest way to learn.

## Prerequisites

None — this is the first lesson.

## Part 1: Install Claude Desktop

**If you haven't set up Claude Desktop yet**, follow the **[Claude Desktop Setup Guide](setup-claude-desktop.md)** first. It covers downloading the app, connecting it to Salesforce, and optionally setting up the tutor project.

Come back here once Claude Desktop is installed and you can see the hammer icon (tools) in the chat input area.

## Part 2: Log Into Salesforce

### Step 4: Open the Salesforce Sandbox

Open your browser and navigate to the Salesforce sandbox URL I sent you. Log in with the credentials I provided (keep those private — don't share them or save them anywhere public).

**What you should see**: The Salesforce Lightning home page with a navigation bar at the top showing tabs like Home, Contacts, Tasks, Reports, and Dashboards.

### Step 5: Find the Contacts Tab

Look for "Contacts" in the top navigation bar. If you don't see it, click the App Launcher (the grid icon, usually in the top-left area) and search for "Contacts."

**What you should see**: A list view of contacts — these are synthetic (fake) client profiles for you to practice with. No real people.

### Step 6: Find a Specific Client

Browse through the contacts list and look for **Janet Morales** (or any client whose name you recognize). Click on her name to open her contact record, then click back to return to the list.

**What you should see**: Approximately 50 contacts with names, emails, phone numbers, and other details. When you open Janet Morales' record, you should see fields like email, phone, and a description.

## Part 3: Set Up the Claude Tutor (Optional — Do This Later)

You can skip this part for now and come back after you've done a couple lessons. See **Step 4** in the **[Claude Desktop Setup Guide](setup-claude-desktop.md)** for instructions on setting up the tutor project.

## Verify with Claude

Now let's check your work using Claude Desktop.

> **Ask Claude**: "How many clients are in my Salesforce sandbox?"

**What to look for**: Claude should use the `sandbox_list_clients` tool and report approximately 50 clients. If Claude can't connect, check that your MCP server is running and Claude Desktop is configured correctly.

> **Ask Claude**: "List the first 5 clients in the sandbox."

**What to look for**: Claude returns 5 client names with basic details. Write down 2-3 of these names — you'll use them in upcoming lessons. One client you'll see referenced in exercises is **Janet Morales** (if she's in your sandbox). If your sandbox has different names, just substitute any client name where the lessons mention a specific person.

## Resetting Your Sandbox Data

If your sandbox is empty or the data looks wrong, you can ask Claude to re-seed it:

> **Ask Claude**: "Please re-seed the sandbox with fresh client data."

Claude will use the `sandbox_seed_clients` tool to generate 50 new synthetic clients. Note that re-seeding creates new random names, so specific names mentioned in later lessons may differ from what you see — just substitute any client from your list.

## Key Takeaways

- **Practice environments exist everywhere**: Salesforce has sandboxes, Schwab has training modes, and most enterprise tools offer safe practice spaces. Always learn there first.
- **Verify with a second source**: The "do it manually, then check with Claude" pattern isn't just for learning — in practice, cross-checking your work against a second data source catches errors early.
- **Advisor tip**: When you start using any new CRM tool at work, your first step should always be finding the training or sandbox environment. The 30 minutes you spend setting up a practice space saves hours of anxiety about breaking real data.

## Challenge

Try this on your own, then ask Claude to verify:

Explore the Salesforce navigation bar and find three different sections beyond Contacts (for example: Tasks, Reports, Dashboards, or Accounts). Write down what you think each section is for based on its name alone.

> **When you're done, ask Claude**: "I found these sections in Salesforce: [list your three sections]. Can you explain what each one is used for in a CRM?"
