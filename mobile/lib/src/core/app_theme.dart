import 'package:flutter/material.dart';

/// App Color Palette
/// Trustworthy, energetic, readable, and friendly colors for practical users
class AppColors {
	// Primary Colors
	static const Color deepTeal =  Color(0xFFFB8500);
	static const Color warmAmber = Color(0xFFFB8500);
	static const Color softCoral = Color(0xFFFB8500);//this one
	
	// Background Colors (Light Mode)
	static const Color offWhite = Color(0xFFF9FAFB);
	static const Color sandGrey = Color(0xFFEAEAEA);
	static const Color white = Color(0xFFFFFFFF);
	
	// Text Colors (Light Mode)
	static const Color charcoal = Color(0xFF2C2C2C);
	static const Color slateGrey = Color(0xFF5F6368);
	
	// Status Colors
	static const Color emerald = Color(0xFF06D6A0);
	static const Color deepRed =  Color(0xFFFB8500);
	
	// Dark Mode Colors
	static const Color darkBackground = Color(0xFF121212);
	static const Color darkCard = Color(0xFF1E1E1E);
	static const Color darkText = Color(0xFFF5F5F5);
	static const Color darkPrimary = Color(0xFF00B4D8);
	static const Color darkAccent = Color(0xFFFFD166);
}

/// Shared Text Styles
class AppTextStyles {
	// Headlines
	static const TextStyle headlineLarge = TextStyle(
		fontSize: 32,
		fontWeight: FontWeight.bold,
		letterSpacing: -0.5,
		color: AppColors.charcoal,
	);
	
	static const TextStyle headlineMedium = TextStyle(
		fontSize: 28,
		fontWeight: FontWeight.bold,
		letterSpacing: -0.5,
		color: AppColors.charcoal,
	);
	
	static const TextStyle headlineSmall = TextStyle(
		fontSize: 24,
		fontWeight: FontWeight.w600,
		letterSpacing: -0.5,
		color: AppColors.charcoal,
	);
	
	// Body Text
	static const TextStyle bodyLarge = TextStyle(
		fontSize: 16,
		fontWeight: FontWeight.normal,
		height: 1.5,
		color: AppColors.charcoal,
	);
	
	static const TextStyle bodyMedium = TextStyle(
		fontSize: 14,
		fontWeight: FontWeight.normal,
		height: 1.5,
		color: AppColors.charcoal,
	);
	
	static const TextStyle bodySmall = TextStyle(
		fontSize: 12,
		fontWeight: FontWeight.normal,
		height: 1.4,
		color: AppColors.charcoal,
	);
	
	// Labels
	static const TextStyle labelLarge = TextStyle(
		fontSize: 14,
		fontWeight: FontWeight.w600,
		letterSpacing: 0.1,
		color: AppColors.charcoal,
	);
	
	static const TextStyle labelMedium = TextStyle(
		fontSize: 12,
		fontWeight: FontWeight.w600,
		letterSpacing: 0.1,
		color: AppColors.charcoal,
	);
	
	static const TextStyle labelSmall = TextStyle(
		fontSize: 11,
		fontWeight: FontWeight.w600,
		letterSpacing: 0.1,
		color: AppColors.charcoal,
	);
}

