import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:bark_frontend/auth/auth_service.dart';
import 'package:bark_frontend/auth/login_page.dart';
import 'package:bark_frontend/auth/pending_redirect.dart';
import 'package:bark_plugin_api/bark_plugin_api.dart';

void main() {
  setUp(() {
    testBaseUrlOverride = 'http://localhost:8997';
    SharedPreferences.setMockInitialValues({});
    pendingRedirect = null;
  });

  tearDown(() {
    testBaseUrlOverride = null;
    pendingRedirect = null;
  });

  Widget buildLoginPage() {
    return ChangeNotifierProvider(
      create: (_) => AuthService(),
      child: const MaterialApp(home: LoginPage()),
    );
  }

  group('LoginPage', () {
    testWidgets('renders login form', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.byType(LoginPage), findsOneWidget);
      expect(find.text('Bark'), findsOneWidget);
      expect(find.text('Log In'), findsWidgets); // button + title
    });

    testWidgets('has email and password fields', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsNWidgets(2));
    });

    testWidgets('has login button and register toggle', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.text('Log In'), findsWidgets);
      expect(find.textContaining('Create one'), findsOneWidget);
    });

    testWidgets('can type in fields', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      final fields = find.byType(TextField);
      await tester.enterText(fields.first, 'testuser');
      await tester.enterText(fields.last, 'testpass');

      expect(find.text('testuser'), findsOneWidget);
      expect(find.text('testpass'), findsOneWidget);
    });

    testWidgets('toggle switches between login and register', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.text('Log In'), findsWidgets);

      await tester.tap(find.textContaining('Create one'));
      await tester.pumpAndSettle();

      expect(find.text('Create Account'), findsWidgets);
      expect(find.textContaining('Log in'), findsWidgets);
    });

    testWidgets('shows Bark logo', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.pets), findsOneWidget);
    });

    testWidgets('shows Web Coding Agent subtitle', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.text('Web Coding Agent'), findsOneWidget);
    });

    testWidgets('shows re-auth message when pendingRedirect is set',
        (tester) async {
      pendingRedirect = '/workspace/abc123';
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.text('Please log in to continue.'), findsOneWidget);
    });

    testWidgets('does not show re-auth message when no pendingRedirect',
        (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.text('Please log in to continue.'), findsNothing);
    });

    testWidgets('login mode validates email format', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      final fields = find.byType(TextField);
      await tester.enterText(fields.first, 'notanemail');
      await tester.enterText(fields.last, 'password');

      await tester.tap(find.widgetWithText(FilledButton, 'Log In'));
      await tester.pumpAndSettle();

      expect(find.textContaining('valid email'), findsOneWidget);
    });

    testWidgets('register mode validates email format', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      // Switch to register mode
      await tester.tap(find.textContaining('Create one'));
      await tester.pumpAndSettle();

      final fields = find.byType(TextField);
      await tester.enterText(fields.first, 'notanemail');
      await tester.enterText(fields.last, 'password');

      await tester.tap(find.widgetWithText(FilledButton, 'Create Account'));
      await tester.pumpAndSettle();

      expect(find.textContaining('valid email'), findsOneWidget);
    });

    testWidgets('register mode accepts valid email', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      // Switch to register mode
      await tester.tap(find.textContaining('Create one'));
      await tester.pumpAndSettle();

      final fields = find.byType(TextField);
      await tester.enterText(fields.first, 'user@example.com');
      await tester.enterText(fields.last, 'pass');

      // Tap an invalid password to trigger validation without a real HTTP call
      await tester.enterText(fields.last, '');
      await tester.tap(find.widgetWithText(FilledButton, 'Create Account'));
      await tester.pumpAndSettle();

      // Email field should not show validation error
      expect(find.textContaining('valid email'), findsNothing);
    });

    testWidgets('register mode shows Email label', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      await tester.tap(find.textContaining('Create one'));
      await tester.pumpAndSettle();

      expect(find.text('Email'), findsOneWidget);
    });

    testWidgets('login mode shows Email label', (tester) async {
      await tester.pumpWidget(buildLoginPage());
      await tester.pumpAndSettle();

      expect(find.text('Email'), findsOneWidget);
    });
  });
}
