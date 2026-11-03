# Website Plan — Design System

## Overview
Comprehensive design system for the multi-tenant restaurant management platform. Covers color palette, typography, spacing, components, and responsive design patterns.

## Color Palette

### Primary Colors
- **Primary**: `#18181B` (almost black, for readability)
- **Secondary**: `#27272A` (card backgrounds)
- **Accent**: `#00D1C1` (teal, for actions/highlights)
- **Error**: `#EF4444` (red, for errors)
- **Success**: `#22C55E` (green, for success states)
- **Warning**: `#F59E0B` (amber, for warnings)

### Tier-Specific Colors
- **Basic**: `#18181B` (default theme)
- **Professional**: `#3B82F6` (blue accent for professional features)
- **Enterprise**: `#8B5CF6` (purple accent for enterprise features)

### Neutral Colors
- **White**: `#FFFFFF`
- **Gray 50**: `#F9FAFB`
- **Gray 100**: `#F3F4F6`
- **Gray 200**: `#E5E7EB`
- **Gray 300**: `#D1D5DB`
- **Gray 400**: `#9CA3AF`
- **Gray 500**: `#6B7280`
- **Gray 600**: `#4B5563`
- **Gray 700**: `#374151`
- **Gray 800**: `#1F2937`
- **Gray 900**: `#111827`

## Typography

### Font Family
- **Primary**: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica Neue, Arial, "Noto Sans", sans-serif
- **Monospace**: "SF Mono", "Monaco", "Inconsolata", "Roboto Mono", "Source Code Pro", monospace

### Font Sizes
| Size | Value | Usage |
|------|-------|-------|
| `xs` | 12px | Captions, small text |
| `sm` | 14px | Secondary text, labels |
| `base` | 16px | Body text (default) |
| `lg` | 18px | Large body text |
| `xl` | 20px | Subheadings |
| `2xl` | 24px | Section headings |
| `3xl` | 30px | Page headings |
| `4xl` | 36px | Hero headings |

### Font Weights
- **Light**: 300
- **Regular**: 400
- **Medium**: 500
- **Semi-Bold**: 600
- **Bold**: 700
- **Extra Bold**: 800

### Line Heights
- **Tight**: 1.25 (headings)
- **Snug**: 1.375 (subheadings)
- **Normal**: 1.5 (body text)
- **Relaxed**: 1.625 (long-form content)
- **Loose**: 2 (spacious content)

## Spacing Scale

### Spacing Values
- **2px**: `0.125rem`
- **4px**: `0.25rem`
- **8px**: `0.5rem`
- **16px**: `1rem`
- **24px**: `1.5rem`
- **32px**: `2rem`
- **48px**: `3rem`
- **64px**: `4rem`

### Spacing Usage
- **Margin**: 4px, 8px, 16px, 24px, 32px, 48px
- **Padding**: 4px, 8px, 16px, 24px, 32px
- **Gap**: 8px, 16px, 24px

## Component Library

### Buttons
- **Primary**: Solid background, white text, rounded corners
- **Secondary**: Outlined, transparent background
- **Ghost**: No background, hover effect
- **Danger**: Red background, white text
- **Sizes**: sm (24px), md (32px), lg (40px), xl (48px)

### Inputs
- **Text Input**: Border, focus ring, label above
- **Password Input**: Toggle visibility, strength meter
- **Select**: Custom dropdown, search functionality
- **Checkbox**: Custom checkbox, label inline
- **Radio**: Custom radio buttons, group layout

### Cards
- **Basic Card**: White background, subtle shadow, rounded corners
- **Elevated Card**: Larger shadow, hover effect
- **Card Header**: Title, subtitle, actions
- **Card Footer**: Actions, metadata

### Modals
- **Confirm Modal**: Title, message, confirm/cancel buttons
- **Input Modal**: Title, form fields, submit/cancel buttons
- **Alert Modal**: Title, alert message, single button

### Tables
- **Basic Table**: Striped rows, hover effect
- **Data Table**: Sorting, filtering, pagination
- **Compact Table**: Dense layout for dashboards

### Navigation
- **Navbar**: Logo, menu items, user profile
- **Sidebar**: Collapsible, icon + label
- **Breadcrumbs**: Path navigation
- **Tabs**: Horizontal tabs, active state

