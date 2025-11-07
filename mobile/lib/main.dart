import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'src/core/api_client.dart';
import 'src/core/session.dart';
import 'src/core/app_theme.dart';
import 'src/LaborerScreens/login_screen.dart';
import 'src/LaborerScreens/root_shell.dart';

void main() {
	runApp(const App());
}

class App extends StatelessWidget {
	const App({super.key});

	@override
	Widget build(BuildContext context) {
		return MultiProvider(
			providers: [
				ChangeNotifierProvider(create: (_) => Session()),
				Provider(create: (_) => ApiClient()),
			],
				child: Consumer<Session>(
				builder: (context, session, _) {
					final theme = AppTheme.lightTheme;
					// Debug: Print primary color to verify theme is loaded
					// print('Theme primary color: ${theme.colorScheme.primary}');
					// print('Theme text color: ${theme.colorScheme.onSurface}');
					
					return MaterialApp(
						title: 'Second Brain',
						debugShowCheckedModeBanner: false,
						theme: theme,
						darkTheme: AppTheme.darkTheme,
						themeMode: ThemeMode.light, // Can be changed to ThemeMode.system for auto dark mode
						home: session.isAuthenticated ? const RootShell() : const LoginScreen(),
					);
				},
			),
		);
	}
}
