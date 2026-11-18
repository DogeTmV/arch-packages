package com.lanbridge.app.service

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONObject

class LanBridgeNotificationService : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        val api = BridgeConnectionService.instance?.api ?: return
        if (!BridgeConnectionService.isConnected()) return
        try {
            val extras = sbn.notification.extras
            val title = extras?.getCharSequence("android.title")?.toString().orEmpty()
            val text = extras?.getCharSequence("android.text")?.toString().orEmpty()
            if (title.isBlank() && text.isBlank()) return
            val payload = JSONObject().apply {
                put("package", sbn.packageName ?: "")
                put("title", title.take(500))
                put("text", text.take(1000))
                put("when", sbn.postTime)
            }
            api.postEvent("notification", payload)
        } catch (_: Exception) {}
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {}
}
