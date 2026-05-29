import 'package:flutter/material.dart';
import '../theme/colors.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:klangk_plugin_api/klangk_plugin_api.dart';
import '../auth/auth_service.dart';

/// Shared widget for the settings, admin, and logout icons in the app bar.
/// Renders icons based on auth state.
class AppBarActions extends StatelessWidget {
  final VoidCallback? onSettingsPressed;
  final VoidCallback? onLogoutPressed;
  final VoidCallback? onAdminPressed;

  const AppBarActions({
    super.key,
    this.onSettingsPressed,
    this.onLogoutPressed,
    this.onAdminPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (context.watch<AuthService>().isAdmin)
          IconButton(
            icon: const Icon(Icons.admin_panel_settings,
                color: KColors.textSecondary),
            tooltip: 'User Management',
            onPressed: onAdminPressed ?? () => context.go('/admin/users'),
          ),
        IconButton(
          icon: const Icon(Icons.settings, color: KColors.textSecondary),
          tooltip: 'Settings',
          onPressed: onSettingsPressed ??
              () => context.go('/settings'), // coverage:ignore-line
        ),
        IconButton(
          icon: const Icon(Icons.logout, color: KColors.textSecondary),
          tooltip: 'Logout',
          onPressed: onLogoutPressed ??
              () async {
                await context.read<AuthService>().logout();
                if (context.mounted) context.go('/login');
              },
        ),
      ],
    );
  }
}
