package com.lanbridge.app.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Path
import android.os.Build
import android.util.DisplayMetrics
import android.view.accessibility.AccessibilityEvent
import org.json.JSONObject

class LanBridgeAccessibilityService : AccessibilityService() {
    companion object {
        const val ACTION_INPUT = "com.lanbridge.app.action.INPUT"
        var instance: LanBridgeAccessibilityService? = null
        fun isEnabled(): Boolean = instance != null
    }

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != ACTION_INPUT) return
            val raw = intent.getStringExtra("payload") ?: return
            try { handleInput(JSONObject(raw)) } catch (_: Exception) {}
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        val filter = IntentFilter(ACTION_INPUT)
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(receiver, filter)
        }
    }

    private fun handleInput(payload: JSONObject) {
        when (payload.optString("type")) {
            "nav" -> when (payload.optString("key")) {
                "back" -> performGlobalAction(GLOBAL_ACTION_BACK)
                "home" -> performGlobalAction(GLOBAL_ACTION_HOME)
                "recents" -> performGlobalAction(GLOBAL_ACTION_RECENTS)
            }
            "tap" -> tapNorm(payload.optDouble("x", 0.5).toFloat(), payload.optDouble("y", 0.5).toFloat())
            "swipe" -> swipeNorm(
                payload.optDouble("x1", 0.5).toFloat(), payload.optDouble("y1", 0.8).toFloat(),
                payload.optDouble("x2", 0.5).toFloat(), payload.optDouble("y2", 0.2).toFloat(),
                payload.optLong("duration", 300L)
            )
        }
    }

    private fun screenSize(): Pair<Int, Int> {
        val dm = resources.displayMetrics
        return dm.widthPixels to dm.heightPixels
    }

    private fun tapNorm(nx: Float, ny: Float) {
        val (w, h) = screenSize()
        val x = (nx.coerceIn(0f, 1f) * w)
        val y = (ny.coerceIn(0f, 1f) * h)
        val path = Path().apply { moveTo(x, y) }
        val stroke = GestureDescription.StrokeDescription(path, 0, 50)
        dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    private fun swipeNorm(x1: Float, y1: Float, x2: Float, y2: Float, duration: Long) {
        val (w, h) = screenSize()
        val path = Path().apply {
            moveTo(x1.coerceIn(0f,1f)*w, y1.coerceIn(0f,1f)*h)
            lineTo(x2.coerceIn(0f,1f)*w, y2.coerceIn(0f,1f)*h)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, duration.coerceIn(50, 2000))
        dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}

    override fun onDestroy() {
        try { unregisterReceiver(receiver) } catch (_: Exception) {}
        instance = null
        super.onDestroy()
    }
}
