# Lesson 5: Building Reports

## Objective

Learn how to build reports that aggregate and summarize client data — turning raw records into insights you can act on.

## CRM Concept: Reporting and Data Aggregation

While list views show you individual records that match criteria, reports summarize and aggregate data across your entire client base. A list view answers "which clients match this filter?" A report answers "what does my client base look like overall?"

Reports are where CRM data becomes business intelligence. An advisor might use reports to answer: "What's the total AUM across all my retirement-stage clients?" "How many clients have each risk tolerance level?" "What's my average client account value by life stage?" These insights inform how you allocate your time, plan outreach campaigns, and identify gaps in your book of business.

Every CRM has reporting capabilities, from simple tabular lists to complex dashboards with charts. The core skill is the same everywhere: define what data you want to see, set filters, choose how to group and summarize it, and save it for reuse.

## Prerequisites

- [x] Lesson 0: Getting Started
- [x] Lesson 1: Navigating Contacts
- [x] Lesson 3: Searching and Filtering Clients
- [x] Lesson 4: Creating List Views

## Exercise: Build a Client Summary Report

### Step 1: Navigate to Reports

Find the Reports tab in the Salesforce navigation bar. If it's not visible, use the App Launcher to search for "Reports."

**What you should see**: A reports landing page showing any existing reports and an option to create new ones.

### Step 2: Create a New Report

Start creating a new report. When prompted for a report type, choose "Contacts" or "Contacts & Accounts" — you want a report based on your client records.

**What you should see**: A report builder interface where you can add columns, filters, and groupings.

### Step 3: Configure the Report

Set up your report with these settings:
- **Columns**: Name, Email, Risk Tolerance (from Description or custom field), Life Stage, Account Value
- **Filter**: All contacts (no filter for now — you want the full picture)
- **Group By**: If the option is available, try grouping by a field like the first letter of Last Name, or leave ungrouped for a simple tabular view

Give the report a name: "Client Overview Report"

**What you should see**: A preview showing all ~50 clients in a table format with the columns you selected.

### Step 4: Add a Filter

Edit the report to add a filter. Try filtering to show only clients in the "growth" risk tolerance category.

Update the report name to "Growth Clients Report" (or save as a new report).

**What you should see**: The report narrows to show only growth-tolerance clients (roughly 35% of your ~50 clients).

### Step 5: Save the Report

Save the report. Salesforce will ask you to choose a folder — save it in "My Personal Reports" or any available folder.

Then navigate back to the Reports tab and confirm your saved report appears in the list.

**What you should see**: Your "Growth Clients Report" (or both reports, if you saved two) appears in the reports list and can be reopened with one click.

## Verify with Claude

Now let's check your work using Claude Desktop.

> **Ask Claude**: "Show me all reports in the sandbox."

**What to look for**: Claude uses `sandbox_show_reports` and your saved report(s) appear in the list. Check that the report name matches what you saved in Salesforce.

> **Ask Claude**: "Save a report called 'Retirement Stage Summary' that focuses on clients in the retirement life stage."

**What to look for**: Claude uses `sandbox_save_report` to create the report. Go back to Salesforce, navigate to Reports, and refresh — the new report should appear. Open it and confirm it shows retirement-stage clients.

## Key Takeaways

- **Reports answer "so what?"**: Contact records are facts. Reports turn facts into insights. "I have 50 clients" is data. "15 of my clients are pre-retirement with growth risk tolerance — they might need rebalancing conversations" is an insight.
- **Start simple, refine over time**: Your first report doesn't need to be complex. A simple list filtered by one criterion is already more powerful than scrolling through contacts manually. You can add groupings, charts, and multiple filters later.
- **Advisor tip**: Build a monthly "book of business" report that gives you a snapshot of your client base by key dimensions (life stage, risk tolerance, account value range). Review it at the start of each month to spot trends and prioritize your outreach. This is how top advisors stay proactive instead of reactive.

## Challenge

Try this on your own, then ask Claude to verify:

Build a report in Salesforce that answers this question: "How many clients do I have in each life stage (accumulation, pre-retirement, retirement, legacy)?" Save it as "Life Stage Distribution." Then compare your results with what Claude can tell you.

> **When you're done, ask Claude**: "Show me all reports. Can you also tell me how many clients are in each life stage — accumulation, pre-retirement, retirement, and legacy?"
