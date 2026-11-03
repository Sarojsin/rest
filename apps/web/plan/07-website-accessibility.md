# Website Plan — Accessibility

## Overview
Comprehensive accessibility plan for the multi-tenant restaurant management platform. WCAG 2.1 AA compliance as minimum, with WCAG 2.1 AAA as goal for Enterprise tier.

## Accessibility Standards

### WCAG 2.1 AA (All Tiers)
- **Perceivable**: Information and UI components must be presentable to users in ways they can perceive
- **Operable**: UI components and navigation must be operable
- **Understandable**: Information and operation of UI must be understandable
- **Robust**: Content must be robust enough to be interpreted by assistive technologies

### WCAG 2.1 AAA (Enterprise Goal)
- Enhanced criteria for color contrast, text sizing, and navigation
- Sign language support for key notifications
- Cognitive accessibility considerations

## Color & Contrast

### Contrast Requirements
- **Text on background**: 4.5:1 minimum (WCAG AA)
- **Large text** (18pt+): 3:1 minimum
- **UI elements**: 3:1 minimum
- **Enhanced contrast**: 7:1 for AAA compliance

### Color Palette Verification
| Color | Hex | Contrast on White | Contrast on Dark |
|-------|-----|-------------------|------------------|
| Primary | `#18181B` | 17.9:1 ✅ | 3.1:1 ⚠️ |
| Accent | `#00D1C1` | 3.5:1 ⚠️ | 5.8:1 ✅ |
| Error | `#EF4444` | 4.5:1 ✅ | 4.5:1 ✅ |
| Success | `#22C55E` | 3.0:1 ⚠️ | 5.4:1 ✅ |
| Warning | `#F59E0B` | 2.6:1 ⚠️ | 4.8:1 ✅ |

### Color Usage Guidelines
- **Never rely on color alone** to convey information
- **Use icons + text** for status indicators
- **Provide alternative indicators** for color-blind users
- **Test with color blindness simulators**

## Keyboard Navigation

### Tab Order
- Logical tab order following visual flow
- Skip navigation link at top of page
- Focus indicators visible (2px outline)
- No keyboard traps

### Keyboard Shortcuts
- **Enter**: Activate buttons/links
- **Space**: Toggle checkboxes, activate buttons
- **Arrow Keys**: Navigate lists, menus, tables
- **Escape**: Close modals, dropdowns
- **Tab**: Move forward
- **Shift + Tab**: Move backward

### Focus Management
- **Modal Focus**: Trap focus inside modal, restore on close
- **Dynamic Content**: Focus management for AJAX updates
- **Skip Link**: Skip to main content
- **Focus Restoration**: Return focus after modal close

### Keyboard Shortcuts (Power Users)
- `Ctrl/Cmd + K`: Command palette
- `Ctrl/Cmd + /`: Search
- `Ctrl/Cmd + Enter`: Submit form
- `Escape`: Cancel/close
- `Arrow keys`: Navigate tables, menus

## Screen Reader Support

### ARIA Labels
- `aria-label` for non-text elements (icons, buttons)
- `aria-describedby` for form fields with help text
- `aria-live` regions for dynamic content
- `aria-hidden` for decorative elements

### Semantic HTML
- Proper heading hierarchy (h1 → h2 → h3)
- Landmark regions (`<header>`, `<nav>`, `<main>`, `<footer>`)
- Lists for navigation and data
- Tables with proper headers

### Screen Reader Announcements
- **Order Status**: "Order submitted, status: pending"
- **Table Changes**: "Table 5 status changed to occupied"
- **Form Errors**: "Email field: Invalid email format"
- **Loading States**: "Loading, please wait"
- **Success Messages**: "Order placed successfully"

### Screen Reader Testing
- **NVDA** (Windows): Primary testing tool
- **VoiceOver** (macOS/iOS): Secondary testing
- **JAWS** (Windows): Enterprise testing
- **TalkBack** (Android): Mobile testing

## Visual Accessibility

