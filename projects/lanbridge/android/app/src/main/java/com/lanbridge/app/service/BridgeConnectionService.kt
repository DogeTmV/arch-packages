package com.lanbridge.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.lanbridge.app.MainActivity
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

        @Volatile var instance: BridgeConnectionService? = null
        fun isConnected(): Boolean = _connected.value

        fun start(context: Context) {
            val i = Intent(context, BridgeConnectionService::class.java).setAction(ACTION_START)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(i) else context.startService(i)
        }

        fun stop(context: Context) {
            val i = Intent(context, BridgeConnectionService::class.java).setAction(ACTION_STOP)
            context.startService(i)
        }
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var loopJob: Job? = null
    private var eventSource: EventSource? = null
    @Volatile var api: BridgeApi? = null
    private lateinit var repo: SettingsRepository

    override fun onCreate() {
        super.onCreate()
        instance = this
        repo = SettingsRepository(this)
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopConnection()
                try { stopForeground(STOP_FOREGROUND_REMOVE) } catch (_: Exception) {}
                stopSelf()
                return START_NOT_STICKY
            }
            else -> {
                startAsForeground("Connecting…")
                startConnection()
            }
        }
        return START_STICKY
    }

    private fun startAsForeground(text: String) {
        val notif = buildNotification(text)
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC else 0
        try {
            ServiceCompat.startForeground(this, NOTIF_ID, notif, type)
        } catch (_: Exception) {
            try { startForeground(NOTIF_ID, notif) } catch (_: Exception) {}
        }
    }

    private fun startConnection() {
        if (loopJob?.isActive == true) return
        loopJob = scope.launch {
            var backoff = 2000L
            while (true) {
                try {
                    val cfg = repo.configFlow.first()
                    if (cfg.host.isBlank() || cfg.token.isBlank()) {
                        _status.value = "Set host and token in Settings"
                        updateNotification("Not configured")
                        delay(3000)
                        continue
                    }
                    val localApi = BridgeApi(cfg)
                    api = localApi
                    _status.value = "Pairing with ${cfg.host}:${cfg.port}…"
                    updateNotification("Connecting to ${cfg.host}…")
                    val pair = localApi.pair()
                    if (pair.isFailure) {
                        _connected.value = false
                        val msg = pair.exceptionOrNull()?.message ?: "failed"
                        _status.value = "Pair failed: $msg"
                        updateNotification("Pair failed, retrying…")
                        delay(backoff); backoff = (backoff * 2).coerceAtMost(15000)
                        continue
                    }
                    backoff = 2000L
                    _connected.value = true
                    _status.value = "Connected to ${cfg.host}:${cfg.port}"
                    updateNotification("Connected to ${cfg.host}")
                    localApi.postEvent("log", JSONObject().put("message", "Android client connected"))
                    eventSource?.cancel()
                    eventSource = localApi.openEvents(
                        onEvent = { evt -> handleEvent(evt) },
                        onFail = { msg ->
                            if (_connected.value) _status.value = "Stream lost: $msg"
                            _connected.value = false
                        }
                    )
                    // keep alive while connected; SSE callback flips state on failure
                    while (_connected.value) {
                        delay(5000)
                        val hb = localApi.postEvent("log", JSONObject().put("message", "heartbeat"))
                        if (hb.isFailure) _connected.value = false
                    }
                    try { eventSource?.cancel() } catch (_: Exception) {}
                    eventSource = null
                } catch (e: Exception) {
                    _connected.value = false
                    _status.value = "Error: ${e.message ?: e.javaClass.simpleName}"
                }
                updateNotification("Reconnecting…")
                delay(backoff); backoff = (backoff * 2).coerceAtMost(15000)
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
                    try {
                        api?.postEvent("command_result", JSONObject().apply {
                            put("id", cmd.optString("id"))
                            put("name", cmd.optString("name"))
                            put("ok", result.first)
                            put("message", result.second)
                        })
                    } catch (_: Exception) {}
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
                try { sendBroadcast(intent) } catch (_: Exception) {}
            }
        }
    }

    private fun stopConnection() {
        _connected.value = false
        try { loopJob?.cancel() } catch (_: Exception) {}
        loopJob = null
        try { eventSource?.cancel() } catch (_: Exception) {}
        eventSource = null
        val a = api
        api = null
        scope.launch { try { a?.postEvent("disconnect", JSONObject()) } catch (_: Exception) {} }
        _status.value = "Disconnected"
    }

    private fun buildNotification(text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0)
        )
        val stopPi = PendingIntent.getService(
            this, 1, Intent(this, BridgeConnectionService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0)
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("LanBridge")
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_launcher)
            .setContentIntent(pi)
            .addAction(0, "Disconnect", stopPi)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun updateNotification(text: String) {
        try {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.notify(NOTIF_ID, buildNotification(text))
        } catch (_: Exception) {}
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, "LanBridge connection", NotificationManager.IMPORTANCE_LOW)
            ch.description = "Keeps LanBridge connected to your PC"
            ch.setShowBadge(false)
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(ch)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopConnection()
        try { scope.cancel() } catch (_: Exception) {}
        instance = null
        super.onDestroy()
    }
}
