# Salesforce Sandbox Setup Guide

**Last validated**: 2026-03-09
**Org type**: Agentforce-provisioned Developer Edition (orgfarm)
**Instance**: `orgfarm-561a3648a3-dev-ed.develop.my.salesforce.com`

## Overview

This guide documents how to set up and connect the advisor-agent sandbox to a Salesforce Developer Edition org. It captures the specific gotchas for Agentforce-provisioned orgs, which have different defaults than standard Developer Edition orgs.

## 1. Salesforce Org Constraints (Agentforce/Orgfarm)

These orgs have restrictions that affect authentication and API access:

| Feature | Standard Dev Edition | Agentforce Orgfarm |
|---------|---------------------|--------------------|
| SOAP API login | Enabled | **Disabled by default** |
| OAuth2 Password flow | Works | **Fails** (authentication failure) |
| OAuth2 Client Credentials | Requires setup | **Only viable auth method** |
| Task.Type field | Available | **Does not exist** |

**Key takeaway**: Only the **Client Credentials OAuth2 flow** works for programmatic access to Agentforce orgs. Both SOAP login and the username-password OAuth flow will fail.

## 2. Connected App Configuration

### Create the Connected App

1. **Setup** → **App Manager** → **New Connected App**
2. Name: `Advisor Agent` (or any name)
3. Enable OAuth Settings: checked
4. Callback URL: `https://login.salesforce.com/services/oauth2/callback` (not used but required)

### Required OAuth Scopes

Add these explicitly — **"Full access (full)" alone is NOT sufficient** for Client Credentials flow:

- **Manage user data via APIs (api)** — this is the critical one
- Full access (full) — optional but doesn't hurt
- Access the Salesforce API Platform (sfap_api)

### Enable Client Credentials Flow

1. After saving the Connected App, go to **Manage** → **Edit Policies**
2. Under **Client Credentials Flow**:
   - Check **"Enable Client Credentials Flow"**
   - Set **"Run As"** user (pick the System Administrator user)
3. Save
4. **Wait ~2 minutes** for Salesforce to propagate the changes

### Get Credentials

From the Connected App detail page:
- **Consumer Key** → `SFDC_CONSUMER_KEY`
- **Consumer Secret** → `SFDC_CONSUMER_SECRET` (click to reveal)

## 3. Environment Variables

Required in `.env`:

```bash
SFDC_INSTANCE_URL=https://orgfarm-561a3648a3-dev-ed.develop.my.salesforce.com
SFDC_CONSUMER_KEY=<from Connected App>
SFDC_CONSUMER_SECRET=<from Connected App>
SFDC_LOGIN_URL=https://login.salesforce.com
SFDC_USERNAME=admin.XXXXX@agentforce.com
SFDC_PASSWORD=<password>
SFDC_SECURITY_TOKEN=<from Reset Security Token in user settings>
```

Note: `SFDC_USERNAME`, `SFDC_PASSWORD`, `SFDC_SECURITY_TOKEN` are stored for reference but **not used for authentication** in Agentforce orgs (password flow fails). The Client Credentials flow uses only `SFDC_INSTANCE_URL`, `SFDC_CONSUMER_KEY`, and `SFDC_CONSUMER_SECRET`.

## 4. Custom Field Deployment

