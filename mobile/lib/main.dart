import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'src/core/api_client.dart';
import 'src/core/session.dart';
import 'src/screens/login_screen.dart';
import 'src/screens/root_shell.dart';

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
					return MaterialApp(
						title: 'Second Brain',
						debugShowCheckedModeBanner: false,
						theme: ThemeData(
							brightness: Brightness.light,
							useMaterial3: true,
							colorScheme: ColorScheme.fromSeed(
								seedColor: const Color(0xFF0F766E),
							),
							inputDecorationTheme: const InputDecorationTheme(
								border: OutlineInputBorder(),
							),
						),
						home: session.isAuthenticated ? const RootShell() : const LoginScreen(),
					);
				},
			),
		);
	}
}