### Text Sizing
- **Minimum**: 16px body text
- **Scalable**: Up to 200% without breaking layout
- **Responsive**: Text scales with viewport
- **No Horizontal Scroll**: At 200% zoom

### Visual Indicators
- **Focus Indicators**: 2px solid outline, visible on all elements
- **Hover States**: Clear visual feedback
- **Active States**: Distinct visual state
- **Disabled States**: Reduced opacity, cursor change

### Motion & Animation
- **Reduced Motion**: `prefers-reduced-motion` respected
- **No Auto-Play**: No auto-playing animations
- **Pause Controls**: Pause/stop for animated content
- **Transition Duration**: <300ms for non-essential animations

### High Contrast Mode
- **Windows High Contrast**: Full support
- **Dark Mode**: Optional dark theme (future)
- **Custom Colors**: User preference override
- **Contrast Testing**: Automated contrast checking

## Form Accessibility

### Form Labels
- All inputs have associated labels
- `for` attribute links label to input
- `aria-label` for complex inputs
- Hidden labels for screen reader only (visually hidden)

### Form Validation
- **Inline Validation**: Real-time validation feedback
- **Error Messages**: Clear, specific error messages
- **Error Association**: `aria-describedby` links input to error
- **Success States**: Clear success indicators

### Form Navigation
- **Tab Order**: Logical field order
- **Enter Key**: Submit form
- **Escape**: Cancel/close
- **Auto-Focus**: First field on form load
- **Error Focus**: Focus first error field on validation failure

## Table Accessibility

### Table Structure
- **Headers**: `th` elements with `scope` attribute
- **Caption**: `<caption>` element for table description
- **Row Groups**: `thead`, `tbody`, `tfoot` for structure
- **Column Headers**: `th` with `scope="col"`
- **Row Headers**: `th` with `scope="row"`

### Table Navigation
- **Arrow Keys**: Navigate cells
- **Tab**: Move between focusable elements
- **Screen Reader**: Row/column announcements
- **Sorting**: `aria-sort` attribute for sortable columns

### Table Features
- **Pagination**: Keyboard navigable, screen reader announcements
- **Filtering**: Clear filter indicators, keyboard accessible
- **Sorting**: Visual sort indicators, keyboard controls
- **Row Selection**: Checkbox selection with keyboard support

## Modal & Dialog Accessibility

### Modal Focus
- **Focus Trapping**: Focus stays inside modal
- **Focus Restoration**: Focus returns to trigger element
- **Escape Key**: Closes modal
- **Background**: Inert (not focusable) when modal open

### Modal Structure
- **Title**: `aria-labelledby` pointing to title
- **Description**: `aria-describedby` for content
- **Role**: `role="dialog"` or `role="alertdialog"`
- **Close Button**: `aria-label="Close modal"`

### Modal Announcements
- **Open**: "Dialog opened: [title]"
- **Close**: "Dialog closed"
- **Content Changes**: `aria-live` for dynamic content

## Loading & Error States

### Loading States
- **Skeleton Screens**: Placeholder for loading content
- **Progress Indicators**: `role="progressbar"` with `aria-valuenow`
- **Loading Announcements**: "Loading, please wait"
- **Disable Interaction**: While loading, prevent interaction

### Error States
- **Error Messages**: Clear, specific, actionable
- **Error Announcements**: `aria-live="assertive"` for errors
- **Error Focus**: Focus on first error field
- **Recovery**: Clear path to fix errors

### Empty States
- **No Data**: Clear message, helpful guidance
- **No Results**: Suggest alternative actions
- **Empty Actions**: Primary CTA for empty state

## Mobile Accessibility

### Touch Targets
- **Minimum Size**: 44px × 44px
- **Spacing**: 8px between touch targets
- **Gesture Alternatives**: Keyboard alternatives for gestures

### Mobile Navigation
- **Hamburger Menu**: Keyboard accessible, screen reader friendly
- **Swipe Gestures**: Alternative keyboard navigation
- **Responsive Text**: Scales with viewport
- **Orientation**: Works in portrait and landscape

