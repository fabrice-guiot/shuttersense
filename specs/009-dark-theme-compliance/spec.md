# Feature Specification: Dark Theme Compliance

**Feature Branch**: `009-dark-theme-compliance`
**Created**: 2026-01-10
**Status**: Draft
**Input**: User description: "Github issue #55 in relation to the content of frontend/docs/design-system.md and respecting the dark theme of the UI while maintaining sufficient contrast for the user. For instance, one thing that does not currently comply with the dark theme are scrollbars: they are light grey on a white background which clashes with the dark theme."
**Related Issue**: [GitHub Issue #55](https://github.com/fabrice-guiot/photo-admin/issues/55) - Implement Design System Recommendation

## Overview

The Photo Admin application uses a dark theme by default, but several UI elements do not currently follow the established design system guidelines. This creates visual inconsistencies that break the immersive dark experience. The most notable issue is scrollbars appearing with light backgrounds and light tracks, which clash against the dark interface.

This feature will audit and remediate all dark theme violations to ensure a cohesive, accessible, and visually consistent user experience across the entire application.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scrollbar Visual Consistency (Priority: P1)

As a user navigating content-heavy pages (collections list, job logs, details panels), I want scrollbars to blend naturally with the dark interface so that the scrolling experience feels native and visually cohesive.

**Why this priority**: Scrollbars are the most visible violation mentioned in Issue #55 and affect nearly every page with scrollable content. Fixing this immediately improves the perceived quality of the entire application.

**Independent Test**: Can be fully tested by opening any page with scrollable content (e.g., Collections list with many items) and verifying scrollbars use dark theme styling with sufficient contrast for the thumb/track.

**Acceptance Scenarios**:

1. **Given** I am viewing any page with vertical scrollable content, **When** the content overflows, **Then** the scrollbar track appears in a dark color that matches the background and the scrollbar thumb appears in a contrasting muted color.
2. **Given** I am viewing a horizontally scrollable element (e.g., a data table), **When** the content overflows, **Then** the horizontal scrollbar follows the same dark theme styling.
3. **Given** I am using a webkit-based browser (Chrome, Safari, Edge), **When** custom scrollbar styles are applied, **Then** they use design tokens for colors.

---

### User Story 2 - Design Token Compliance Audit (Priority: P2)

As a developer maintaining the Photo Admin frontend, I want all UI elements to use design tokens instead of hardcoded colors so that theme consistency is guaranteed and future theming is possible.

**Why this priority**: Hardcoded colors are the root cause of theme violations. Addressing these systematically prevents future regressions and enables potential light mode support.

**Independent Test**: Can be verified by running a codebase search for hardcoded color patterns (hex codes, rgb values, Tailwind color classes like `bg-gray-*`, `text-white`, etc.) and confirming zero violations in component files.

**Acceptance Scenarios**:

1. **Given** a component uses background colors, **When** I inspect the styles, **Then** I see design tokens (`bg-background`, `bg-card`, `bg-muted`) not hardcoded values.
2. **Given** a component uses text colors, **When** I inspect the styles, **Then** I see semantic tokens (`text-foreground`, `text-muted-foreground`) not hardcoded values.
3. **Given** a component uses border colors, **When** I inspect the styles, **Then** I see the `border-border` token.

---

### User Story 3 - Sufficient Contrast for Accessibility (Priority: P2)

As a user with varying visual abilities, I want all UI elements to have sufficient color contrast so that I can easily read text and identify interactive elements in the dark theme.

**Why this priority**: Accessibility compliance is both a usability requirement and often a legal/regulatory consideration. Proper contrast ensures all users can effectively use the application.

**Independent Test**: Can be verified by running an accessibility audit tool (e.g., browser DevTools accessibility checker, axe, or Lighthouse) and confirming all text/background combinations meet WCAG 2.1 AA contrast requirements (4.5:1 for normal text, 3:1 for large text and UI components).

**Acceptance Scenarios**:

1. **Given** any text element in the interface, **When** I check its contrast ratio against its background, **Then** the ratio meets or exceeds WCAG AA requirements.
2. **Given** any interactive element (button, link, input), **When** I check its contrast ratio against adjacent colors, **Then** the ratio meets or exceeds 3:1.
3. **Given** a user relies on keyboard navigation focus states, **When** focus is applied to an element, **Then** the focus ring is clearly visible against the dark background.

---

### User Story 4 - Form Input Styling (Priority: P3)

As a user filling out forms in the application, I want input fields, dropdowns, and other form controls to follow dark theme styling so that the form experience is consistent with the rest of the application.

**Why this priority**: Forms are critical for data entry but are less frequently encountered than general navigation. Ensuring they match the dark theme improves overall polish.

**Independent Test**: Can be verified by navigating to any form (Create Collection, Create Connector, etc.) and confirming all input fields, selects, textareas, and labels use dark theme styling.

**Acceptance Scenarios**:

1. **Given** I am viewing a form with text inputs, **When** I observe the input styling, **Then** inputs have dark backgrounds, light text, and borders that match the design system.
2. **Given** I am interacting with a dropdown/select component, **When** I open the dropdown, **Then** the dropdown menu follows dark theme styling.
3. **Given** I focus on a form field, **When** the focus state is applied, **Then** the focus ring uses the design token (`ring`) and is clearly visible.

---

### User Story 5 - Error State Visibility and Graceful Degradation (Priority: P2)

As a user encountering an error (backend unavailable, invalid navigation, unexpected failure), I want to see a clearly readable, user-friendly error message instead of a blank page or unreadable content so that I understand something went wrong and can take appropriate action.

**Why this priority**: Error states are critical touchpoints that can frustrate users if poorly handled. A blank page or unreadable error box leaves users confused and unable to recover. Proper error display maintains trust and provides actionable guidance even when things go wrong.

**Independent Test**: Can be fully tested by simulating error conditions (stopping the backend, navigating to invalid routes, triggering API failures) and verifying that all error states display readable, properly styled messages.

**Acceptance Scenarios**:

1. **Given** the backend is unavailable, **When** I attempt to load any page that requires data, **Then** I see a clearly visible error message explaining the connection issue with readable text on a properly contrasted background.
2. **Given** I navigate to a non-existent route or invalid URL, **When** the page loads, **Then** I see a styled "not found" page (not a blank page) with navigation options to return to valid content.
3. **Given** an API call fails unexpectedly, **When** the error is displayed, **Then** the error alert/box uses dark theme styling with sufficient contrast (not dark text on dark background).
4. **Given** any error message is displayed, **When** I read the message, **Then** it contains user-friendly language (not raw technical stack traces or JSON) and suggests a recovery action if possible.
5. **Given** a page component fails to render, **When** the error boundary catches the failure, **Then** a fallback UI is displayed that follows dark theme styling and allows navigation away from the broken page.

---

### Edge Cases

- What happens when native browser elements (file inputs, date pickers) are used? They should be styled to match the dark theme where possible, or documented as exceptions.
- How does the system handle user-agent stylesheet overrides for scrollbars in different browsers (Firefox uses different scrollbar properties than WebKit)?
- What happens with dynamically injected content from third-party libraries that may bring their own styles?
- What happens when multiple errors occur simultaneously (e.g., network timeout during form submission)? The system should display a single, coherent error message.
- What happens when an error message content is very long? It should remain readable with proper text wrapping and scrolling if needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST style all scrollbars (vertical and horizontal) using dark theme colors via CSS custom properties.
- **FR-002**: System MUST provide cross-browser scrollbar styling covering WebKit browsers (via `::-webkit-scrollbar` pseudo-elements) and Firefox (via `scrollbar-color` and `scrollbar-width` properties).
- **FR-003**: All components MUST use design tokens for colors (no hardcoded hex values, rgb values, or Tailwind utility colors like `gray-900`, `white`, etc.).
- **FR-004**: All text/background combinations MUST meet WCAG 2.1 AA contrast requirements (4.5:1 for normal text, 3:1 for large text and UI components).
- **FR-005**: Form controls (inputs, selects, textareas, checkboxes) MUST follow dark theme styling using design tokens.
- **FR-006**: Focus states MUST be clearly visible against dark backgrounds using the `ring` design token.
- **FR-007**: System MUST document any elements that cannot be styled (native browser controls, third-party components) as known exceptions in the design system documentation.
- **FR-008**: All error states (API failures, network errors, invalid routes) MUST display user-friendly messages with proper dark theme styling and sufficient contrast.
- **FR-009**: System MUST provide a styled "not found" page for invalid routes that follows dark theme guidelines and offers navigation options.
- **FR-010**: Error boundaries MUST catch component failures and display a dark-theme-styled fallback UI instead of blank pages.
- **FR-011**: Error messages MUST present user-friendly language, hiding technical details (stack traces, raw JSON) from the end user.

### Key Entities

- **Design Tokens**: CSS custom properties (variables) that define the application's color palette and can be referenced throughout the styles. Key tokens include `--background`, `--foreground`, `--card`, `--muted`, `--border`, `--ring`.
- **Component Styles**: CSS/Tailwind classes applied to React components that determine their visual appearance.
- **Global Styles**: Application-wide CSS rules (typically in `globals.css` or `index.css`) that affect all elements including scrollbars.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero hardcoded color values exist in component files (verified by codebase search for hex/rgb patterns and non-token Tailwind color classes).
- **SC-002**: Scrollbars on all scrollable containers blend with the dark theme (verified by visual inspection on Chrome, Firefox, Safari, Edge).
- **SC-003**: All text passes WCAG 2.1 AA contrast requirements (verified by Lighthouse/axe accessibility audit with zero contrast violations).
- **SC-004**: All interactive elements have visible focus states (verified by keyboard navigation through the application).
- **SC-005**: Design system documentation updated to include scrollbar styling guidelines and any known exceptions.
- **SC-006**: All error states display readable messages with no blank pages (verified by simulating backend unavailability, invalid routes, and API failures).
- **SC-007**: Error alerts and messages use proper contrast ratios matching WCAG AA requirements (verified by accessibility audit on error state components).
- **SC-008**: No raw technical content (stack traces, JSON responses) is visible to end users in error messages (verified by triggering various error conditions).

## Assumptions

- The application operates exclusively in dark mode (no light mode toggle currently exists).
- Tailwind CSS is configured with a dark mode color palette using CSS custom properties.
- The existing design token definitions in the codebase are correct and appropriate for dark mode; they just need to be applied consistently.
- Browser support targets modern browsers (Chrome, Firefox, Safari, Edge) in their latest 2 major versions.
