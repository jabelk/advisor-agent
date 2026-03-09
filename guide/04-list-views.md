# Lesson 4: Creating List Views

## Objective

Learn how to create and save custom list views — reusable filtered views of your client base that you can return to with one click.

## CRM Concept: Saved Views and Segments

In Lesson 3, you searched and filtered manually each time. List views (called "saved searches," "smart lists," or "segments" in other CRMs) let you save those filters so you don't have to rebuild them every time.

Think of a list view as a window into your client base with specific criteria baked in. An advisor might have list views like "High-Priority Follow-Ups," "Clients Approaching Retirement," or "New Clients This Quarter." Instead of running the same search repeatedly, you click the view name and instantly see the filtered list.

This is where CRM starts saving real time. A well-organized set of list views is like having a personal assistant who pre-sorts your client files every morning.

## Prerequisites

- [x] Lesson 0: Getting Started
- [x] Lesson 1: Navigating Contacts
- [x] Lesson 3: Searching and Filtering Clients

## Exercise: Build a Custom List View

### Step 1: See the Default List Views

Navigate to the Contacts tab. Look for a dropdown or selector near the top of the list — this lets you switch between different list views. Salesforce comes with some built-in views like "All Contacts," "Recently Viewed," and "My Contacts."

**What you should see**: A dropdown showing available list views, with "All Contacts" or similar as the default.

### Step 2: Create a New List View

Create a new list view. In Salesforce Lightning, look for a "New" option in the list view controls, or a gear icon with list view settings. Name your view:

- **List View Name**: "Pre-Retirement Clients"
- **Filter Criteria**: Filter to show only contacts whose Description contains "pre-retirement" or whose relevant field indicates the pre-retirement life stage
- **Visibility**: Only visible to you (private)

The exact filter setup depends on how the seed data stores life stage information — check the Description field or any custom fields.

**What you should see**: The list narrows to show only contacts in the pre-retirement segment (roughly 15 of your 50 clients).

### Step 3: Customize the Columns

Edit the list view to show the most useful columns for this segment. Good columns for a pre-retirement view might include:
- Name
- Phone
- Email
- Description (to see risk tolerance and goals)

Remove columns that aren't useful for this particular view.

**What you should see**: A clean, focused view showing only pre-retirement clients with the columns you care about.

### Step 4: Save and Switch Between Views

Save your new list view. Then switch back to "All Contacts" and switch again to "Pre-Retirement Clients" to confirm it persists.

**What you should see**: Your custom view appears in the list view dropdown and loads instantly when selected.

### Step 5: Create a Second List View

Create another list view:
- **List View Name**: "High-Value Clients"
- **Filter Criteria**: Filter for clients with account values above a threshold you choose (check what values exist in your seed data first)

**What you should see**: A second custom view in the dropdown, showing a different subset of your clients.

## Verify with Claude

Now let's check your work using Claude Desktop.

> **Ask Claude**: "Show me all list views in the sandbox."

**What to look for**: Claude uses `sandbox_show_listviews` and your two new list views — "Pre-Retirement Clients" and "High-Value Clients" — appear in the results along with any default Salesforce list views.

> **Ask Claude**: "Save a list view called 'Conservative Investors' that filters for clients with conservative risk tolerance."

**What to look for**: Claude uses `sandbox_save_listview` to create the view. Then go to Salesforce, refresh the Contacts tab, and check the list view dropdown — "Conservative Investors" should appear as a new option. This shows that list views created through Claude are real Salesforce list views.

## Key Takeaways

- **Saved views eliminate repetitive work**: Any filter you run more than twice should be a saved list view. The time investment (2 minutes to create) pays off every day.
- **Views are personal productivity tools**: In most CRMs, you can create private views just for yourself. Organize them by your workflow — "Monday Morning Calls," "Quarterly Review Candidates," "New Clients Needing Onboarding."
- **Advisor tip**: Start each work day by checking 2-3 key list views: clients with upcoming tasks, clients not contacted recently, and high-priority follow-ups. This 5-minute habit ensures nothing falls through the cracks.

## Challenge

Try this on your own, then ask Claude to verify:

Create a list view in Salesforce called "Aggressive Growth Clients" filtering for clients with aggressive risk tolerance. Then verify it exists through Claude and compare the client count to what you see in Salesforce.

> **When you're done, ask Claude**: "Show me all list views. Is 'Aggressive Growth Clients' there? How many clients would match aggressive risk tolerance?"