### Mobile Screen Readers
- **VoiceOver** (iOS): Full support
- **TalkBack** (Android): Full support
- **Mobile Navigation**: Swipe navigation, rotor controls

## Testing & Validation

### Automated Testing
- **axe-core**: Automated accessibility testing
- **Lighthouse**: Accessibility audits
- **WAVE**: Web accessibility evaluation tool
- **Pa11y**: Command-line accessibility testing

### Manual Testing
- **Keyboard Navigation**: Full keyboard-only testing
- **Screen Reader Testing**: NVDA, VoiceOver, JAWS
- **Color Contrast**: Manual verification
- **Zoom Testing**: 200% zoom without breaking layout

### Testing Schedule
- **Development**: Accessibility checks on every PR
- **Staging**: Full accessibility audit before release
- **Production**: Monthly accessibility audits
- **User Testing**: Quarterly user testing with assistive technology users

### Accessibility Checklist
- [ ] All images have alt text
- [ ] All form fields have labels
- [ ] All interactive elements are keyboard accessible
- [ ] All colors meet contrast requirements
- [ ] All dynamic content has ARIA labels
- [ ] All modals have focus management
- [ ] All tables have proper headers
- [ ] All error messages are accessible
- [ ] All loading states are announced
- [ ] All empty states have guidance

## Legal Compliance

### Privacy Policy
- **Accessibility Statement**: Commitment to accessibility
- **Contact Information**: Accessibility contact email
- **Feedback Mechanism**: User feedback for accessibility issues
- **Remediation Process**: Process for fixing accessibility issues

### Terms of Service
- **Accessibility Clause**: Commitment to WCAG 2.1 AA
- **User Responsibilities**: Users must not disable accessibility features
- **Indemnification**: Standard legal language

### Cookie Consent
- **Banner**: Clear, accessible cookie consent
- **Options**: Accept all, reject all, customize
- **Persistence**: Remember user preference
- **Screen Reader**: Announced when banner appears

### Data Processing Agreement (Enterprise)
- **Accessibility**: DPA available in accessible format
- **Large Text**: Support for larger text sizes
- **Screen Reader**: DPA readable by screen readers

## Accessibility Roadmap

### Phase 1: Basic Accessibility (Current)
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- Color contrast
- Form accessibility

### Phase 2: Enhanced Accessibility (Future)
- WCAG 2.1 AAA compliance
- Sign language support
- Cognitive accessibility
- Voice navigation
- Eye tracking support

### Phase 3: Advanced Accessibility (Future)
- AI-powered accessibility
- Real-time captioning
- Audio descriptions
- Personalized accessibility profiles

## Accessibility Metrics

### Key Metrics
- **Lighthouse Accessibility Score**: >90
- **axe-core Violations**: 0
- **Keyboard Navigation**: 100% of interactive elements
- **Screen Reader Compatibility**: 100% of content
- **Color Contrast**: 100% of text meets 4.5:1

### Monitoring
- **Automated Testing**: Every commit
- **Manual Testing**: Monthly
- **User Testing**: Quarterly
- **Audit**: Annual external audit

### Reporting
- **Accessibility Report**: Monthly internal report
- **User Feedback**: Tracked and addressed
- **Issue Tracking**: Accessibility issues in bug tracker
- **Resolution Time**: Critical issues <7 days

## Resources

### Documentation
- **WCAG 2.1 Guidelines**: w3.org/WAI/WCAG21/quickref/
- **ARIA Practices**: w3.org/WAI/ARIA/apg/
- **WebAIM**: webaim.org/resources/

### Tools
- **axe DevTools**: Browser extension for accessibility testing
- **Lighthouse**: Built into Chrome DevTools
- **WAVE**: Web accessibility evaluation tool
- **Color Contrast Analyzer**: For manual contrast checking

### Training
- **Team Training**: Accessibility basics for all developers
- **Advanced Training**: WCAG compliance for leads
- **User Testing**: Regular testing with assistive technology users

---
*Accessibility plan aligned with 26-phase backend implementation. All accessibility features designed for WCAG 2.1 AA compliance with Enterprise AAA as goal.*