The sandbox requires 6 custom fields on the Contact object. These **cannot** be created via the Tooling API alone in Agentforce orgs (fields appear in metadata but aren't accessible via the REST API). The reliable approach is the **Metadata Deploy REST API**.

### What gets deployed

| Field API Name | Type | Label |
|---------------|------|-------|
| `Age__c` | Number(3,0) | Age |
| `Account_Value__c` | Currency(18,2) | Account Value |
| `Risk_Tolerance__c` | Text(20) | Risk Tolerance |
| `Life_Stage__c` | Text(20) | Life Stage |
| `Investment_Goals__c` | LongTextArea(5000) | Investment Goals |
| `Household_Members__c` | LongTextArea(2000) | Household Members |

### Deployment method

The `sandbox setup` command (or `ensure_custom_fields()` in `sfdc.py`) uses:

1. **Metadata Deploy REST API** (`POST /services/data/v66.0/metadata/deployRequest`)
   - Sends a zip containing `package.xml`, `objects/Contact.object`, and a PermissionSet
   - This is REST-based, no SOAP required
2. **PermissionSet** (`Advisor_Agent_Fields`)
   - Grants Read/Edit Field-Level Security on all 6 custom fields
   - Auto-assigned to the Run As user
3. Polls for deployment completion (typically < 10 seconds)

### Why not Tooling API?

We tried the Tooling API first. It returns `201 Created` for each field, and the fields appear in Tooling API queries. However, they are **NOT accessible** via the standard REST API (`/services/data/vXX.0/sobjects/Contact/`). This appears to be specific to Agentforce orgs — the Tooling API creates field metadata but doesn't fully deploy to the runtime schema. The Metadata Deploy API is the only reliable path.

### Why PermissionSet is required

Even after fields are deployed via the Metadata API, they're not visible to the API user until Field-Level Security (FLS) grants access. The `Advisor_Agent_Fields` PermissionSet handles this automatically.

## 5. Data Model Mapping

### Contact (Client Profiles)

| Our Field | Salesforce Field | Type |
|-----------|-----------------|------|
| first_name | FirstName | Standard |
| last_name | LastName | Standard |
| email | Email | Standard |
| phone | Phone | Standard |
| occupation | Title | Standard |
| notes | Description | Standard |
| age | Age__c | Custom |
| account_value | Account_Value__c | Custom |
| risk_tolerance | Risk_Tolerance__c | Custom |
| life_stage | Life_Stage__c | Custom |
| investment_goals | Investment_Goals__c | Custom |
| household_members | Household_Members__c | Custom |
| created_at | CreatedDate | System (read-only) |
| updated_at | LastModifiedDate | System (read-only) |

### Task (Interaction History)

| Our Field | Salesforce Field | Notes |
|-----------|-----------------|-------|
| client_id | WhoId | FK to Contact |
| interaction_date | ActivityDate | Date only (no time) |
| interaction_type | Description | `Type` field doesn't exist in Agentforce orgs |
| summary | Subject | Standard combobox field |
| (status) | Status | Always set to "Completed" |
| created_at | CreatedDate | System (read-only) |

**Important**: Standard Salesforce orgs have a `Task.Type` field, but Agentforce orgs do not. We store the interaction type in `Description` instead.

## 6. Gotchas & Workarounds

### Duplicate Detection

Salesforce's Standard Contact Duplicate Rule blocks creates when contacts have similar names/emails. Since seed data generates names from pools that can repeat, we pass the `Sforce-Duplicate-Rule-Header: allowSave=true` header on Contact creates.

### API Version

`simple_salesforce` defaults to v59.0. Custom fields and newer APIs work across all versions, but the Metadata Deploy endpoint requires specifying a recent version (we use v66.0 for deployment operations).

### Seed Data Cleanup

The `reset_sandbox` function identifies seeded contacts by their `@example.com` email domain. It deletes Tasks first (since they reference Contacts via WhoId), then deletes the Contacts. Pre-existing org contacts without `@example.com` emails are untouched.

### Session Caching

`simple_salesforce` caches the object describe metadata. If you create custom fields and immediately try to use them in the same session, the describe cache may be stale. Get a fresh `Salesforce()` instance after field deployment.

## 7. Setup from Scratch (Step-by-Step)

If setting up a new org:

1. Provision a Salesforce Developer Edition (or get an Agentforce trial org)
2. Create a Connected App (Section 2 above)
3. Enable Client Credentials Flow with correct scopes and Run As user
4. Wait 2 minutes
5. Set environment variables in `.env` (Section 3)
6. Run `finance-agent sandbox setup` — deploys custom fields + PermissionSet
7. Run `finance-agent sandbox seed` — pushes 50 synthetic clients to Salesforce
8. Run `finance-agent sandbox list` — verify data

## 8. Architecture Decisions

### Why Salesforce instead of local SQLite?

The original implementation used SQLite for all client data. This was reworked to use the actual Salesforce API because:

- **Learning goal**: Jordan needs to understand Salesforce concepts (SOQL, objects, fields, relationships) — a local database doesn't teach that
- **Transferable skills**: Working with the Salesforce API builds patterns applicable to any CRM integration
- **Real SFDC practice**: Custom fields, PermissionSets, Connected Apps, OAuth flows — these are all things an advisor automation developer needs to understand

### Hybrid architecture

- **Client data** → Salesforce (Contact + Task objects)
- **Research signals** → local SQLite (SEC EDGAR, Finnhub, RSS pipeline — unchanged)
- **Meeting briefs** → Salesforce client data + SQLite signals → Claude API
- **Commentary** → SQLite signals only → Claude API (no per-client data needed)

This split means the research pipeline stays fast and local, while CRM operations teach real Salesforce skills.
