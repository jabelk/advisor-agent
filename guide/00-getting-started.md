# Lesson 0: Getting Started

## Objective

Set up your Salesforce sandbox environment and Claude Desktop so you're ready to learn CRM fundamentals hands-on.

## CRM Concept: The Practice Sandbox

Every major CRM platform offers a sandbox or trial environment where you can experiment without affecting real data. This is how professionals learn — you don't practice on live client records. A sandbox gives you the full CRM experience with synthetic data, so you can click around, make mistakes, and build confidence before touching anything that matters.

In your career, whether you're working in Salesforce, Schwab Advisor Center, or any other platform, always look for the training or sandbox environment first. It's the fastest way to learn.

## Prerequisites

None — this is the first lesson.

## Part 1: Install Claude Desktop

Claude Desktop is an app made by Anthropic (the company behind Claude). It's like ChatGPT but runs as a desktop app and can connect to external tools — in our case, it connects to your Salesforce sandbox so you can ask it to look up clients, verify your work, etc.

### Step 1: Download Claude Desktop

Go to **https://claude.ai/download** and download the version for your computer (Mac or Windows). Install it like any other app.

**What you should see**: Claude Desktop opens and asks you to sign in or create an account.

### Step 2: Sign In

Create an Anthropic account (or sign in if you already have one). You can sign up with your email — it's free to start.

**What you should see**: The Claude Desktop chat interface, similar to ChatGPT but as a standalone app on your computer.

### Step 3: Connect to the Salesforce Tools

This is the step that makes Claude "smart" about your Salesforce sandbox. I'll send you a configuration snippet separately — you'll paste it into Claude Desktop's settings under **Settings > MCP Servers**. This tells Claude how to talk to the Salesforce sandbox.

If you get stuck on this step, just message me and I'll walk you through it.

**What you should see**: After restarting Claude Desktop, you should see a hammer icon (tools) in the chat input area, indicating MCP tools are connected.

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

## Part 3: Set Up the Claude Tutor

This part is optional but recommended — it turns Claude into a Salesforce tutor that knows the lesson plan and can guide you through exercises.

### Step 7: Download the Guide Files

You need the lesson files on your computer. The easiest way:

1. Go to **https://github.com/jabelk/advisor-agent**
2. Click the green **"Code"** button near the top right
3. Click **"Download ZIP"**
4. Unzip the downloaded file somewhere you'll remember (like your Desktop or Documents folder)
5. Inside the unzipped folder, find the **`guide/`** folder — that's what you need

### Step 8: Create a Claude Desktop Project

A "Project" in Claude Desktop is like a workspace with persistent context. Here's how to set one up:

1. Open Claude Desktop
2. In the left sidebar, look for **"Projects"** and click it
3. Click **"Create Project"** (or the **+** button)
4. Give it a name like **"Salesforce Learning"**
5. Under project settings, look for an option to **add files** or **set a folder** — point it to the `guide/` folder you downloaded in Step 7
6. The `CLAUDE.md` file inside that folder will automatically load, which gives Claude the tutor instructions

**What you should see**: When you start a new conversation in this project, Claude knows about the lesson curriculum and can guide you.

### Step 9: Verify Everything Works

This is the pattern you'll use throughout every lesson: do something in Salesforce, then ask Claude to check it.

**What you should see**: Claude responds with information from your sandbox, confirming everything is connected.

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
