import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';

import '../core/api_client.dart';
import '../core/session.dart';

class VoiceCaptureScreen extends StatefulWidget {
	const VoiceCaptureScreen({super.key});

	@override
	State<VoiceCaptureScreen> createState() => _VoiceCaptureScreenState();
}

class _VoiceCaptureScreenState extends State<VoiceCaptureScreen> {
	final _textCtrl = TextEditingController();
	final _recorder = AudioRecorder();
	bool _recording = false;
	String? _audioPath;
	bool _saving = false;
	String? _error;

	ApiClient get _api => context.read<ApiClient>();
	Session get _session => context.read<Session>();

	Future<bool> _ensureMic() async {
		final status = await Permission.microphone.request();
		return status.isGranted;
	}

	Future<void> _toggleRecord() async {
		if (_recording) {
			final path = await _recorder.stop();
			setState(() { _recording = false; _audioPath = path; });
			return;
		}
		if (!await _ensureMic()) {
			setState(() => _error = 'Microphone permission denied');
			return;
		}
		final dir = await getTemporaryDirectory();
		final outPath = '${dir.path}/note-${DateTime.now().millisecondsSinceEpoch}.m4a';
		await _recorder.start(
			const RecordConfig(encoder: AudioEncoder.aacLc, sampleRate: 16000, bitRate: 64000),
			path: outPath,
		);
		setState(() { _recording = true; _audioPath = null; _error = null; });
	}

	Future<void> _save() async {
		setState(() { _saving = true; _error = null; });
		_api.attachSession(_session);
		try {
			final createResp = await _api.dio.post('/notes', data: {
				'text': _textCtrl.text.trim().isEmpty ? null : _textCtrl.text.trim(),
			});
			final note = createResp.data as Map<String, dynamic>;
			final noteId = note['id'] as String;

			if (_audioPath != null) {
				final presign = await _api.dio.post(
					'/notes/$noteId/presign',
					queryParameters: {'kind': 'audio', 'content_type': 'audio/m4a'},
				);
				final p = presign.data as Map<String, dynamic>;
				final url = p['upload_url'] as String;
				final mediaId = p['media_id'] as String;
				final audioFile = File(_audioPath!);
				await Dio().put(url, data: audioFile.openRead(), options: Options(headers: {'Content-Type': 'audio/m4a'}));
				await _api.dio.post('/notes/$noteId/finalize', queryParameters: {'media_id': mediaId});
			}

			if (!mounted) return;
			setState(() { _textCtrl.clear(); _audioPath = null; _recording = false; });
			ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved')));
		} on DioException catch (e) {
			setState(() => _error = e.response?.data?.toString() ?? 'Failed');
		} finally {
			setState(() => _saving = false);
		}
	}

	@override
	void dispose() {
		_textCtrl.dispose();
		_recorder.dispose();
		super.dispose();
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('Record')),
			body: Padding(
				padding: const EdgeInsets.all(16),
				child: Column(
					children: [
						Expanded(
							child: Center(
								child: SizedBox(
									height: 160,
									width: 160,
									child: FilledButton(
										onPressed: _saving ? null : _toggleRecord,
										style: FilledButton.styleFrom(shape: const CircleBorder(), padding: EdgeInsets.zero),
										child: Icon(_recording ? Icons.stop : Icons.mic, size: 64),
									),
								),
							),
						),
						TextField(
							controller: _textCtrl,
							maxLines: 3,
							decoration: const InputDecoration(labelText: 'Optional note text'),
						),
						const SizedBox(height: 12),
						if (_audioPath != null) const Align(alignment: Alignment.centerLeft, child: Text('Audio attached')),
						if (_error != null) ...[
							const SizedBox(height: 8),
							Text(_error!, style: const TextStyle(color: Colors.red)),
						],
						const SizedBox(height: 8),
						SizedBox(
							width: double.infinity,
							child: FilledButton(
								onPressed: _saving || _recording ? null : _save,
								child: _saving
									? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
									: const Text('Save'),
							),
						),
					],
				),
			),
		);
	}
}
