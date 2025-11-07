import 'package:flutter/material.dart';

import 'voice_capture_screen.dart';
import 'home_screen.dart';
import 'clients_screen.dart';
import 'jobs_screen.dart';
import 'search_screen.dart';

class RootShell extends StatefulWidget {
	const RootShell({super.key});

	@override
	State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
	int _index = 0;
	final _pages = const [
		VoiceCaptureScreen(),
		HomeScreen(),
		ClientsScreen(),
		JobsScreen(),
		SearchScreen(),
	];

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			body: IndexedStack(index: _index, children: _pages),
			bottomNavigationBar: NavigationBar(
				selectedIndex: _index,
				onDestinationSelected: (i) => setState(() => _index = i),
				destinations: const [
					NavigationDestination(icon: Icon(Icons.mic_none), selectedIcon: Icon(Icons.mic), label: 'Record'),
					NavigationDestination(icon: Icon(Icons.notes_outlined), selectedIcon: Icon(Icons.notes), label: 'Notes'),
					NavigationDestination(icon: Icon(Icons.people_alt_outlined), selectedIcon: Icon(Icons.people), label: 'Clients'),
					NavigationDestination(icon: Icon(Icons.work_outline), selectedIcon: Icon(Icons.work), label: 'Jobs'),
					NavigationDestination(icon: Icon(Icons.search), selectedIcon: Icon(Icons.search), label: 'Search'),
				],
			),
		);
	}
}
