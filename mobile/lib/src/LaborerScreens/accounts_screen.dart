import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';
import 'login_screen.dart';

class AccountsScreen extends StatefulWidget {
	const AccountsScreen({super.key});

	@override
	State<AccountsScreen> createState() => _AccountsScreenState();
}

class _AccountsScreenState extends State<AccountsScreen> {
	bool _deleting = false;
	String? _deleteError;

	ApiClient get _api => context.read<ApiClient>();
	Session get _session => context.read<Session>();

	void safeSetState(VoidCallback fn) {
		if (!mounted) return;
		setState(fn);
	}

	Future<void> _logout() async {
		final confirmed = await showDialog<bool>(
			context: context,
			builder: (context) => AlertDialog(
				title: const Text('Logout'),
				content: const Text('Are you sure you want to logout?'),
				actions: [
					TextButton(
						onPressed: () => Navigator.of(context).pop(false),
						child: const Text('Cancel'),
					),
					FilledButton(
						onPressed: () => Navigator.of(context).pop(true),
						style: FilledButton.styleFrom(
							backgroundColor: AppColors.deepRed,
						),
						child: const Text('Logout'),
					),
				],
			),
		);

		if (confirmed == true) {
			await _session.logout();
			if (!mounted) return;
			Navigator.of(context).pushAndRemoveUntil(
				MaterialPageRoute(builder: (_) => const LoginScreen()),
				(route) => false,
			);
		}
	}

	Future<void> _deleteAll(String type, String endpoint) async {
		final confirmed = await showDialog<bool>(
			context: context,
			builder: (context) => AlertDialog(
				title: Text('Delete All $type'),
				content: Text(
					'Are you sure you want to delete ALL $type? This action cannot be undone.',
				),
				actions: [
					TextButton(
						onPressed: () => Navigator.of(context).pop(false),
						child: const Text('Cancel'),
					),
					FilledButton(
						onPressed: () => Navigator.of(context).pop(true),
						style: FilledButton.styleFrom(
							backgroundColor: AppColors.deepRed,
						),
						child: const Text('Delete All'),
					),
				],
			),
		);

		if (confirmed != true) return;

		_api.attachSession(_session);
		safeSetState(() {
			_deleting = true;
			_deleteError = null;
		});

		try {
			await _api.dio.delete(endpoint);
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(
						content: Text('All $type deleted successfully'),
						backgroundColor: AppColors.emerald,
					),
				);
			}
		} on DioException catch (e) {
			safeSetState(() {
				_deleteError = e.response?.data?.toString() ?? 'Failed to delete $type';
			});
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(
						content: Text('Failed to delete $type: ${_deleteError}'),
						backgroundColor: AppColors.deepRed,
					),
				);
			}
		} finally {
			safeSetState(() => _deleting = false);
		}
	}

	Future<void> _deleteAllCache() async {
		final confirmed = await showDialog<bool>(
			context: context,
			builder: (context) => AlertDialog(
				title: const Text('Delete All Cache'),
				content: const Text(
					'Are you sure you want to delete ALL NLP cache? This will force re-extraction of all voice notes. This action cannot be undone.',
				),
				actions: [
					TextButton(
						onPressed: () => Navigator.of(context).pop(false),
						child: const Text('Cancel'),
					),
					FilledButton(
						onPressed: () => Navigator.of(context).pop(true),
						style: FilledButton.styleFrom(
							backgroundColor: AppColors.deepRed,
						),
						child: const Text('Delete All'),
					),
				],
			),
		);

		if (confirmed != true) return;

		_api.attachSession(_session);
		safeSetState(() {
			_deleting = true;
			_deleteError = null;
		});

		try {
			await _api.dio.delete('/nlp/cache?all=true');
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(
						content: const Text('All cache deleted successfully'),
						backgroundColor: AppColors.emerald,
					),
				);
			}
		} on DioException catch (e) {
			safeSetState(() {
				_deleteError = e.response?.data?.toString() ?? 'Failed to delete cache';
			});
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(
						content: Text('Failed to delete cache: ${_deleteError}'),
						backgroundColor: AppColors.deepRed,
					),
				);
			}
		} finally {
			safeSetState(() => _deleting = false);
		}
	}

	Widget _buildDeleteButton({
		required String label,
		required String type,
		required String endpoint,
		required IconData icon,
	}) {
		return ListTile(
			leading: Icon(icon, color: AppColors.deepRed),
			title: Text(label),
			subtitle: Text('Delete all $type'),
			trailing: _deleting
				? const SizedBox(
					width: 20,
					height: 20,
					child: CircularProgressIndicator(strokeWidth: 2),
				)
				: IconButton(
					icon: const Icon(Icons.delete_outline),
					color: AppColors.deepRed,
					onPressed: _deleting ? null : () => _deleteAll(type, endpoint),
				),
		);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('Account Settings'),
			),
			body: ListView(
				children: [
					// Account Section
					Padding(
						padding: const EdgeInsets.all(16),
						child: Text(
							'Account',
							style: Theme.of(context).textTheme.titleMedium?.copyWith(
								fontWeight: FontWeight.bold,
								color: AppColors.softCoral,
							),
						),
					),
					Card(
						margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
						child: ListTile(
							leading: const Icon(Icons.logout, color: AppColors.deepRed),
							title: const Text('Logout'),
							subtitle: const Text('Sign out of your account'),
							trailing: const Icon(Icons.chevron_right),
							onTap: _logout,
						),
					),

					const SizedBox(height: 16),

					// Danger Zone Section
					Padding(
						padding: const EdgeInsets.all(16),
						child: Text(
							'Danger Zone',
							style: Theme.of(context).textTheme.titleMedium?.copyWith(
								fontWeight: FontWeight.bold,
								color: AppColors.deepRed,
							),
						),
					),
					Card(
						margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
						child: Column(
							children: [
								_buildDeleteButton(
									label: 'Delete All Notes',
									type: 'notes',
									endpoint: '/notes/all',
									icon: Icons.note_outlined,
								),
								const Divider(height: 1),
								_buildDeleteButton(
									label: 'Delete All Jobs',
									type: 'jobs',
									endpoint: '/jobs/all',
									icon: Icons.work_outline,
								),
								const Divider(height: 1),
								_buildDeleteButton(
									label: 'Delete All Reminders',
									type: 'reminders',
									endpoint: '/reminders/all',
									icon: Icons.notifications_outlined,
								),
								const Divider(height: 1),
								_buildDeleteButton(
									label: 'Delete All Clients',
									type: 'clients',
									endpoint: '/clients/all',
									icon: Icons.people_outline,
								),
								const Divider(height: 1),
								ListTile(
									leading: const Icon(Icons.cached, color: AppColors.deepRed),
									title: const Text('Delete All Cache'),
									subtitle: const Text('Delete all NLP cache (force re-extraction)'),
									trailing: _deleting
										? const SizedBox(
											width: 20,
											height: 20,
											child: CircularProgressIndicator(strokeWidth: 2),
										)
										: IconButton(
											icon: const Icon(Icons.delete_outline),
											color: AppColors.deepRed,
											onPressed: _deleting ? null : _deleteAllCache,
										),
								),
							],
						),
					),

					const SizedBox(height: 32),
				],
			),
		);
	}
}

