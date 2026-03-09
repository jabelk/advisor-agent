# Lesson 3: Searching and Filtering Clients

## Objective

Learn how to find specific clients and filter your client base by criteria — the skill that turns a CRM from a digital Rolodex into a strategic tool.

## CRM Concept: Search and Segmentation

Every CRM lets you search for individual clients and filter groups by shared characteristics. This matters because advisors don't treat all clients the same — a pre-retiree with aggressive risk tolerance needs different attention than a young accumulator with conservative goals.

Searching finds one person. Filtering finds a group that shares something in common. Together, they let you answer questions like "Who hasn't been contacted in 90 days?" or "Which clients have over $500K and are approaching retirement?" These questions drive proactive outreach — the hallmark of a great advisor.

In any CRM, mastering search and filter is what separates advisors who react to client requests from advisors who anticipate client needs.

## Prerequisites

- [x] Lesson 0: Getting Started
- [x] Lesson 1: Navigating Contacts

## Exercise: Find and Filter Clients

### Step 1: Use Global Search

Find the search bar at the top of Salesforce (it's typically always visible in the header). Type "Janet Morales" and press Enter.

**What you should see**: Search results showing Janet Morales as a Contact, possibly along with related records like tasks or activities you created in Lesson 2.

### Step 2: Search by Partial Name

Clear the search bar and type just "Morales" (or just the last name of any client in your sandbox). Press Enter.

**What you should see**: All contacts with that last name appear. Global search is flexible — it matches partial names, emails, and other text fields.

### Step 3: Filter the Contacts List View

Go to the Contacts tab. Look for a filter option on the list view — in Salesforce Lightning, you can click on column headers to sort, or use the list view controls to add filters.

Try filtering or sorting contacts by one of these approaches:
- Click a column header (like "Name") to sort alphabetically
- If filter controls are available, try filtering by a field value

**What you should see**: The contacts list reorders or narrows based on your sort/filter criteria.

### Step 4: Explore the Description Field

Open 3-4 different contacts and look at their Description field (or Notes). Some clients have preferences noted, like "Prefers email communication" or "Interested in ESG investing."

Write down any patterns you notice — these descriptions are the kind of information that powers targeted outreach.

**What you should see**: Some contacts have descriptions with communication preferences, investment interests, or other notes. Some may have no description at all.

### Step 5: Try a Targeted Search

Think of a question an advisor might ask: "Which of my clients are interested in retirement planning?" Try using the global search with terms like "retirement" to see if any results come up.

**What you should see**: Search results may include contacts whose descriptions mention retirement, or tasks/activities with retirement-related subjects.

## Verify with Claude

Now let's check your work using Claude Desktop.

> **Ask Claude**: "Search for clients with the last name Morales."

**What to look for**: Claude uses `sandbox_search_clients` and returns any clients matching "Morales." Compare with your Salesforce search results from Step 2.

> **Ask Claude**: "Show me all clients who have a conservative risk tolerance."

**What to look for**: Claude uses `sandbox_query_clients` to filter by risk tolerance. You should see a subset of clients (roughly 15% of the ~50 total). This is the kind of segmentation that powers targeted outreach — something that would take much longer to do manually in the UI.

## Key Takeaways

- **Search finds individuals, filters find segments**: Both are essential. Search for "John Smith" before a call. Filter for "all high-net-worth pre-retirees" when planning a quarterly outreach campaign.
- **CRM data quality drives search quality**: If contact records are incomplete (missing descriptions, wrong risk tolerances), your searches and filters give bad results. Good data hygiene is part of the job.
- **Advisor tip**: Once a week, try a new filter on your client base. "Who has a birthday this month?" "Who hasn't been contacted in 60 days?" "Which growth-tolerance clients might be interested in new market opportunities?" This habit turns your CRM into a prospecting engine.

## Challenge

Try this on your own, then ask Claude to verify:

Use Claude to find all clients in the "retirement" life stage. Then pick one of those clients and look them up manually in Salesforce. Compare what Claude reports against what you see in their contact record.

> **When you're done, ask Claude**: "Find all clients in the retirement life stage. How many are there, and what's the range of their account values?"
