import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';

class DashboardScreen extends StatefulWidget {
	const DashboardScreen({super.key});

	@override
	State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
	Map<String, dynamic>? _financialData;
	bool _loading = true;
	String? _error;
	DateTime? _startDate;
	DateTime? _endDate;

	ApiClient get _api => context.read<ApiClient>();
	Session get _session => context.read<Session>();

	void safeSetState(VoidCallback fn) {
		if (!mounted) return;
		setState(fn);
	}

	Future<void> _load() async {
		_api.attachSession(_session);
		safeSetState(() { _loading = true; _error = null; });
		try {
			final params = <String, String?>{};
			if (_startDate != null) {
				params['start_date'] = DateFormat('yyyy-MM-dd').format(_startDate!);
			}
			if (_endDate != null) {
				params['end_date'] = DateFormat('yyyy-MM-dd').format(_endDate!);
			}
			
			final resp = await _api.dio.get('/dashboard/financial', queryParameters: params);
			if (!mounted) return;
			safeSetState(() {
				_financialData = resp.data as Map<String, dynamic>;
			});
		} on DioException catch (e) {
			safeSetState(() { _error = e.response?.data?.toString() ?? 'Failed to load financial data'; });
		} finally {
			safeSetState(() { _loading = false; });
		}
	}

	Future<void> _selectDate(bool isStart) async {
		final picked = await showDatePicker(
			context: context,
			initialDate: isStart ? (_startDate ?? DateTime.now().subtract(const Duration(days: 30))) : (_endDate ?? DateTime.now()),
			firstDate: DateTime(2020),
			lastDate: DateTime.now().add(const Duration(days: 365)),
		);
		if (picked != null) {
			safeSetState(() {
				if (isStart) {
					_startDate = picked;
				} else {
					_endDate = picked;
				}
			});
			await _load();
		}
	}

	@override
	void initState() {
		super.initState();
		WidgetsBinding.instance.addPostFrameCallback((_) => _load());
	}

	Widget _buildStatCard(String title, double value, Color color, {bool isProjected = false}) {
		return Card(
			child: Padding(
				padding: const EdgeInsets.all(10),
				child: Column(
					crossAxisAlignment: CrossAxisAlignment.start,
					children: [
						Row(
							children: [
								Expanded(
									child: Text(
										title,
										style: Theme.of(context).textTheme.bodySmall?.copyWith(
											color: Colors.grey[600],
											fontSize: 11,
										),
									),
								),
								if (isProjected)
									Container(
										padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
										decoration: BoxDecoration(
											color: Colors.orange.withOpacity(0.1),
											borderRadius: BorderRadius.circular(6),
										),
										child: Text(
											'Est',
											style: TextStyle(
												color: Colors.orange[700],
												fontSize: 9,
												fontWeight: FontWeight.w600,
											),
										),
									),
							],
						),
						const SizedBox(height: 4),
						Text(
							'KES ${NumberFormat('#,##0.00').format(value)}',
							style: Theme.of(context).textTheme.titleMedium?.copyWith(
								fontWeight: FontWeight.bold,
								color: color,
								fontSize: 18,
							),
						),
					],
				),
			),
		);
	}