/// App Theme Configuration
class AppTheme {
	/// Light Theme - Optimized for outdoor readability
	static ThemeData get lightTheme {
		// Create explicit ColorScheme with all required colors
		// Using base ColorScheme() constructor to prevent Material 3 auto-generation
		final colorScheme = ColorScheme(
			brightness: Brightness.light,
			primary: AppColors.deepTeal,
			onPrimary: Colors.white,
			secondary: AppColors.warmAmber,
			onSecondary: AppColors.charcoal,
			tertiary: AppColors.softCoral,
			onTertiary: Colors.white,
			error: AppColors.deepRed,
			onError: Colors.white,
			surface: AppColors.white,
			onSurface: AppColors.charcoal,
			surfaceVariant: AppColors.sandGrey,
			onSurfaceVariant: AppColors.slateGrey,
			background: AppColors.offWhite,
			onBackground: AppColors.charcoal,
			outline: AppColors.sandGrey,
			outlineVariant: AppColors.sandGrey.withOpacity(0.5),
			shadow: Colors.black,
			scrim: Colors.black,
			inverseSurface: AppColors.charcoal,
			onInverseSurface: AppColors.white,
			inversePrimary: AppColors.deepTeal.withOpacity(0.2),
		);
		
		return ThemeData(
			useMaterial3: true,
			colorScheme: colorScheme,
			// Force Material 3 to use our explicit colors, not generated ones
			applyElevationOverlayColor: false,
			
			// Explicitly set text selection colors to prevent green tint
			textSelectionTheme: TextSelectionThemeData(
				cursorColor: AppColors.deepTeal,
				selectionColor: AppColors.deepTeal.withOpacity(0.3),
				selectionHandleColor: AppColors.deepTeal,
			),
			
			// Scaffold
			scaffoldBackgroundColor: AppColors.offWhite,
			
			// App Bar
			appBarTheme: const AppBarTheme(
				backgroundColor: AppColors.deepTeal,
				foregroundColor: Colors.white,
				elevation: 0,
				centerTitle: false,
				titleTextStyle: TextStyle(
					fontSize: 20,
					fontWeight: FontWeight.w600,
					color: Colors.white,
					letterSpacing: -0.5,
				),
			),
			
			// Card Theme
			cardTheme: CardThemeData(
				color: AppColors.white,
				elevation: 1,
				shape: RoundedRectangleBorder(
					borderRadius: BorderRadius.circular(12),
				),
				margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
			),
			
			// Button Themes
			elevatedButtonTheme: ElevatedButtonThemeData(
				style: ElevatedButton.styleFrom(
					backgroundColor: AppColors.deepTeal,
					foregroundColor: Colors.white,
					elevation: 2,
					padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
					shape: RoundedRectangleBorder(
						borderRadius: BorderRadius.circular(8),
					),
					textStyle: AppTextStyles.labelLarge.copyWith(color: Colors.white),
				),
			),
			
			filledButtonTheme: FilledButtonThemeData(
				style: FilledButton.styleFrom(
					backgroundColor: AppColors.deepTeal,
					foregroundColor: Colors.white,
					padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
					shape: RoundedRectangleBorder(
						borderRadius: BorderRadius.circular(8),
					),
					textStyle: AppTextStyles.labelLarge.copyWith(color: Colors.white),
				),
			),
			
			outlinedButtonTheme: OutlinedButtonThemeData(
				style: OutlinedButton.styleFrom(
					foregroundColor: AppColors.deepTeal,
					padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
					side: const BorderSide(color: AppColors.deepTeal, width: 1.5),
					shape: RoundedRectangleBorder(
						borderRadius: BorderRadius.circular(8),
					),
					textStyle: AppTextStyles.labelLarge.copyWith(color: AppColors.deepTeal),
				),
			),
			
			textButtonTheme: TextButtonThemeData(
				style: TextButton.styleFrom(
					foregroundColor: AppColors.deepTeal,
					padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
					textStyle: AppTextStyles.labelLarge.copyWith(color: AppColors.deepTeal),
				),
			),
			
			// Floating Action Button
			floatingActionButtonTheme: const FloatingActionButtonThemeData(
				backgroundColor: AppColors.warmAmber,
				foregroundColor: AppColors.charcoal,
				elevation: 4,
			),
			
			// Input Decoration
			inputDecorationTheme: InputDecorationTheme(
				filled: true,
				fillColor: AppColors.white,
				border: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.sandGrey),
				),
				enabledBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.sandGrey),
				),
				focusedBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.deepTeal, width: 2),
				),
				errorBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.deepRed),
				),
				focusedErrorBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.deepRed, width: 2),
				),
				contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
				labelStyle: AppTextStyles.bodyMedium.copyWith(color: AppColors.slateGrey),
				floatingLabelStyle: AppTextStyles.bodyMedium.copyWith(color: AppColors.deepTeal),
				hintStyle: AppTextStyles.bodyMedium.copyWith(color: AppColors.slateGrey),
			),
			
			// Text Theme - Explicitly set all text colors to charcoal
			textTheme: const TextTheme(
				displayLarge: AppTextStyles.headlineLarge,
				displayMedium: AppTextStyles.headlineMedium,
				displaySmall: AppTextStyles.headlineSmall,
				headlineLarge: AppTextStyles.headlineLarge,
				headlineMedium: AppTextStyles.headlineMedium,
				headlineSmall: AppTextStyles.headlineSmall,
				titleLarge: AppTextStyles.headlineSmall,
				titleMedium: AppTextStyles.bodyLarge,
				titleSmall: AppTextStyles.bodyMedium,
				bodyLarge: AppTextStyles.bodyLarge,
				bodyMedium: AppTextStyles.bodyMedium,
				bodySmall: AppTextStyles.bodySmall,
				labelLarge: AppTextStyles.labelLarge,
				labelMedium: AppTextStyles.labelMedium,
				labelSmall: AppTextStyles.labelSmall,
			),
			
			// Icon Theme
			iconTheme: const IconThemeData(
				color: AppColors.deepTeal,
				size: 24,
			),
			
			// Navigation Bar (Bottom Navigation)
			navigationBarTheme: NavigationBarThemeData(
				backgroundColor: AppColors.white,
				indicatorColor: AppColors.deepTeal.withOpacity(0.1),
				labelTextStyle: MaterialStateProperty.resolveWith((states) {
					if (states.contains(MaterialState.selected)) {
						return AppTextStyles.labelSmall.copyWith(color: AppColors.deepTeal);
					}
					return AppTextStyles.labelSmall.copyWith(color: AppColors.slateGrey);
				}),
				iconTheme: MaterialStateProperty.resolveWith((states) {
					if (states.contains(MaterialState.selected)) {
						return const IconThemeData(color: AppColors.deepTeal);
					}
					return const IconThemeData(color: AppColors.slateGrey);
				}),
			),
			
			// Chip Theme
			chipTheme: ChipThemeData(
				backgroundColor: AppColors.sandGrey,
				deleteIconColor: AppColors.charcoal,
				disabledColor: AppColors.sandGrey.withOpacity(0.5),
				selectedColor: AppColors.deepTeal,
				secondarySelectedColor: AppColors.warmAmber,
				padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
				labelStyle: AppTextStyles.bodySmall,
				secondaryLabelStyle: AppTextStyles.bodySmall.copyWith(color: Colors.white),
				shape: RoundedRectangleBorder(
					borderRadius: BorderRadius.circular(20),
				),
			),
			
			// Divider
			dividerTheme: const DividerThemeData(
				color: AppColors.sandGrey,
				thickness: 1,
				space: 1,
			),
		);
	}
	
	/// Dark Theme - For future dark mode support
	static ThemeData get darkTheme {
		// Create explicit ColorScheme with all required colors for dark mode
		final darkColorScheme = ColorScheme(
			brightness: Brightness.dark,
			primary: AppColors.darkPrimary,
			onPrimary: AppColors.darkBackground,
			secondary: AppColors.darkAccent,
			onSecondary: AppColors.darkBackground,
			tertiary: AppColors.softCoral,
			onTertiary: Colors.white,
			error: AppColors.deepRed,
			onError: Colors.white,
			surface: AppColors.darkCard,
			onSurface: AppColors.darkText,
			surfaceVariant: AppColors.darkCard,
			onSurfaceVariant: AppColors.darkText.withOpacity(0.7),
			background: AppColors.darkBackground,
			onBackground: AppColors.darkText,
			outline: AppColors.darkText.withOpacity(0.3),
			outlineVariant: AppColors.darkText.withOpacity(0.2),
			shadow: Colors.black,
			scrim: Colors.black,
			inverseSurface: AppColors.darkText,
			onInverseSurface: AppColors.darkBackground,
			inversePrimary: AppColors.darkPrimary.withOpacity(0.2),
		);
		
		return ThemeData(
			useMaterial3: true,
			colorScheme: darkColorScheme,
			
			// Scaffold
			scaffoldBackgroundColor: AppColors.darkBackground,
			
			// App Bar
			appBarTheme: const AppBarTheme(
				backgroundColor: AppColors.darkCard,
				foregroundColor: AppColors.darkText,
				elevation: 0,
				centerTitle: false,
				titleTextStyle: TextStyle(
					fontSize: 20,
					fontWeight: FontWeight.w600,
					color: AppColors.darkText,
					letterSpacing: -0.5,
				),
			),
			
			// Card Theme
			cardTheme: CardThemeData(
				color: AppColors.darkCard,
				elevation: 2,
				shape: RoundedRectangleBorder(
					borderRadius: BorderRadius.circular(12),
				),
				margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
			),
			
			// Button Themes
			elevatedButtonTheme: ElevatedButtonThemeData(
				style: ElevatedButton.styleFrom(
					backgroundColor: AppColors.darkPrimary,
					foregroundColor: AppColors.darkBackground,
					elevation: 2,
					padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
					shape: RoundedRectangleBorder(
						borderRadius: BorderRadius.circular(8),
					),
					textStyle: AppTextStyles.labelLarge.copyWith(color: AppColors.darkBackground),
				),
			),
			
			filledButtonTheme: FilledButtonThemeData(
				style: FilledButton.styleFrom(
					backgroundColor: AppColors.darkPrimary,
					foregroundColor: AppColors.darkBackground,
					padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
					shape: RoundedRectangleBorder(
						borderRadius: BorderRadius.circular(8),
					),
					textStyle: AppTextStyles.labelLarge.copyWith(color: AppColors.darkBackground),
				),
			),
			
			// Input Decoration
			inputDecorationTheme: InputDecorationTheme(
				filled: true,
				fillColor: AppColors.darkCard,
				border: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: BorderSide(color: AppColors.darkText.withOpacity(0.3)),
				),
				enabledBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: BorderSide(color: AppColors.darkText.withOpacity(0.3)),
				),
				focusedBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.darkPrimary, width: 2),
				),
				errorBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.deepRed),
				),
				focusedErrorBorder: OutlineInputBorder(
					borderRadius: BorderRadius.circular(8),
					borderSide: const BorderSide(color: AppColors.deepRed, width: 2),
				),
				contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
				labelStyle: AppTextStyles.bodyMedium.copyWith(color: AppColors.darkText.withOpacity(0.7)),
			),
			
			// Text Theme
			textTheme: const TextTheme(
				displayLarge: AppTextStyles.headlineLarge,
				displayMedium: AppTextStyles.headlineMedium,
				displaySmall: AppTextStyles.headlineSmall,
				headlineLarge: AppTextStyles.headlineLarge,
				headlineMedium: AppTextStyles.headlineMedium,
				headlineSmall: AppTextStyles.headlineSmall,
				titleLarge: AppTextStyles.headlineSmall,
				titleMedium: AppTextStyles.bodyLarge,
				titleSmall: AppTextStyles.bodyMedium,
				bodyLarge: AppTextStyles.bodyLarge,
				bodyMedium: AppTextStyles.bodyMedium,
				bodySmall: AppTextStyles.bodySmall,
				labelLarge: AppTextStyles.labelLarge,
				labelMedium: AppTextStyles.labelMedium,
				labelSmall: AppTextStyles.labelSmall,
			).apply(
				bodyColor: AppColors.darkText,
				displayColor: AppColors.darkText,
			),
			
			// Icon Theme
			iconTheme: const IconThemeData(
				color: AppColors.darkText,
				size: 24,
			),
			
			// Navigation Bar
			navigationBarTheme: NavigationBarThemeData(
				backgroundColor: AppColors.darkCard,
				indicatorColor: AppColors.darkPrimary.withOpacity(0.2),
				labelTextStyle: MaterialStateProperty.resolveWith((states) {
					if (states.contains(MaterialState.selected)) {
						return AppTextStyles.labelSmall.copyWith(color: AppColors.darkPrimary);
					}
					return AppTextStyles.labelSmall.copyWith(color: AppColors.darkText.withOpacity(0.7));
				}),
				iconTheme: MaterialStateProperty.resolveWith((states) {
					if (states.contains(MaterialState.selected)) {
						return const IconThemeData(color: AppColors.darkPrimary);
					}
					return IconThemeData(color: AppColors.darkText.withOpacity(0.7));
				}),
			),
			
			// Floating Action Button
			floatingActionButtonTheme: const FloatingActionButtonThemeData(
				backgroundColor: AppColors.darkAccent,
				foregroundColor: AppColors.darkBackground,
				elevation: 4,
			),
		);
	}
}

/// Extension methods for easy access to app colors and styles
extension AppThemeExtension on BuildContext {
	AppColors get colors => AppColors();
	AppTextStyles get textStyles => AppTextStyles();
	
	/// Quick access to theme colors
	Color get primaryColor => Theme.of(this).colorScheme.primary;
	Color get secondaryColor => Theme.of(this).colorScheme.secondary;
	Color get backgroundColor => Theme.of(this).scaffoldBackgroundColor;
	Color get surfaceColor => Theme.of(this).colorScheme.surface;
	Color get textColor => Theme.of(this).colorScheme.onSurface;
	Color get secondaryTextColor => Theme.of(this).colorScheme.onSurfaceVariant;
}

