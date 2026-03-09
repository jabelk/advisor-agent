# Feature Specification: Salesforce-Native List Views & Reports

**Feature Branch**: `021-sfdc-native-lists`
**Created**: 2026-03-09
**Status**: Draft
**Input**: Push compound filter definitions into Salesforce as native List Views and Reports so Jordan can see and interact with them in the Salesforce browser UI.

## Clarifications

### Session 2026-03-09

- Q: How should the system identify tool-created List Views/Reports to distinguish them from Salesforce defaults? → A: Platform-appropriate identification — List Views use a `DeveloperName` prefix (`AA_`) for programmatic lookup since ListViews have no description field; Reports use a description field tag (`[advisor-agent]`) for programmatic lookup. Both use a naming prefix (`AA:`) for visual clarity in the Salesforce UI.
- Q: When a compound filter includes dimensions that can't be represented in a Salesforce List View, what should the tool do? → A: Create a partial List View with supported filters translated, and warn the user in CLI output about which filter dimensions were omitted.

## User Scenarios & Testing

### User Story 1 - Create List Views from Compound Filters (Priority: P1)

Jordan runs a compound filter query from the CLI and wants to save it as a Salesforce List View so he can see the same filtered list in the Salesforce Contacts tab. He types a filter command, sees results in the CLI, then chooses to save it as a List View. The system creates the List View in Salesforce and prints a clickable URL so Jordan can open it in his browser and see the same clients displayed in the native Salesforce UI.

**Why this priority**: This is the core value — Jordan learns how List Views work in Salesforce by having the tool create them and then seeing the result in the browser. List Views are the most fundamental Salesforce CRM skill for segmenting clients.

**Independent Test**: Run `sandbox lists save --name "Top 50 Under 50" --max-age 50 --sort-by account_value --limit 50`, then open the printed Salesforce URL and verify the List View appears in the Contacts tab with matching filter criteria.

**Acceptance Scenarios**:

1. **Given** a compound filter (e.g., max-age 50, risk growth aggressive), **When** the user runs `sandbox lists save --name "Top 50 Under 50" [filters]`, **Then** a List View is created on the Contact object in Salesforce with the equivalent filter criteria, the name is prefixed with `AA:` for visual identification, the `DeveloperName` is prefixed with `AA_` for programmatic identification, and the CLI prints the Salesforce URL to open it.
2. **Given** an existing List View with the same name, **When** the user saves with that name again, **Then** the system updates the existing List View's filters rather than creating a duplicate.
3. **Given** a compound filter with multiple risk tolerances (e.g., growth AND aggressive), **When** saved as a List View, **Then** the List View filter uses the equivalent multi-value filter in Salesforce.
4. **Given** a filter with age, value, risk, and contact recency dimensions, **When** saved as a List View, **Then** all supported filter dimensions are translated to List View filter criteria, and any unsupported dimensions are noted in the CLI output.
5. **Given** a successful List View creation, **When** the user opens the URL in their browser, **Then** they see the Contact List View with the prefixed name, and the displayed clients match the CLI results.
6. **Given** a List View was created, **When** the user runs `sandbox lists show`, **Then** the list appears with its name (without the prefix) and Salesforce URL. Filter details are visible by opening the URL in Salesforce.

---

### User Story 2 - Manage Salesforce List Views from CLI (Priority: P2)

Jordan wants to see all the List Views he's created, delete ones he doesn't need, and understand what each one filters. The CLI provides commands to list all tool-created List Views in Salesforce, show their filter details, and delete them.

**Why this priority**: Management commands are essential once List Views exist — Jordan needs to maintain his Salesforce org and learn the lifecycle of CRM objects.

**Independent Test**: Create two List Views, run `sandbox lists show` to see both, run `sandbox lists delete "name"` on one, verify it's removed from both the CLI listing and the Salesforce UI.

**Acceptance Scenarios**:

1. **Given** multiple List Views created by the tool, **When** the user runs `sandbox lists show`, **Then** all tool-created List Views (identified by the `AA_` DeveloperName prefix) are listed with their name and Salesforce URL.
2. **Given** a List View exists, **When** the user runs `sandbox lists delete "Top 50 Under 50"`, **Then** the List View is removed from Salesforce and no longer appears in `sandbox lists show` or the Salesforce Contacts tab.
3. **Given** the user tries to delete a List View that doesn't exist, **Then** the system displays a clear "not found" message.
4. **Given** a List View was created manually in Salesforce (not by this tool), **When** the user runs `sandbox lists show`, **Then** only tool-created List Views (those with the `AA_` DeveloperName prefix) are shown, to avoid accidentally deleting Salesforce defaults.

---

### User Story 3 - Create Reports from Compound Filters (Priority: P3)

Jordan wants to save a compound filter query as a Salesforce Report so he can view it in the Reports tab, share it, and learn how Salesforce reporting works. The system creates a tabular report in a designated report folder with the filter criteria applied.

**Why this priority**: Reports are a more advanced Salesforce skill than List Views. Once Jordan is comfortable with List Views, Reports teach him about the reporting and analytics side of CRM.

**Independent Test**: Run `sandbox reports save --name "Growth Clients Under 40" --risk growth --max-age 40`, then open the printed Salesforce URL and verify the report appears in the Reports tab with matching data.

**Acceptance Scenarios**:

1. **Given** a compound filter, **When** the user runs `sandbox reports save --name "name" [filters]`, **Then** a tabular report is created in Salesforce in a designated report folder with the `AA:` name prefix and `[advisor-agent]` description tag, and the CLI prints the Salesforce URL.
2. **Given** an existing report with the same name, **When** the user saves again, **Then** the system updates the existing report rather than creating a duplicate.
3. **Given** the report is created, **When** the user opens the URL, **Then** they see a Salesforce report showing the filtered Contact data in a table format.
4. **Given** multiple reports exist, **When** the user runs `sandbox reports show`, **Then** all tool-created reports (identified by description tag) are listed with name, filter summary, URL, and last run date.
5. **Given** a report exists, **When** the user runs `sandbox reports delete "name"`, **Then** the report is removed from Salesforce.

