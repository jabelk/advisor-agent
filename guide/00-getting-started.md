# Lesson 0: Getting Started

## Objective

Set up your Salesforce sandbox environment and Claude Desktop so you're ready to learn CRM fundamentals hands-on.

## CRM Concept: The Practice Sandbox

Every major CRM platform offers a sandbox or trial environment where you can experiment without affecting real data. This is how professionals learn — you don't practice on live client records. A sandbox gives you the full CRM experience with synthetic data, so you can click around, make mistakes, and build confidence before touching anything that matters.

In your career, whether you're working in Salesforce, Schwab Advisor Center, or any other platform, always look for the training or sandbox environment first. It's the fastest way to learn.

## Prerequisites

None — this is the first lesson.

## Exercise: Connect to Your Sandbox

### Step 1: Log into the Salesforce Sandbox

Open your browser and navigate to your Salesforce developer sandbox. Use the credentials provided to you separately (never stored in this guide).

**What you should see**: The Salesforce Lightning home page with a navigation bar at the top showing tabs like Home, Contacts, Tasks, Reports, and Dashboards.

### Step 2: Find the Contacts Tab

Look for "Contacts" in the top navigation bar. If you don't see it, click the App Launcher (the grid icon, usually in the top-left area) and search for "Contacts."

**What you should see**: A list view of contacts. If the sandbox has been seeded, you should see synthetic client names — these are your practice clients.

### Step 3: Find a Specific Client

Browse through the contacts list and look for **Janet Morales** (or any client whose name you recognize). Click on her name to open her contact record, then click back to return to the list. These are synthetic clients generated specifically for learning — no real people, no real data.

**What you should see**: Approximately 50 contacts with names, emails, phone numbers, and other details. When you open Janet Morales' record, you should see fields like email, phone, and a description.

### Step 4: Set Up Claude Desktop as Your Tutor

Open Claude Desktop on your computer. It should already be connected to the advisor-agent MCP server. To use the guided tutor experience:

1. Open Claude Desktop's Projects feature
2. Create a new project (or open an existing one) and point it to the `guide/` folder in this repository
3. The `CLAUDE.md` file in this folder will automatically load, giving Claude the context to act as your Salesforce tutor

**What you should see**: When you start a new conversation in this project, Claude should be aware of the lesson curriculum and your MCP tools.

### Step 5: Verify Your Setup with Claude

This is the pattern you'll use throughout every lesson: do something in Salesforce, then ask Claude to verify.

**What you should see**: Claude responds with a list of clients from your sandbox, confirming the MCP connection works.

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
