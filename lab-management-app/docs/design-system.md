# AIlab Design System v1.0

## Purpose
This document defines the visual and interaction baseline for AIlab user and admin apps.

## 1. Color System

### Brand
- `primary-50`: `#eef6ff`
- `primary-100`: `#dbeafe`
- `primary-200`: `#bfdbfe`
- `primary-500`: `#1677ff`
- `primary-600`: `#145fe0`
- `primary-700`: `#1d4ed8`

### Neutral
- `gray-50`: `#f8fafc`
- `gray-100`: `#f1f5f9`
- `gray-200`: `#e6ebf2`
- `gray-300`: `#cbd5e1`
- `gray-500`: `#667085`
- `gray-700`: `#334155`
- `gray-900`: `#0f172a`

### Semantic
- `success`: `#16a34a`
- `warning`: `#d97706`
- `danger`: `#dc2626`
- `info`: `#1677ff`

## 2. Typography
- Font family (sans): `"PingFang SC", "Noto Sans SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif`
- Font family (mono): `"JetBrains Mono", "SFMono-Regular", Consolas, monospace`

### Type scale
- `h1`: `24/32`, `700`
- `h2`: `20/28`, `700`
- `h3`: `18/26`, `600`
- `body`: `14/22`, `400`
- `caption`: `12/18`, `400`

## 3. Spacing
4pt grid scale:
- `space-1`: `4px`
- `space-2`: `8px`
- `space-3`: `12px`
- `space-4`: `16px`
- `space-6`: `24px`
- `space-8`: `32px`

## 4. Buttons
- Types: `Primary`, `Secondary`, `Ghost`, `Danger`
- Size default: `height 36px`, `radius 10px`, `font-size 13px`
- Mini: `height 30px`, `font-size 12px`
- Active feedback: `transform: scale(0.98)`

## 5. Forms
- Input height: `36px`
- Border: `1px solid #e6ebf2`
- Radius: `10px`
- Error text: `12px`, red (`#b91c1c`)
- Validation guideline: always use field-level messages

## 6. Cards
- Background: `#fff`
- Border: `1px solid #e6ebf2`
- Radius: `14px`
- Shadow: `0 8px 24px rgba(15, 23, 42, 0.08)`
- Padding: `12px` to `16px`

## 7. Tags
- Shape: pill (`999px`)
- Common states:
  - Success: bg `#eafaf0`, text `#15803d`
  - Warning: bg `#fff7e6`, text `#b45309`
  - Danger: bg `#fff1f2`, text `#b91c1c`
  - Info: bg `#eaf3ff`, text `#1d4ed8`

## 8. Modal
- Mask: `rgba(0, 0, 0, 0.4)`
- Width: `84%`, max `520px`
- Radius: `14px`
- Use confirm for destructive actions
- Show explicit success receipt after key operations

## 9. Empty State
- Structure: `icon + title + description (+ optional action)`
- Icon size: `36px` to `48px`
- Title: `15px`, `600`
- Description: `12px`, neutral text

## Implementation Files
- `styles/tokens.scss`
- `styles/mixins.scss`
- `styles/components.scss`
- Global entry: `App.vue` imports `styles/components.scss`
