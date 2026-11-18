package com.lanbridge.app.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import com.lanbridge.app.data.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: return
        if (action != Intent.ACTION_BOOT_COMPLETED && action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        val pending = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val cfg = SettingsRepository(context).configFlow.first()
                // Only auto-connect if the user has configured a target and explicitly opted in via saved config.
                // We treat a configured host+token as opt-in for background reconnect; users can clear them to disable.
                if (cfg.host.isNotBlank() && cfg.token.isNotBlank()) {
                    val svc = Intent(context, BridgeConnectionService::class.java).setAction(BridgeConnectionService.ACTION_START)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        context.startForegroundService(svc)
                    } else {
                        context.startService(svc)
                    }
                }
            } catch (_: Exception) {
            } finally {
                try { pending.finish() } catch (_: Exception) {}
            }
        }
    }
}