### Badges
- **Status Badge**: Active, inactive, suspended, pending
- **Role Badge**: Owner, manager, waiter, kitchen, cashier
- **Tier Badge**: Basic, Professional, Enterprise

## Responsive Design

### Breakpoints
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

### Mobile-First Approach
- Base styles for mobile
- Progressive enhancement for larger screens
- Touch-friendly targets (minimum 44px)
- Hamburger navigation for mobile
- Collapsible sidebars

### Responsive Patterns
- **Grid**: 1 column (mobile) → 2 columns (tablet) → 3-4 columns (desktop)
- **Navigation**: Hamburger (mobile) → Horizontal (tablet+)
- **Tables**: Horizontal scroll (mobile) → Responsive table (desktop)
- **Images**: Responsive sizes, lazy loading

## Accessibility (WCAG 2.1 AA)

### Color Contrast
- Text on background: 4.5:1 minimum
- Large text: 3:1 minimum
- UI elements: 3:1 minimum

### Keyboard Navigation
- All interactive elements focusable
- Tab order follows visual flow
- Skip navigation link
- Focus indicators visible

### Screen Reader Support
- `aria-label` for non-text elements
- `aria-describedby` for form fields
- `aria-live` regions for dynamic content
- Semantic HTML structure

### Focus Management
- Modal focus trapping
- Focus restoration after modal close
- Skip link to main content

## Animation & Motion

### Transitions
- **Fast**: 150ms (button hover, focus)
- **Normal**: 250ms (modal open/close, dropdown)
- **Slow**: 350ms (page transitions, complex animations)

### Easing
- **Ease-out**: `cubic-bezier(0.0, 0.0, 0.2, 1)` (entrance)
- **Ease-in**: `cubic-bezier(0.4, 0.0, 1, 1)` (exit)
- **Ease-in-out**: `cubic-bezier(0.4, 0.0, 0.2, 1)` (default)

### Motion Preferences
- `prefers-reduced-motion`: Disable animations
- `prefers-color-scheme`: Dark mode support (future)

## Dark Mode (Future)
- **Toggle**: User preference, system preference detection
- **Colors**: Inverted palette, adjusted for readability
- **Implementation**: CSS variables with `.dark` class

## Icon System
- **Library**: Lucide React (consistent with shadcn-ui)
- **Size**: 16px, 20px, 24px
- **Color**: Inherit from parent
- **Usage**: Navigation, actions, status indicators

## Loading States
- **Skeleton**: Placeholder for loading content
- **Spinner**: Circular loading indicator
- **Progress Bar**: Linear progress for uploads/operations
- **Empty State**: No data illustrations

## Error States
- **Inline Errors**: Form field validation
- **Toast Notifications**: Success, error, warning, info
- **Error Pages**: 404, 500, 403 custom pages
- **Empty States**: No data, no results

## Design Tokens (CSS Variables)
```css
:root {
  /* Colors */
  --color-primary: #18181B;
  --color-secondary: #27272A;
  --color-accent: #00D1C1;
  --color-error: #EF4444;
  --color-success: #22C55E;
  --color-warning: #F59E0B;
  
  /* Typography */
  --font-sans: Inter, system-ui, sans-serif;
  --font-mono: "SF Mono", Monaco, monospace;
  
  /* Spacing */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  
  /* Border Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
}
```

## Component Naming Convention
- **PascalCase** for components: `Button`, `Modal`, `Table`
- **camelCase** for props: `onClick`, `disabled`, `variant`
- **kebab-case** for CSS classes: `btn-primary`, `card-elevated`
- **BEM** for complex components: `table__header`, `table__row--selected`

## File Organization
```
src/
├── components/          # Reusable components
│   ├── ui/             # Base UI components (shadcn-ui)
│   ├── layout/         # Layout components
│   └── features/       # Feature-specific components
├── pages/              # Page components
├── hooks/              # Custom React hooks
├── lib/                # Utility functions
├── types/              # TypeScript types
├── styles/             # Global styles
└── assets/             # Static assets
```

## Design Handoff
- **Figma**: Design files for all components and pages
- **Storybook**: Component documentation and testing
- **Token export**: JSON format for design tokens
- **Component specs**: Detailed specs for each component

---
*Design system aligned with 26-phase backend implementation. All components designed for production-grade SAAS with multi-tenant isolation and responsive design.*