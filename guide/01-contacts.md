# Lesson 1: Navigating Contacts

## Objective

Learn how to find, open, and read a client's contact record — the foundation of every CRM interaction.

## CRM Concept: The Contact Record

In every CRM, the contact record is the central hub for a client relationship. Think of it as a digital version of the client file folder that financial advisors have used for decades — except it's searchable, shareable, and always up to date.

A contact record typically stores who the person is (name, phone, email), where they are in their financial journey (life stage, risk tolerance, account value), and what's happened in the relationship (notes, meeting history, follow-ups). Every CRM organizes these slightly differently, but the concept is universal.

As a financial advisor, you'll open contact records dozens of times a day — before calls, during meetings, and when preparing follow-ups. Getting comfortable navigating them quickly is the single most important CRM skill you can build.

## Prerequisites

- [x] Lesson 0: Getting Started

## Exercise: Explore a Client Profile

### Step 1: Open the Contacts List

Navigate to the Contacts tab in Salesforce. You should see a list of your synthetic clients.

**What you should see**: A table showing client names, with columns for details like email, phone, and account information.

### Step 2: Find Janet Morales

Use the contacts list to locate Janet Morales. You can scroll through the list or use the alphabetical filter along the top. (If Janet Morales isn't in your sandbox, pick any client and substitute their name throughout this exercise.)

**What you should see**: Janet Morales appears in the list with a clickable name.

### Step 3: Open the Contact Detail Page

Click on Janet Morales' name to open her full contact record.

**What you should see**: A detail page showing fields like:
- **Name**: Janet Morales
- **Email**: An @example.com address
- **Phone**: A 555-xxx-xxxx number
- **Description**: May include notes about communication preferences or investment interests
- Other fields like account value, risk tolerance, and life stage

### Step 4: Identify Key Fields

Look through the contact record and identify these five pieces of information:
1. Her full name
2. Her email address
3. Her phone number
4. Any notes or description text
5. Her risk tolerance or investment goals (check the Description field or custom fields)

Write these down — you'll compare them with Claude's data in the next step.

**What you should see**: All five pieces of information visible somewhere on the contact detail page.

### Step 5: Navigate Back to the List

Use the browser's back button or click "Contacts" in the navigation bar to return to the contacts list.

**What you should see**: You're back on the contacts list, and Janet Morales is still visible.

## Verify with Claude

Now let's check your work using Claude Desktop.

> **Ask Claude**: "Show me the details for Janet Morales."

**What to look for**: Claude uses the `sandbox_get_client` tool and returns Janet's information — name, email, phone, risk tolerance, life stage, and any notes. Compare each field to what you saw in Salesforce. They should match.

> **Ask Claude**: "How many total clients do we have, and what are their risk tolerance levels?"

**What to look for**: Claude uses `sandbox_list_clients` and gives you a count (~50) plus a breakdown of risk tolerances (conservative, moderate, growth, aggressive). This gives you a feel for the client base you'll be working with in later lessons.

## Key Takeaways

- **Contacts are the foundation**: In any CRM, everything starts with the contact record. Tasks, meetings, reports — they all link back to a person.
- **Fields vary, concepts don't**: Salesforce calls it a "Contact." Schwab's tools might call it a "Client Profile." The data is the same: who they are, how to reach them, and what matters to them.
- **Advisor tip**: Before every client interaction — call, meeting, or email — spend 30 seconds reviewing their contact record. Knowing their risk tolerance, last interaction, and any pending tasks makes you sound prepared and attentive.

## Challenge

Try this on your own, then ask Claude to verify:

Find a different client in the contacts list (not Janet Morales). Open their record, note their name, risk tolerance, and life stage. Then compare what you see with what Claude reports.

> **When you're done, ask Claude**: "Show me the details for [client name you chose]. Does their risk tolerance match what I should see?"
