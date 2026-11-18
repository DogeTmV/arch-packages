package com.lanbridge.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.lanbridge.app.R
import com.lanbridge.app.data.SettingsRepository
import com.lanbridge.app.net.BridgeApi
import com.lanbridge.app.util.CommandExecutor
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import okhttp3.sse.EventSource
import org.json.JSONObject

class BridgeConnectionService : Service() {
    companion object {
        const val ACTION_START = "com.lanbridge.app.action.START"
        const val ACTION_STOP = "com.lanbridge.app.action.STOP"
        private const val CHANNEL_ID = "lanbridge_connection"
        private const val NOTIF_ID = 1001

        private val _connected = MutableStateFlow(false)
        val connected: StateFlow<Boolean> = _connected
        private val _status = MutableStateFlow("Disconnected")
        val status: StateFlow<String> = _status
        private val _lastEvent = MutableStateFlow<JSONObject?>(null)
        val lastEvent: StateFlow<JSONObject?> = _lastEvent

        var instance: BridgeConnectionService? = null
        fun isConnected(): Boolean = _connected.value
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var loopJob: Job? = null
    private var eventSource: EventSource? = null
    var api: BridgeApi? = null
    private lateinit var repo: SettingsRepository

    override fun onCreate() {
        super.onCreate()
        instance = this
        repo = SettingsRepository(this)
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> { stopConnection(); stopSelf(); return START_NOT_STICKY }
            else -> { startForeground(NOTIF_ID, buildNotification("Connecting…")); startConnection() }
        }
        return START_STICKY
    }

    private fun startConnection() {
        if (loopJob != null) return
        loopJob = scope.launch {
            while (true) {
                try {
                    val cfg = repo.configFlow.first()
                    if (cfg.host.isBlank() || cfg.token.isBlank()) {
                        _status.value = "Set host and token in Settings"
                        delay(3000); continue
                    }
                    val localApi = BridgeApi(cfg)
                    api = localApi
                    _status.value = "Pairing with ${cfg.host}:${cfg.port}…"
                    val pair = localApi.pair()
                    if (pair.isFailure) {
                        _connected.value = false
                        _status.value = "Pair failed: ${pair.exceptionOrNull()?.message}"
                        delay(4000); continue
                    }
                    _connected.value = true
                    _status.value = "Connected to ${cfg.host}:${cfg.port}"
                    updateNotification("Connected to ${cfg.host}")
                    localApi.postEvent("log", JSONObject().put("message", "Android client connected"))
                    eventSource?.cancel()
                    eventSource = localApi.openEvents(
                        onEvent = { evt -> handleEvent(evt) },
                        onFail = { msg -> _status.value = "Stream: $msg"; _connected.value = false }
                    )
                    // keep alive while connected; SSE callback flips state on failure
                    while (_connected.value) {
                        delay(5000)
                        localApi.postEvent("log", JSONObject().put("message", "heartbeat")).onFailure { _connected.value = false }
                    }
                    eventSource?.cancel(); eventSource = null
                } catch (e: Exception) {
                    _connected.value = false
                    _status.value = "Error: ${e.message}"
                }
                updateNotification("Reconnecting…")
                delay(4000)
            }
        }
    }

    private fun handleEvent(evt: JSONObject) {
        _lastEvent.value = evt
        val type = evt.optString("type")
        val payload = evt.optJSONObject("payload") ?: JSONObject()
        when (type) {
            "pc_clipboard" -> {
                val text = payload.optString("text", "")
                scope.launch { CommandExecutor.setClipboardText(this@BridgeConnectionService, text) }
            }
            "run_command" -> {
                val cmd = payload.optJSONObject("command") ?: return
                scope.launch {
                    val result = CommandExecutor.execute(this@BridgeConnectionService, cmd, api)
                    api?.postEvent("command_result", JSONObject().apply {
                        put("id", cmd.optString("id"))
                        put("name", cmd.optString("name"))
                        put("ok", result.first)
                        put("message", result.second)
                    })
                }
            }
            "commands_sync" -> {
                try {
                    val arr = payload.optJSONArray("commands") ?: return
                    val list = mutableListOf<com.lanbridge.app.data.SavedCommand>()
                    for (i in 0 until arr.length()) {
                        val o = arr.optJSONObject(i) ?: continue
                        list.add(com.lanbridge.app.data.SavedCommand(
                            id = o.optString("id", "cmd_$i"),
                            name = o.optString("name", "Command"),
                            action = o.optString("action", "notify"),
                            payload = o.optJSONObject("payload") ?: JSONObject(),
                            target = o.optString("target", "phone")
                        ))
                    }
                    scope.launch { repo.saveCommands(list) }
                } catch (_: Exception) {}
            }
            "phone_input" -> {
                val intent = Intent(LanBridgeAccessibilityService.ACTION_INPUT).apply {
                    setPackage(packageName)
                    putExtra("payload", payload.toString())
                }
                sendBroadcast(intent)
            }
        }
    }

    private fun stopConnection() {
        loopJob?.cancel(); loopJob = null
        eventSource?.cancel(); eventSource = null
        scope.launch { try { api?.postEvent("disconnect", JSONObject()) } catch (_: Exception) {} }
        _connected.value = false
        _status.value = "Disconnected"
    }

    private fun buildNotification(text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("LanBridge")
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_launcher)
            .setOngoing(true)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIF_ID, buildNotification(text))
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, "LanBridge connection", NotificationManager.IMPORTANCE_LOW)
            ch.description = "Keeps LanBridge connected to your PC"
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(ch)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopConnection()
        scope.cancel()
        instance = null
        super.onDestroy()
    }
}