	Widget _buildBreakdownSection(String title, Map<String, dynamic> data) {
		if (data.isEmpty) {
			return const SizedBox.shrink();
		}
		
		return Column(
			crossAxisAlignment: CrossAxisAlignment.start,
			children: [
				Padding(
					padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
					child: Text(
						title,
						style: Theme.of(context).textTheme.titleSmall?.copyWith(
							fontWeight: FontWeight.bold,
							color: AppColors.softCoral,
							fontSize: 14,
						),
					),
				),
				...data.entries.map((entry) {
					final name = entry.key;
					final stats = entry.value as Map<String, dynamic>;
					final earnings = (stats['earnings'] as num?)?.toDouble() ?? 0.0;
					final expenses = (stats['expenses'] as num?)?.toDouble() ?? 0.0;
					final profit = (stats['profit'] as num?)?.toDouble() ?? 0.0;
					final projectedEarnings = (stats['projected_earnings'] as num?)?.toDouble() ?? 0.0;
					final projectedExpenses = (stats['projected_expenses'] as num?)?.toDouble() ?? 0.0;
					final projectedProfit = (stats['projected_profit'] as num?)?.toDouble() ?? 0.0;
					
					return Card(
						margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
						child: ExpansionTile(
							title: Text(
								name,
								style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
							),
							subtitle: Text(
								'Profit: KES ${NumberFormat('#,##0.00').format(profit)}',
								style: TextStyle(
									color: profit >= 0 ? AppColors.emerald : AppColors.deepRed,
									fontWeight: FontWeight.w600,
									fontSize: 11,
								),
							),
							children: [
								Padding(
									padding: const EdgeInsets.all(10),
									child: Column(
										children: [
											Row(
												mainAxisAlignment: MainAxisAlignment.spaceBetween,
												children: [
													Text('Actual Earnings:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
													Text(
														'KES ${NumberFormat('#,##0.00').format(earnings)}',
														style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
													),
												],
											),
											const SizedBox(height: 4),
											Row(
												mainAxisAlignment: MainAxisAlignment.spaceBetween,
												children: [
													Text('Actual Expenses:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
													Text(
														'KES ${NumberFormat('#,##0.00').format(expenses)}',
														style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
													),
												],
											),
											const SizedBox(height: 4),
											Row(
												mainAxisAlignment: MainAxisAlignment.spaceBetween,
												children: [
													Text('Actual Profit:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
													Text(
														'KES ${NumberFormat('#,##0.00').format(profit)}',
														style: TextStyle(
															fontWeight: FontWeight.w600,
															color: profit >= 0 ? AppColors.emerald : AppColors.deepRed,
															fontSize: 11,
														),
													),
												],
											),
											if (projectedEarnings > 0 || projectedExpenses > 0) ...[
												const Divider(),
												Row(
													mainAxisAlignment: MainAxisAlignment.spaceBetween,
													children: [
														Row(
															children: [
																Text('Projected Earnings:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
																const SizedBox(width: 4),
																Container(
																	padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
																	decoration: BoxDecoration(
																		color: Colors.orange.withOpacity(0.1),
																		borderRadius: BorderRadius.circular(4),
																	),
																	child: Text(
																		'Est',
																		style: TextStyle(
																			color: Colors.orange[700],
																			fontSize: 8,
																		),
																	),
																),
															],
														),
														Text(
															'KES ${NumberFormat('#,##0.00').format(projectedEarnings)}',
															style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
														),
													],
												),
												const SizedBox(height: 4),
												Row(
													mainAxisAlignment: MainAxisAlignment.spaceBetween,
													children: [
														Row(
															children: [
																Text('Projected Expenses:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
																const SizedBox(width: 4),
																Container(
																	padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
																	decoration: BoxDecoration(
																		color: Colors.orange.withOpacity(0.1),
																		borderRadius: BorderRadius.circular(4),
																	),
																	child: Text(
																		'Est',
																		style: TextStyle(
																			color: Colors.orange[700],
																			fontSize: 8,
																		),
																	),
																),
															],
														),
														Text(
															'KES ${NumberFormat('#,##0.00').format(projectedExpenses)}',
															style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
														),
													],
												),
												const SizedBox(height: 4),
												Row(
													mainAxisAlignment: MainAxisAlignment.spaceBetween,
													children: [
														Text('Projected Profit:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
														Text(
															'KES ${NumberFormat('#,##0.00').format(projectedProfit)}',
															style: TextStyle(
																fontWeight: FontWeight.w600,
																color: projectedProfit >= 0 ? AppColors.emerald : AppColors.deepRed,
																fontSize: 11,
															),
														),
													],
												),
											],
										],
									),
								),
							],
						),
					);
				}),
			],
		);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('Financial Dashboard'),
				actions: [
					IconButton(
						icon: const Icon(Icons.refresh),
						onPressed: _load,
						tooltip: 'Refresh',
					),
				],
			),
			body: _loading
				? const Center(child: CircularProgressIndicator())
				: _error != null
					? Center(
						child: Column(
							mainAxisAlignment: MainAxisAlignment.center,
							children: [
								Text(_error!, style: TextStyle(color: AppColors.deepRed)),
								const SizedBox(height: 16),
								ElevatedButton(
									onPressed: _load,
									child: const Text('Retry'),
								),
							],
						),
					)
					: _financialData == null
						? const Center(child: Text('No data available'))
						: RefreshIndicator(
							onRefresh: _load,
							child: SingleChildScrollView(
								child: Column(
									crossAxisAlignment: CrossAxisAlignment.start,
									children: [
										// Date Range Filter
										Card(
											margin: const EdgeInsets.all(12),
											child: Padding(
												padding: const EdgeInsets.all(10),
												child: Column(
													crossAxisAlignment: CrossAxisAlignment.start,
													children: [
														Text(
															'Date Range',
															style: Theme.of(context).textTheme.titleSmall?.copyWith(
																fontWeight: FontWeight.bold,
																fontSize: 13,
															),
														),
														const SizedBox(height: 8),
														Row(
															children: [
																Expanded(
																	child: OutlinedButton.icon(
																		onPressed: () => _selectDate(true),
																		icon: const Icon(Icons.calendar_today, size: 16),
																		label: Text(
																			_startDate != null
																				? DateFormat('MMM d, y').format(_startDate!)
																				: 'Start Date',
																		),
																	),
																),
																const SizedBox(width: 8),
																Expanded(
																	child: OutlinedButton.icon(
																		onPressed: () => _selectDate(false),
																		icon: const Icon(Icons.calendar_today, size: 16),
																		label: Text(
																			_endDate != null
																				? DateFormat('MMM d, y').format(_endDate!)
																				: 'End Date',
																		),
																	),
																),
															],
														),
													],
												),
											),
										),
										
										// Actual Financial Summary
										Padding(
											padding: const EdgeInsets.symmetric(horizontal: 12),
											child: Text(
												'Actual (Received/Spent)',
												style: Theme.of(context).textTheme.titleSmall?.copyWith(
													fontWeight: FontWeight.bold,
													color: AppColors.softCoral,
													fontSize: 14,
												),
											),
										),
										const SizedBox(height: 6),
										Padding(
											padding: const EdgeInsets.symmetric(horizontal: 12),
											child: Row(
												children: [
													Expanded(
														child: _buildStatCard(
															'Earnings',
															(_financialData!['total_earnings'] as num?)?.toDouble() ?? 0.0,
															AppColors.emerald,
														),
													),
													const SizedBox(width: 8),
													Expanded(
														child: _buildStatCard(
															'Expenses',
															(_financialData!['total_expenses'] as num?)?.toDouble() ?? 0.0,
															AppColors.deepRed,
														),
													),
												],
											),
										),
										const SizedBox(height: 6),
										Padding(
											padding: const EdgeInsets.symmetric(horizontal: 12),
											child: _buildStatCard(
												'Net Profit',
												(_financialData!['net_profit'] as num?)?.toDouble() ?? 0.0,
												((_financialData!['net_profit'] as num?)?.toDouble() ?? 0.0) >= 0 ? AppColors.emerald : AppColors.deepRed,
											),
										),
										
										const SizedBox(height: 16),
										
										// Projected Financial Summary
										Padding(
											padding: const EdgeInsets.symmetric(horizontal: 12),
											child: Text(
												'Projected (Quotes/Estimates)',
												style: Theme.of(context).textTheme.titleSmall?.copyWith(
													fontWeight: FontWeight.bold,
													color: AppColors.softCoral,
													fontSize: 14,
												),
											),
										),
										const SizedBox(height: 6),
										Padding(
											padding: const EdgeInsets.symmetric(horizontal: 12),
											child: Row(
												children: [
													Expanded(
														child: _buildStatCard(
															'Earnings',
															(_financialData!['total_projected_earnings'] as num?)?.toDouble() ?? 0.0,
															AppColors.emerald,
															isProjected: true,
														),
													),
													const SizedBox(width: 8),
													Expanded(
														child: _buildStatCard(
															'Expenses',
															(_financialData!['total_projected_expenses'] as num?)?.toDouble() ?? 0.0,
															AppColors.deepRed,
															isProjected: true,
														),
													),
												],
											),
										),
										const SizedBox(height: 6),
										Padding(
											padding: const EdgeInsets.symmetric(horizontal: 12),
											child: _buildStatCard(
												'Projected Profit',
												(_financialData!['projected_profit'] as num?)?.toDouble() ?? 0.0,
												((_financialData!['projected_profit'] as num?)?.toDouble() ?? 0.0) >= 0 ? AppColors.emerald : AppColors.deepRed,
												isProjected: true,
											),
										),
										
										const SizedBox(height: 16),
										
										// Combined Summary
										Card(
											margin: const EdgeInsets.symmetric(horizontal: 12),
											child: Padding(
												padding: const EdgeInsets.all(10),
												child: Column(
													crossAxisAlignment: CrossAxisAlignment.start,
													children: [
														Text(
															'Combined (Actual + Projected)',
															style: Theme.of(context).textTheme.titleSmall?.copyWith(
																fontWeight: FontWeight.bold,
																fontSize: 13,
															),
														),
														const SizedBox(height: 8),
														Row(
															mainAxisAlignment: MainAxisAlignment.spaceBetween,
															children: [
																Text('Total Earnings:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
																Text(
																	'KES ${NumberFormat('#,##0.00').format((_financialData!['total_combined_earnings'] as num?)?.toDouble() ?? 0.0)}',
																	style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.emerald, fontSize: 11),
																),
															],
														),
														const SizedBox(height: 6),
														Row(
															mainAxisAlignment: MainAxisAlignment.spaceBetween,
															children: [
																Text('Total Expenses:', style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11)),
																Text(
																	'KES ${NumberFormat('#,##0.00').format((_financialData!['total_combined_expenses'] as num?)?.toDouble() ?? 0.0)}',
																	style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.deepRed, fontSize: 11),
																),
															],
														),
														const Divider(height: 16),
														Row(
															mainAxisAlignment: MainAxisAlignment.spaceBetween,
															children: [
																Text(
																	'Combined Profit:',
																	style: Theme.of(context).textTheme.titleSmall?.copyWith(
																		fontWeight: FontWeight.bold,
																		fontSize: 13,
																	),
																),
																Text(
																	'KES ${NumberFormat('#,##0.00').format((_financialData!['combined_profit'] as num?)?.toDouble() ?? 0.0)}',
																	style: TextStyle(
																		fontSize: 15,
																		fontWeight: FontWeight.bold,
																		color: ((_financialData!['combined_profit'] as num?)?.toDouble() ?? 0.0) >= 0 ? AppColors.emerald : AppColors.deepRed,
																	),
																),
															],
														),
													],
												),
											),
										),
										
										const SizedBox(height: 16),
										
										// Breakdown by Job Type
										_buildBreakdownSection(
											'By Job Type',
											(_financialData!['by_job_type'] as Map<String, dynamic>?) ?? {},
										),
										
										const SizedBox(height: 12),
										
										// Breakdown by Client
										_buildBreakdownSection(
											'By Client',
											(_financialData!['by_client'] as Map<String, dynamic>?) ?? {},
										),
										
										const SizedBox(height: 16),
									],
								),
							),
						),
		);
	}
}

