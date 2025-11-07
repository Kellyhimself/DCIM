# App Theme Usage Guide

This document shows how to use the shared theme and color palette throughout the app.

## Quick Access

### Colors
```dart
// Direct access to color constants
AppColors.deepTeal      // Primary brand color
AppColors.warmAmber     // Accent/CTA color
AppColors.softCoral     // Icons, progress indicators
AppColors.emerald       // Success states
AppColors.deepRed       // Error states
AppColors.charcoal      // Primary text
AppColors.slateGrey     // Secondary text
```

### Using Theme Colors in Widgets
```dart
// Access theme colors via context
context.primaryColor
context.secondaryColor
context.backgroundColor
context.textColor
context.secondaryTextColor

// Or via Theme.of(context)
Theme.of(context).colorScheme.primary
Theme.of(context).colorScheme.secondary
Theme.of(context).scaffoldBackgroundColor
```

### Text Styles
```dart
// Use predefined text styles
Text('Heading', style: AppTextStyles.headlineLarge)
Text('Body text', style: AppTextStyles.bodyMedium)
Text('Label', style: AppTextStyles.labelSmall)

// Or use theme text styles
Text('Title', style: Theme.of(context).textTheme.titleLarge)
Text('Body', style: Theme.of(context).textTheme.bodyMedium)
```

## Component Examples

### Buttons
```dart
// Primary button (uses deep teal)
ElevatedButton(
  onPressed: () {},
  child: Text('Submit'),
)

// Secondary button (uses warm amber accent)
FilledButton(
  onPressed: () {},
  child: Text('Action'),
)

// Outlined button
OutlinedButton(
  onPressed: () {},
  child: Text('Cancel'),
)
```

### Cards
```dart
Card(
  child: ListTile(
    title: Text('Card Title'),
    subtitle: Text('Card content'),
  ),
)
```

### Input Fields
```dart
TextFormField(
  decoration: InputDecoration(
    labelText: 'Email',
    hintText: 'Enter your email',
  ),
)
```

### Navigation Bar
The bottom navigation bar automatically uses the theme colors:
- Selected items: Deep Teal
- Unselected items: Slate Grey
- Background: White (light mode) / Dark Card (dark mode)

## Status Colors

### Success Messages
```dart
Container(
  color: AppColors.emerald,
  child: Text('Success!', style: TextStyle(color: Colors.white)),
)
```

### Error Messages
```dart
Container(
  color: AppColors.deepRed,
  child: Text('Error!', style: TextStyle(color: Colors.white)),
)
```

## Custom Styling

### Using Theme Colors for Custom Widgets
```dart
Container(
  decoration: BoxDecoration(
    color: Theme.of(context).colorScheme.surface,
    borderRadius: BorderRadius.circular(8),
    border: Border.all(
      color: Theme.of(context).colorScheme.primary,
    ),
  ),
  child: Text(
    'Custom Widget',
    style: TextStyle(
      color: Theme.of(context).colorScheme.onSurface,
    ),
  ),
)
```

### Custom Buttons with Theme Colors
```dart
ElevatedButton(
  style: ElevatedButton.styleFrom(
    backgroundColor: AppColors.warmAmber,
    foregroundColor: AppColors.charcoal,
  ),
  onPressed: () {},
  child: Text('Custom Button'),
)
```

## Dark Mode

The app supports dark mode. To enable it, change `themeMode` in `main.dart`:

```dart
MaterialApp(
  theme: AppTheme.lightTheme,
  darkTheme: AppTheme.darkTheme,
  themeMode: ThemeMode.system, // Auto-switch based on system settings
  // or
  themeMode: ThemeMode.dark,   // Force dark mode
)
```

## Best Practices

1. **Always use theme colors** instead of hardcoded colors for consistency
2. **Use AppTextStyles** for consistent typography
3. **Leverage Material 3 components** which automatically use the theme
4. **Test in both light and dark modes** when applicable
5. **Use semantic colors** (primary, secondary, error) rather than specific hex values when possible

## Color Palette Reference

| Purpose | Color | Hex | Usage |
|---------|-------|-----|-------|
| Primary | Deep Teal | #006D77 | Buttons, key brand color |
| Secondary | Warm Amber | #FFB703 | Highlights, call-to-actions |
| Accent | Soft Coral | #FB8500 | Icons, progress indicators |
| Background | Off-white | #F9FAFB | Default background |
| Surface | Sand Grey | #EAEAEA | Card or list background |
| Text Primary | Charcoal | #2C2C2C | Main text color |
| Text Secondary | Slate Grey | #5F6368 | Secondary text |
| Success | Emerald | #06D6A0 | Confirmations |
| Error | Deep Red | #E63946 | Alerts, warnings |