---

### User Story 4 - NL Query to List View (Priority: P4)

Jordan uses the natural language query feature and wants to save the interpreted filters as a Salesforce List View in one step. After running `sandbox ask "top 50 clients under 50"`, the system offers to create a List View from the interpreted filters.

**Why this priority**: This builds on US1 (List Views) and the existing NL query feature from 020. It's a convenience enhancement, not a core capability.

**Independent Test**: Run `sandbox ask "growth clients under 40" --save-as "Young Growth Clients"`, verify a List View is created in Salesforce with the NL-interpreted filters.

**Acceptance Scenarios**:

1. **Given** a high-confidence NL query result, **When** the user adds `--save-as "List Name"`, **Then** the interpreted filters are saved as a Salesforce List View with that name (prefixed and tagged), and the URL is printed.
2. **Given** a low-confidence NL query, **When** the user adds `--save-as`, **Then** the system shows the interpreted filters first and asks for confirmation before creating the List View.

---

### Edge Cases

- What happens when Salesforce API limits prevent List View or Report creation? The system displays a clear error with the specific limit hit (e.g., "Maximum List Views reached for Contact object").
- What happens when a compound filter uses dimensions that List Views don't support (e.g., recency-based "not contacted in N days" requires a relative date formula)? The system creates a partial List View with supported filters and warns the user which dimensions were omitted. The Salesforce view may show a broader result set than the CLI query.
- What happens when the Salesforce session expires mid-operation? The system re-authenticates and retries, or displays a clear error asking the user to re-run.
- What happens when the user creates a List View with the tool, then modifies it manually in Salesforce, then tries to update it from the CLI? The CLI update overwrites the current filters (tool is the source of truth for tool-created views).

## Requirements

### Functional Requirements

- **FR-001**: System MUST create List Views on the Contact object in Salesforce from compound filter definitions, translating filter dimensions (age range, risk tolerance, life stage, account value, contact recency) into List View filter criteria.
- **FR-002**: System MUST return a clickable Salesforce URL for every created List View or Report so the user can open it directly in their browser.
- **FR-003**: System MUST support updating an existing List View's filters when saving with the same name (upsert behavior, not duplicate creation).
- **FR-004**: System MUST list all tool-created List Views with their name and Salesforce URL.
- **FR-005**: System MUST delete tool-created List Views from Salesforce by name.
- **FR-006**: System MUST create tabular Reports on the Contact object in a designated report folder, with compound filter criteria applied.
- **FR-007**: System MUST support updating an existing Report when saving with the same name.
- **FR-008**: System MUST list and delete tool-created Reports.
- **FR-009**: When a compound filter includes unsupported dimensions, the system MUST still create a partial List View or Report with the supported filters, and MUST display a warning listing the omitted filter dimensions so the user understands the Salesforce view may show more results than the CLI query.
- **FR-010**: System MUST identify tool-created objects using platform-appropriate mechanisms: List Views use a `DeveloperName` prefix (`AA_`) for programmatic lookup (ListViews have no description field); Reports use a description field tag (`[advisor-agent]`) for programmatic lookup. Both use a naming prefix (`AA:`) for visual identification in the Salesforce UI.
- **FR-011**: The `sandbox ask` NL query command MUST support an optional flag to save the interpreted filters as a Salesforce List View.

### Key Entities

- **Salesforce List View**: A filtered view of the Contact object, visible in the Salesforce Contacts tab. Has a name (prefixed with `AA:` when tool-created), a DeveloperName (prefixed with `AA_` for programmatic identification), filter criteria, column layout, and a unique Salesforce URL. Note: ListViews have no description field.
- **Salesforce Report**: A tabular report displaying filtered Contact data, stored in a report folder. Has a name (prefixed with `AA:` when tool-created), filter criteria, columns, a description containing `[advisor-agent]` tag, and a unique URL.
- **CompoundFilter** (existing from 020): The local filter model that drives compound queries. This feature translates CompoundFilter into Salesforce-native filter definitions.

## Success Criteria

### Measurable Outcomes

- **SC-001**: User can create a Salesforce List View from any compound filter query and open it in the browser within 10 seconds of the command completing.
- **SC-002**: 100% of List Views created by the tool are visible in the Salesforce Contacts tab and display the correct filtered client set.
- **SC-003**: User can complete the full List View lifecycle (create, view in browser, list, update, delete) entirely from the CLI without manually editing anything in Salesforce.
- **SC-004**: User can create a Salesforce Report from any compound filter query and open it in the browser, seeing the same data as the CLI output.
- **SC-005**: All supported filter dimensions (age, risk tolerance, life stage, account value) translate accurately to Salesforce List View filters — the browser view matches the CLI results.

## Assumptions

- The Salesforce developer sandbox supports programmatic List View and Report creation.
- The Salesforce org has sufficient List View and Report limits for the tool's usage (developer sandboxes typically allow many).
- Contact recency filters ("not contacted in N days") may require relative date formulas in Salesforce, which may not be fully representable in basic List View filters. The system will translate what it can and document limitations.
- The 020 compound filter engine (CompoundFilter model, list_clients, NL translation) remains the query execution layer. This feature adds a Salesforce persistence layer on top.
- The existing `sandbox lists save` command from 020 (which saved to local JSON) will be replaced by Salesforce List View creation. The local JSON storage will be deprecated.
- Report creation requires a report folder in Salesforce. The system will create a "Client Lists" folder if it doesn't exist.
