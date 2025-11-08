import 'package:flutter/material.dart';

import 'home_screen.dart';
import 'jobs_screen.dart';
import 'search_screen.dart';
import 'reminders_screen.dart';
import 'dashboard_screen.dart';

class RootShell extends StatefulWidget {
	const RootShell({super.key});

	@override
	State<RootShell> createState() => RootShellState();
}

class RootShellState extends State<RootShell> {
	int _index = 0;
	final _remindersKey = GlobalKey<RemindersScreenState>();
	
	late final _pages = [
		HomeScreen(),
		JobsScreen(),
		SearchScreen(),
		RemindersScreen(key: _remindersKey),
		DashboardScreen(),
	];

	// Public method to navigate to reminders tab and refresh
	void navigateToReminders() {
		setState(() => _index = 3);
		// Trigger refresh after navigation
		Future.delayed(const Duration(milliseconds: 100), () {
			_remindersKey.currentState?.refreshReminders();
		});
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			body: IndexedStack(index: _index, children: _pages),
			bottomNavigationBar: NavigationBar(
				selectedIndex: _index,
				onDestinationSelected: (i) {
					setState(() => _index = i);
					// Refresh reminders when navigating to reminders tab
					if (i == 3 && _remindersKey.currentState != null) {
						_remindersKey.currentState!.refreshReminders();
					}
				},
				destinations: const [
					NavigationDestination(icon: Icon(Icons.notes_outlined), selectedIcon: Icon(Icons.notes), label: 'Notes'),
					NavigationDestination(icon: Icon(Icons.work_outline), selectedIcon: Icon(Icons.work), label: 'Jobs'),
					NavigationDestination(icon: Icon(Icons.search), selectedIcon: Icon(Icons.search), label: 'Search'),
					NavigationDestination(icon: Icon(Icons.notifications_outlined), selectedIcon: Icon(Icons.notifications), label: 'Reminders'),
					NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: 'Dashboard'),
				],
			),
		);
	}
}
