import 'dart:convert';
import 'package:http/http.dart' as http;
import '../utils/backend_url.dart';

/// Cached Soliplex URL fetched from the Bark backend config.
String? _soliplexUrl;

/// Fetch the Soliplex URL from the Bark backend config endpoint.
Future<String> _getSoliplexUrl() async {
  if (_soliplexUrl != null) return _soliplexUrl!;
  final resp = await http.get(Uri.parse('$baseUrl/api/config'));
  if (resp.statusCode == 200) {
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    _soliplexUrl = (data['soliplex_url'] as String? ?? '').replaceAll(RegExp(r'/+$'), '');
  }
  _soliplexUrl ??= '';
  return _soliplexUrl!;
}

/// Lightweight Soliplex client that calls the Soliplex API directly.
class SoliplexClient {
  SoliplexClient();

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

  /// List all rooms the user has access to.
  Future<List<Map<String, dynamic>>> listRooms() async {
    final soliplexUrl = await _getSoliplexUrl();
    final response = await http.get(
      Uri.parse('$soliplexUrl/api/v1/rooms'),
      headers: _headers,
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to list rooms: ${response.statusCode} ${response.body}');
    }
    final data = jsonDecode(response.body);
    if (data is Map) {
      return data.entries.map((e) {
        final room = e.value as Map<String, dynamic>;
        return {'room_id': e.key, ...room};
      }).toList();
    }
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    }
    return [];
  }

  /// Query a room by creating a thread, posting a question, and collecting the response.
  Future<String> queryRoom(String roomId, String question) async {
    final soliplexUrl = await _getSoliplexUrl();

    // 1. Create a new thread
    final threadResp = await http.post(
      Uri.parse('$soliplexUrl/api/v1/rooms/$roomId/agui'),
      headers: _headers,
      body: jsonEncode({}),
    );
    if (threadResp.statusCode != 200) {
      throw Exception('Failed to create thread: ${threadResp.statusCode} ${threadResp.body}');
    }
    final threadData = jsonDecode(threadResp.body);
    final threadId = threadData['thread_id'] as String;

    final runs = threadData['runs'] as Map<String, dynamic>? ?? {};
    if (runs.isEmpty) {
      throw Exception('No run created for thread');
    }
    final runId = runs.keys.first;

    // 2. Post the question and collect the streamed SSE response
    final sseUrl = '$soliplexUrl/api/v1/rooms/$roomId/agui/$threadId/$runId';

    final runInput = jsonEncode({
      'thread_id': threadId,
      'run_id': runId,
      'state': null,
      'messages': [
        {
          'id': 'msg-${DateTime.now().millisecondsSinceEpoch}',
          'role': 'user',
          'content': question,
        }
      ],
      'tools': [],
      'context': [],
      'forwarded_props': null,
    });

    // Use a streamed request so we can read the SSE response as it arrives
    final client = http.Client();
    try {
      final request = http.Request('POST', Uri.parse(sseUrl));
      request.headers['Content-Type'] = 'application/json';
      request.headers['Accept'] = 'text/event-stream';
      request.body = runInput;

      final streamedResp = await client.send(request);

      if (streamedResp.statusCode != 200) {
        final body = await streamedResp.stream.bytesToString();
        throw Exception('Failed to run query: ${streamedResp.statusCode} $body');
      }

      // Collect the full streamed response, then parse
      final body = await streamedResp.stream.bytesToString();
      final responseText = _extractTextFromSseResponse(body);
      return responseText.isNotEmpty ? responseText : '(No response from Soliplex)';
    } finally {
      client.close();
    }
  }

  /// Parse SSE event stream and extract TEXT_MESSAGE_CONTENT deltas.
  String _extractTextFromSseResponse(String sseBody) {
    final buffer = StringBuffer();
    for (final line in sseBody.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      final data = line.substring(6).trim();
      if (data.isEmpty || data == '[DONE]') continue;
      try {
        final event = jsonDecode(data) as Map<String, dynamic>;
        final type = event['type'] as String?;
        if (type == 'TEXT_MESSAGE_CONTENT') {
          buffer.write(event['delta'] ?? '');
        }
      } catch (_) {
        // Skip non-JSON lines
      }
    }
    return buffer.toString();
  }
}
